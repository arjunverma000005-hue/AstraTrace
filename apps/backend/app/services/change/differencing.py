"""Spectral Differencing and Index Deltas Engine.

SIH 2026 | Problem ID: SIH26227
Pure NumPy implementations of normalized Euclidean distance, Delta NDVI,
Delta NDWI, Delta Brightness, and adaptive Otsu thresholding.
"""
from typing import Dict, Optional, Tuple
import numpy as np


def compute_spectral_difference(
    t1_data: np.ndarray,
    t2_data: np.ndarray,
    valid_mask: Optional[np.ndarray] = None,
    eps: float = 1e-6,
) -> np.ndarray:
    """Computes pixel-wise normalized Euclidean spectral distance between two rasters.

    Args:
        t1_data: First observation raster of shape (bands, height, width), float32.
        t2_data: Second observation raster of shape (bands, height, width), float32.
        valid_mask: Boolean 2D mask of shape (height, width) where True means valid pixel.
        eps: Small epsilon to prevent division by zero.

    Returns:
        2D float32 magnitude map of shape (height, width) in range [0.0, 1.0].
    """
    bands, height, width = t1_data.shape
    if t2_data.shape != t1_data.shape:
        raise ValueError(
            f"Shape mismatch: t1 shape {t1_data.shape} != t2 shape {t2_data.shape}"
        )

    # Relative normalized difference per band
    max_vals = np.maximum(np.abs(t1_data), np.maximum(np.abs(t2_data), eps))
    diff_norm = (t2_data - t1_data) / max_vals

    # Mean squared error across bands, then square root
    mse = np.mean(diff_norm ** 2, axis=0)
    magnitude = np.sqrt(mse)

    # Clip to [0.0, 1.0]
    magnitude = np.clip(magnitude, 0.0, 1.0).astype(np.float32)

    if valid_mask is not None:
        magnitude[~valid_mask] = 0.0

    return magnitude


def compute_index_deltas(
    t1_data: np.ndarray,
    t2_data: np.ndarray,
    valid_mask: Optional[np.ndarray] = None,
    eps: float = 1e-6,
) -> Dict[str, np.ndarray]:
    """Computes physical spectral index deltas (Delta NDVI, Delta NDWI, Delta Brightness).

    Sentinel-2 4-band order: Band 1: Blue, Band 2: Green, Band 3: Red, Band 4: NIR.

    Returns:
        Dictionary containing 2D arrays:
        - "delta_ndvi": NDVI_T2 - NDVI_T1 in [-2.0, 2.0]
        - "delta_ndwi": NDWI_T2 - NDWI_T1 in [-2.0, 2.0]
        - "delta_brightness": relative brightness change in [-1.0, 1.0]
    """
    bands, height, width = t1_data.shape

    if bands >= 4:
        # Full 4-band Sentinel-2 processing
        blue_t1, green_t1, red_t1, nir_t1 = t1_data[0], t1_data[1], t1_data[2], t1_data[3]
        blue_t2, green_t2, red_t2, nir_t2 = t2_data[0], t2_data[1], t2_data[2], t2_data[3]

        # NDVI: (NIR - Red) / (NIR + Red + eps)
        ndvi_t1 = (nir_t1 - red_t1) / (nir_t1 + red_t1 + eps)
        ndvi_t2 = (nir_t2 - red_t2) / (nir_t2 + red_t2 + eps)
        delta_ndvi = (ndvi_t2 - ndvi_t1).astype(np.float32)

        # NDWI: (Green - NIR) / (Green + NIR + eps)
        ndwi_t1 = (green_t1 - nir_t1) / (green_t1 + nir_t1 + eps)
        ndwi_t2 = (green_t2 - nir_t2) / (green_t2 + nir_t2 + eps)
        delta_ndwi = (ndwi_t2 - ndwi_t1).astype(np.float32)

        # Brightness: (Blue + Green + Red) / 3.0
        bright_t1 = (blue_t1 + green_t1 + red_t1) / 3.0
        bright_t2 = (blue_t2 + green_t2 + red_t2) / 3.0
        denom_b = np.maximum(bright_t1, np.maximum(bright_t2, eps))
        delta_bright = ((bright_t2 - bright_t1) / denom_b).astype(np.float32)

    elif bands == 3:
        # RGB only: Band 1: Blue, Band 2: Green, Band 3: Red
        blue_t1, green_t1, red_t1 = t1_data[0], t1_data[1], t1_data[2]
        blue_t2, green_t2, red_t2 = t2_data[0], t2_data[1], t2_data[2]

        bright_t1 = (blue_t1 + green_t1 + red_t1) / 3.0
        bright_t2 = (blue_t2 + green_t2 + red_t2) / 3.0
        denom_b = np.maximum(bright_t1, np.maximum(bright_t2, eps))
        delta_bright = ((bright_t2 - bright_t1) / denom_b).astype(np.float32)

        # Approximate vegetation greenness ratio: (Green - Red) / (Green + Red + eps)
        g_t1 = (green_t1 - red_t1) / (green_t1 + red_t1 + eps)
        g_t2 = (green_t2 - red_t2) / (green_t2 + red_t2 + eps)
        delta_ndvi = (g_t2 - g_t1).astype(np.float32)
        delta_ndwi = np.zeros((height, width), dtype=np.float32)

    else:
        # 1 band grayscale
        bright_t1 = t1_data[0]
        bright_t2 = t2_data[0]
        denom_b = np.maximum(bright_t1, np.maximum(bright_t2, eps))
        delta_bright = ((bright_t2 - bright_t1) / denom_b).astype(np.float32)
        delta_ndvi = np.zeros((height, width), dtype=np.float32)
        delta_ndwi = np.zeros((height, width), dtype=np.float32)

    if valid_mask is not None:
        delta_ndvi[~valid_mask] = 0.0
        delta_ndwi[~valid_mask] = 0.0
        delta_bright[~valid_mask] = 0.0

    return {
        "delta_ndvi": delta_ndvi,
        "delta_ndwi": delta_ndwi,
        "delta_brightness": delta_bright,
    }


