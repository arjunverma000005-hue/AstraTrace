"""Pure NumPy Mathematical Morphology for Raster Noise Suppression.

SIH 2026 | Problem ID: SIH26227
Implements binary erosion, dilation, opening, closing, and connected-component
area filtering without heavy OpenCV or SciPy C-library dependencies.
"""
from collections import deque
from typing import List, Tuple
import numpy as np


def _get_offsets(kernel_size: int) -> List[Tuple[int, int]]:
    """Returns list of relative (di, dj) offsets for a square kernel."""
    r = kernel_size // 2
    return [(di, dj) for di in range(-r, r + 1) for dj in range(-r, r + 1)]


def binary_erosion(mask: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    """Computes binary erosion using pure vectorized NumPy sliding slices.

    A pixel remains 1 if and only if all neighbors in the kernel are 1.
    """
    h, w = mask.shape
    r = kernel_size // 2
    padded = np.pad(mask.astype(bool), r, mode="constant", constant_values=False)

    slices = [padded[r + di : r + di + h, r + dj : r + dj + w] for di, dj in _get_offsets(kernel_size)]
    eroded = np.logical_and.reduce(slices)
    return eroded.astype(bool)


def binary_dilation(mask: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    """Computes binary dilation using pure vectorized NumPy sliding slices.

    A pixel becomes 1 if any neighbor in the kernel is 1.
    """
    h, w = mask.shape
    r = kernel_size // 2
    padded = np.pad(mask.astype(bool), r, mode="constant", constant_values=False)

    slices = [padded[r + di : r + di + h, r + dj : r + dj + w] for di, dj in _get_offsets(kernel_size)]
    dilated = np.logical_or.reduce(slices)
    return dilated.astype(bool)


def binary_opening(mask: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    """Computes binary opening (erosion followed by dilation).

    Removes small isolated noise specks and thin protrusions.
    """
    return binary_dilation(binary_erosion(mask, kernel_size), kernel_size)


def binary_closing(mask: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    """Computes binary closing (dilation followed by erosion).

    Fills small internal voids, holes, and breaks within structural shapes.
    """
    return binary_erosion(binary_dilation(mask, kernel_size), kernel_size)


def filter_small_components(mask: np.ndarray, min_pixels: int = 10) -> np.ndarray:
    """Removes connected components containing fewer than `min_pixels` using 8-connectivity.

    Suppresses false-alarm sensor jitter while preserving cohesive building footprints.
    """
    if min_pixels <= 1:
        return mask.astype(bool)

    h, w = mask.shape
    visited = np.zeros((h, w), dtype=bool)
    filtered = mask.copy().astype(bool)

    # 8-connectivity neighbor shifts
    neighbors = [
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1),           (0, 1),
        (1, -1),  (1, 0),  (1, 1),
    ]

    # Find all 1-pixels
    ones_y, ones_x = np.where(filtered)

    for start_y, start_x in zip(ones_y, ones_x):
        if visited[start_y, start_x]:
            continue

        # BFS to discover the entire connected component
        component = []
        queue = deque([(start_y, start_x)])
        visited[start_y, start_x] = True

        while queue:
            cy, cx = queue.popleft()
            component.append((cy, cx))

            for dy, dx in neighbors:
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < h and 0 <= nx < w:
                    if filtered[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        queue.append((ny, nx))

        # If component is smaller than threshold, zero it out
        if len(component) < min_pixels:
            for py, px in component:
                filtered[py, px] = False

    return filtered
