"""AstraTrace Baseline Change Detection Package.

SIH 2026 | Problem ID: SIH26227
Deterministic bitemporal satellite image differencing, spectral index deltas,
pure NumPy morphological filtering, and change taxonomy categorization.
"""
from apps.backend.app.services.change.differencing import (
    compute_spectral_difference,
    compute_index_deltas,
    compute_otsu_threshold,
)
from apps.backend.app.services.change.morphology import (
    binary_erosion,
    binary_dilation,
    binary_opening,
    binary_closing,
    filter_small_components,
)
from apps.backend.app.services.change.detector import BaselineChangeDetector
from apps.backend.app.services.change.service import ChangeDetectionService

__all__ = [
    "compute_spectral_difference",
    "compute_index_deltas",
    "compute_otsu_threshold",
    "binary_erosion",
    "binary_dilation",
    "binary_opening",
    "binary_closing",
    "filter_small_components",
    "BaselineChangeDetector",
    "ChangeDetectionService",
]