def compute_otsu_threshold(
    magnitude_map: np.ndarray,
    valid_mask: Optional[np.ndarray] = None,
    num_bins: int = 256,
    min_threshold: float = 0.15,
    max_threshold: float = 0.65,
) -> float:
    """Computes the optimal Otsu binarization threshold on the spectral magnitude map.

    Maximizes between-class variance sigma_b^2 = w0 * w1 * (mu0 - mu1)^2.
    Clamps result within [min_threshold, max_threshold] for satellite defense stability.
    """
    if valid_mask is not None:
        values = magnitude_map[valid_mask]
    else:
        values = magnitude_map.ravel()

    if len(values) == 0 or np.all(values == 0):
        return min_threshold

    # Calculate 256-bin histogram between 0.0 and 1.0
    hist, bin_edges = np.histogram(values, bins=num_bins, range=(0.0, 1.0), density=False)
    total_pixels = len(values)

    if total_pixels == 0:
        return min_threshold

    probabilities = hist / float(total_pixels)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0

    # Cumulative sums and cumulative means
    cum_weights = np.cumsum(probabilities)
    cum_means = np.cumsum(probabilities * bin_centers)
    global_mean = cum_means[-1]

    # Vectorized between-class variance calculation
    # Avoid division by zero when cum_weights is 0 or 1
    valid_bins = (cum_weights > 0) & (cum_weights < 1.0)
    w0 = cum_weights[valid_bins]
    w1 = 1.0 - w0
    mu0 = cum_means[valid_bins] / w0
    mu1 = (global_mean - cum_means[valid_bins]) / w1

    between_class_variance = w0 * w1 * ((mu0 - mu1) ** 2)

    if len(between_class_variance) == 0:
        return min_threshold

    best_idx = np.argmax(between_class_variance)
    optimal_threshold = float(bin_centers[valid_bins][best_idx])

    # Clamp threshold to stable range
    clamped_threshold = float(np.clip(optimal_threshold, min_threshold, max_threshold))
    return round(clamped_threshold, 4)
