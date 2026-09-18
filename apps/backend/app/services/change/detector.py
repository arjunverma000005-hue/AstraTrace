"""AstraTrace Baseline Change Detector.

SIH 2026 | Problem ID: SIH26227
Validates bitemporal raster pairs, computes spectral differences and index deltas,
applies Otsu thresholding and pure NumPy morphology, classifies change types,
and generates georeferenced change masks.
"""
from pathlib import Path
import time
from typing import Any, Dict, Optional, Tuple, Union
import numpy as np
from PIL import Image
import rasterio

from apps.backend.app.core.errors import NotFoundError, ValidationError
from apps.backend.app.core.logging import logger
from apps.backend.app.services.change.differencing import (
    compute_index_deltas,
    compute_otsu_threshold,
    compute_spectral_difference,
)
from apps.backend.app.services.change.morphology import (
    binary_closing,
    binary_opening,
    filter_small_components,
)


class BaselineChangeDetector:
    """Deterministic change detector performing bitemporal image comparison and noise filtering."""

    def __init__(self, project_root: Optional[Path] = None):
        if project_root is None:
            current = Path(__file__).resolve()
            for parent in current.parents:
                if (parent / "data").is_dir() and (parent / "README.md").is_file():
                    self.project_root = parent
                    break
            else:
                self.project_root = current.parents[4]
        else:
            self.project_root = project_root

    def validate_pair(
        self,
        t1_path_input: Union[str, Path],
        t2_path_input: Union[str, Path],
    ) -> Tuple[Path, Path]:
        """Validates that both rasters exist, are readable, share CRS, and have matching dimensions."""
        p1 = Path(t1_path_input)
        if not p1.is_absolute():
            p1 = (self.project_root / p1).resolve()

        p2 = Path(t2_path_input)
        if not p2.is_absolute():
            p2 = (self.project_root / p2).resolve()

        if not p1.exists() or not p1.is_file():
            raise NotFoundError(f"T1 before raster not found: {t1_path_input}")
        if not p2.exists() or not p2.is_file():
            raise NotFoundError(f"T2 after raster not found: {t2_path_input}")

        with rasterio.open(p1) as src1, rasterio.open(p2) as src2:
            # 1. CRS validation
            if src1.crs != src2.crs:
                raise ValidationError(
                    f"CRS mismatch: T1 CRS '{src1.crs}' != T2 CRS '{src2.crs}'. Imagery must be co-registered."
                )

            # 2. Dimensions validation
            if (src1.height, src1.width) != (src2.height, src2.width):
                raise ValidationError(
                    f"Dimension mismatch: T1 ({src1.width}x{src1.height}) != T2 ({src2.width}x{src2.height})."
                )

            # 3. Band count validation
            if src1.count != src2.count:
                raise ValidationError(
                    f"Band count mismatch: T1 has {src1.count} bands, T2 has {src2.count} bands."
                )

        return p1, p2

    def detect_change(
        self,
        t1_path_input: Union[str, Path, np.ndarray],
        t2_path_input: Union[str, Path, np.ndarray],
        threshold: Optional[float] = None,
        min_pixels: int = 10,
        apply_morphology: bool = True,
        output_mask_path: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """Executes end-to-end baseline change detection across two co-registered rasters or arrays."""
        t0 = time.perf_counter()

        # Step 1: Preprocessing & validation
        if isinstance(t1_path_input, np.ndarray) and isinstance(t2_path_input, np.ndarray):
            t1_data = t1_path_input.astype(np.float32)
            t2_data = t2_path_input.astype(np.float32)
            if t1_data.shape != t2_data.shape:
                raise ValidationError(
                    f"Dimension mismatch: T1 shape {t1_data.shape} != T2 shape {t2_data.shape}."
                )
            if t1_data.ndim != 3:
                raise ValidationError(f"Expected 3D array (bands, height, width). Got ndim={t1_data.ndim}")
            nodata1 = None
            nodata2 = None
            transform = None
            crs = "EPSG:4326"
        else:
            p1, p2 = self.validate_pair(t1_path_input, t2_path_input)
            with rasterio.open(p1) as src1, rasterio.open(p2) as src2:
                t1_data = src1.read().astype(np.float32)
                t2_data = src2.read().astype(np.float32)
                nodata1 = src1.nodata
                nodata2 = src2.nodata
                transform = src1.transform
                crs = src1.crs.to_string() if src1.crs else "EPSG:4326"

        bands, height, width = t1_data.shape

        # Construct valid data mask (exclude NoData or all-zero pixels)
        valid_mask = np.ones((height, width), dtype=bool)
        if nodata1 is not None:
            valid_mask &= (t1_data[0] != nodata1)
        if nodata2 is not None:
            valid_mask &= (t2_data[0] != nodata2)

        # Exclude regions where both are all zeros across all bands
        zero_t1 = np.all(t1_data == 0, axis=0)
        zero_t2 = np.all(t2_data == 0, axis=0)
        valid_mask &= ~(zero_t1 | zero_t2)

        t1_perf = time.perf_counter()
        preprocess_ms = round((t1_perf - t0) * 1000.0, 3)

        # Step 2: Normalized spectral differencing & index deltas
        diff_magnitude = compute_spectral_difference(t1_data, t2_data, valid_mask=valid_mask)
        index_deltas = compute_index_deltas(t1_data, t2_data, valid_mask=valid_mask)

        t2_perf = time.perf_counter()
        diff_ms = round((t2_perf - t1_perf) * 1000.0, 3)

        # Step 3: Adaptive Otsu or calibrated thresholding
        if threshold is None:
            effective_threshold = compute_otsu_threshold(diff_magnitude, valid_mask=valid_mask)
        else:
            if not (0.01 <= threshold <= 0.99):
                raise ValidationError(f"Threshold must be between 0.01 and 0.99. Got: {threshold}")
            effective_threshold = float(threshold)

        raw_change_mask = (diff_magnitude >= effective_threshold) & valid_mask

        # Step 4: Pure NumPy morphology noise filtering
        if apply_morphology:
            # Opening removes 1-pixel jitter, closing fills structural voids
            opened = binary_opening(raw_change_mask, kernel_size=3)
            closed = binary_closing(opened, kernel_size=3)
            clean_mask = filter_small_components(closed, min_pixels=min_pixels)
        else:
            clean_mask = raw_change_mask

        t3_perf = time.perf_counter()
        morphology_ms = round((t3_perf - t2_perf) * 1000.0, 3)

        # Step 5: Metrics computation and Change Taxonomy
        total_pixels = height * width
        valid_pixels = int(np.sum(valid_mask))
        changed_pixels = int(np.sum(clean_mask))
        change_percent = round((changed_pixels / valid_pixels * 100.0), 4) if valid_pixels > 0 else 0.0

        if changed_pixels > 0:
            mean_magnitude = round(float(np.mean(diff_magnitude[clean_mask])), 4)
            # Normalized composite score: weighted by magnitude and changed area
            area_weight = min(1.0, (changed_pixels / valid_pixels) * 5.0) if valid_pixels > 0 else 0.0
            composite_change_score = round(float(0.4 * mean_magnitude + 0.6 * area_weight), 4)

            # Heuristic physical taxonomy
            mean_d_bright = float(np.mean(index_deltas["delta_brightness"][clean_mask]))
            mean_d_ndvi = float(np.mean(index_deltas["delta_ndvi"][clean_mask]))
            mean_d_ndwi = float(np.mean(index_deltas["delta_ndwi"][clean_mask]))

            if mean_d_bright > 0.15 and mean_d_ndvi < -0.05:
                change_type = "construction"
            elif mean_d_ndvi < -0.20:
                change_type = "vegetation_loss"
            elif mean_d_ndvi > 0.20:
                change_type = "vegetation_gain"
            elif abs(mean_d_ndwi) > 0.20:
                change_type = "water_shift"
            elif mean_d_bright > 0.15:
                change_type = "construction"
            else:
                change_type = "unclassified_surface_shift"
        else:
            mean_magnitude = 0.0
            composite_change_score = 0.0
            change_type = "no_change"
            mean_d_bright = 0.0
            mean_d_ndvi = 0.0
            mean_d_ndwi = 0.0

        # Step 6: Generate mask image file if requested or default
        mask_path_str = None
        if output_mask_path is not None:
            out_p = Path(output_mask_path)
            if not out_p.is_absolute():
                out_p = (self.project_root / out_p).resolve()

            # Save 8-bit grayscale PNG: 0 = background, 255 = change
            mask_img = Image.fromarray((clean_mask * 255).astype(np.uint8), mode="L")
            try:
                out_p.parent.mkdir(parents=True, exist_ok=True)
                mask_img.save(out_p)
                mask_path_str = str(out_p.relative_to(self.project_root)).replace("\\", "/")
            except (OSError, PermissionError):
                tmp_dir = Path("/tmp/changes")
                tmp_dir.mkdir(parents=True, exist_ok=True)
                tmp_path = tmp_dir / out_p.name
                mask_img.save(tmp_path)
                mask_path_str = f"/tmp/changes/{out_p.name}"

        total_ms = round((time.perf_counter() - t0) * 1000.0, 3)

        return {
            "total_pixels": total_pixels,
            "valid_pixels": valid_pixels,
            "changed_pixels": changed_pixels,
            "change_percent": change_percent,
            "mean_magnitude": mean_magnitude,
            "composite_change_score": composite_change_score,
            "change_type": change_type,
            "effective_threshold": effective_threshold,
            "applied_morphology": apply_morphology,
            "min_component_pixels": min_pixels,
            "change_mask": clean_mask,
            "index_deltas_mean": {
                "delta_brightness": round(mean_d_bright, 4),
                "delta_ndvi": round(mean_d_ndvi, 4),
                "delta_ndwi": round(mean_d_ndwi, 4),
            },
            "mask_path": mask_path_str,
            "execution_trace": {
                "preprocess_ms": preprocess_ms,
                "diff_ms": diff_ms,
                "morphology_ms": morphology_ms,
                "total_ms": total_ms,
            },
        }
