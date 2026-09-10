"""AstraTrace Optical Tile Quality Detector.

SIH 2026 | Problem ID: SIH26227
Analyzes 4-band optical satellite imagery to extract transparent, physically-grounded
quality signals: nodata, clouds, shadows, sensor saturation, and usable pixel area.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import rasterio

from apps.backend.app.core.errors import NotFoundError, ValidationError
from apps.backend.app.core.logging import logger
from apps.backend.app.schemas.quality import QualityStatus, TileQualityMetrics


class TileQualityDetector:
    """Evaluates optical quality and usable area for a single satellite tile."""

    def __init__(
        self,
        cloud_vis_threshold: float = 0.35,
        cloud_nir_threshold: float = 0.30,
        cloud_whiteness_tolerance: float = 0.25,
        shadow_nir_threshold: float = 0.12,
        shadow_vis_threshold: float = 0.10,
        saturation_threshold: float = 0.98,
        nodata_tolerance: float = 0.90,
    ):
        # Configurable engineering thresholds with safe bounds
        self.cloud_vis_threshold = float(np.clip(cloud_vis_threshold, 0.15, 0.80))
        self.cloud_nir_threshold = float(np.clip(cloud_nir_threshold, 0.15, 0.80))
        self.cloud_whiteness_tolerance = float(np.clip(cloud_whiteness_tolerance, 0.05, 0.50))
        self.shadow_nir_threshold = float(np.clip(shadow_nir_threshold, 0.02, 0.25))
        self.shadow_vis_threshold = float(np.clip(shadow_vis_threshold, 0.02, 0.25))
        self.saturation_threshold = float(np.clip(saturation_threshold, 0.90, 1.00))
        self.nodata_tolerance = float(np.clip(nodata_tolerance, 0.50, 0.99))

    def analyze_raster(
        self,
        raster_input: Union[Path, str, np.ndarray],
        nodata_val: Optional[float] = None,
        tile_id: Optional[str] = None,
    ) -> Tuple[TileQualityMetrics, Dict[str, np.ndarray]]:
        """Extracts optical quality metrics and boolean masks from raster file or array.

        Returns:
            Tuple[TileQualityMetrics, Dict[str, np.ndarray]]:
                - Pydantic quality metrics summary
                - Dictionary of 2D boolean masks: "valid", "cloud", "shadow", "saturated", "usable"
        """
        if isinstance(raster_input, (Path, str)):
            p = Path(raster_input)
            if not p.exists() or not p.is_file():
                raise NotFoundError(f"Raster file not found: {raster_input}")
            with rasterio.open(p) as src:
                arr = src.read().astype(np.float32)
                nodata_val = src.nodata if nodata_val is None else nodata_val
        elif isinstance(raster_input, np.ndarray):
            arr = raster_input.astype(np.float32)
        else:
            raise ValidationError(f"Unsupported raster input type: {type(raster_input)}")

        if arr.ndim != 3 or arr.shape[0] < 1 or arr.shape[1] < 1 or arr.shape[2] < 1:
            raise ValidationError(f"Invalid raster shape: expected (bands, H, W), got {arr.shape}")

        # Check for non-finite values (NaN / Inf) and sanitize
        has_nan_inf = not np.all(np.isfinite(arr))
        if has_nan_inf:
            nan_inf_mask = ~np.isfinite(arr)
            arr = np.nan_to_num(arr, nan=0.0, posinf=10000.0, neginf=0.0)
        else:
            nan_inf_mask = np.zeros(arr.shape, dtype=bool)

        bands, height, width = arr.shape
        total_pixels = height * width

        # Scale detection: if values > 1.0, assume Sentinel-2 [0, 10000] reflectance and normalize to [0, 1]
        max_val = float(np.max(arr)) if total_pixels > 0 else 0.0
        scale = 10000.0 if max_val > 1.5 else 1.0
        norm_arr = arr / scale

        # 1. NoData / Invalid Pixel Mask
        nodata_mask = np.zeros((height, width), dtype=bool)
        if nodata_val is not None:
            nodata_mask |= np.isclose(arr[0], nodata_val)

        # All-zero across all bands (edge/padding)
        all_zeros = np.all(arr == 0, axis=0)
        nodata_mask |= all_zeros

        # Non-finite pixels
        any_nan_inf = np.any(nan_inf_mask, axis=0)
        nodata_mask |= any_nan_inf

        valid_mask = ~nodata_mask
        valid_count = int(np.sum(valid_mask))
        nodata_count = total_pixels - valid_count

        # Early exit for completely invalid or empty images
        if valid_count == 0:
            metrics = TileQualityMetrics(
                tile_id=tile_id,
                total_pixels=total_pixels,
                valid_pixels=0,
                nodata_pixels=total_pixels,
                cloud_pixels=0,
                shadow_pixels=0,
                saturated_pixels=0,
                dark_pixels=0,
                usable_pixels=0,
                nodata_fraction=1.0,
                cloud_fraction=0.0,
                shadow_fraction=0.0,
                usable_fraction=0.0,
                quality_score=0.0,
                quality_status=QualityStatus.INSUFFICIENT,
                quality_flags=["ALL_NODATA", "OBSERVATION_EMPTY"],
            )
            empty_mask = np.zeros((height, width), dtype=bool)
            return metrics, {
                "valid": valid_mask,
                "cloud": empty_mask,
                "shadow": empty_mask,
                "saturated": empty_mask,
                "usable": empty_mask,
            }

        # 2. Extract Spectral Bands
        # Standard Sentinel-2 ordering: B0=Blue, B1=Green, B2=Red, B3=NIR
        if bands >= 4:
            blue = norm_arr[0]
            green = norm_arr[1]
            red = norm_arr[2]
            nir = norm_arr[3]
        elif bands == 3:
            blue = norm_arr[0]
            green = norm_arr[1]
            red = norm_arr[2]
            nir = green  # Fallback
        else:
            blue = norm_arr[0]
            green = norm_arr[0]
            red = norm_arr[0]
            nir = norm_arr[0]

        vis_mean = (blue + green + red) / 3.0

        # 3. Cloud Contamination Detection
        # Clouds: high visible reflectance, high NIR, spectral whiteness (low inter-band variance in visible)
        cloud_vis = vis_mean > self.cloud_vis_threshold
        cloud_nir = nir > self.cloud_nir_threshold
        diff_rg = np.abs(red - green)
        diff_gb = np.abs(green - blue)
        max_diff = np.maximum(diff_rg, diff_gb)
        whiteness = max_diff / np.maximum(vis_mean, 1e-4) < self.cloud_whiteness_tolerance

        cloud_mask = cloud_vis & cloud_nir & whiteness & valid_mask

        # 4. Cloud Shadow Detection
        # Shadows: very low visible & NIR, but excluding deep clear water (NDWI check)
        shadow_vis = vis_mean < self.shadow_vis_threshold
        shadow_nir = nir < self.shadow_nir_threshold
        denom_ndwi = green + nir + 1e-6
        ndwi = (green - nir) / denom_ndwi
        not_water = ndwi < 0.15

        shadow_mask = shadow_vis & shadow_nir & not_water & valid_mask & (~cloud_mask)

        # 5. Sensor Saturation & Extreme Darkness
        sat_mask = (np.any(norm_arr > self.saturation_threshold, axis=0)) & valid_mask
        dark_mask = (vis_mean < 0.01) & valid_mask & (~shadow_mask)

        # 6. Usable Pixel Mask
        unusable_mask = cloud_mask | shadow_mask | sat_mask | nodata_mask
        usable_mask = ~unusable_mask
        usable_count = int(np.sum(usable_mask))

        # 7. Compute Metric Fractions
        cloud_count = int(np.sum(cloud_mask))
        shadow_count = int(np.sum(shadow_mask))
        sat_count = int(np.sum(sat_mask))
        dark_count = int(np.sum(dark_mask))

        nodata_fraction = round(nodata_count / float(total_pixels), 4)
        cloud_fraction = round(cloud_count / float(valid_count), 4) if valid_count > 0 else 0.0
        shadow_fraction = round(shadow_count / float(valid_count), 4) if valid_count > 0 else 0.0
        usable_fraction = round(usable_count / float(total_pixels), 4)

        # 8. Compute Composite Tile Quality Score
        penalty = 0.5 * cloud_fraction + 0.3 * shadow_fraction + 0.2 * (sat_count / valid_count)
        base_score = usable_fraction * max(0.0, 1.0 - penalty)
        quality_score = round(float(np.clip(base_score, 0.0, 1.0)), 4)

        # 9. Assign Diagnostic Flags
        flags: List[str] = []
        if has_nan_inf:
            flags.append("NAN_INF_VALUES_DETECTED")
        if nodata_fraction > 0.25:
            flags.append("NODATA_EXCESSIVE")
        if cloud_fraction > 0.30:
            flags.append("CLOUD_CONTAMINATION_HIGH")
        elif cloud_fraction > 0.02:
            flags.append("CLOUD_CONTAMINATION_MODERATE")
        if shadow_fraction > 0.02:
            flags.append("CLOUD_SHADOW_DETECTED")
        if sat_count > 0:
            flags.append("SENSOR_SATURATION_DETECTED")
        if dark_count > (0.1 * valid_count):
            flags.append("EXTREME_DARKNESS_DETECTED")

        # 10. Determine Categorical Quality Status
        if nodata_fraction >= self.nodata_tolerance or usable_fraction < 0.05:
            status = QualityStatus.INSUFFICIENT
            flags.append("STATUS_INSUFFICIENT")
        elif cloud_fraction > 0.40 or quality_score < 0.30:
            status = QualityStatus.UNRELIABLE
            flags.append("STATUS_UNRELIABLE")
        elif cloud_fraction > 0.10 or shadow_fraction > 0.10 or nodata_fraction > 0.15 or quality_score < 0.80:
            status = QualityStatus.DEGRADED
            flags.append("STATUS_DEGRADED")
        else:
            status = QualityStatus.USABLE
            flags.append("STATUS_USABLE")

        metrics = TileQualityMetrics(
            tile_id=tile_id,
            total_pixels=total_pixels,
            valid_pixels=valid_count,
            nodata_pixels=nodata_count,
            cloud_pixels=cloud_count,
            shadow_pixels=shadow_count,
            saturated_pixels=sat_count,
            dark_pixels=dark_count,
            usable_pixels=usable_count,
            nodata_fraction=nodata_fraction,
            cloud_fraction=cloud_fraction,
            shadow_fraction=shadow_fraction,
            usable_fraction=usable_fraction,
            quality_score=quality_score,
            quality_status=status,
            quality_flags=flags,
        )

        masks = {
            "valid": valid_mask,
            "cloud": cloud_mask,
            "shadow": shadow_mask,
            "saturated": sat_mask,
            "usable": usable_mask,
        }
        return metrics, masks
