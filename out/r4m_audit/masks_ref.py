"""Otsu body masks, extent rule and Dice, for volumes laid out (H, W, D)."""
from __future__ import annotations

import numpy as np
from scipy import ndimage

BORDER_PX = 5


def otsu_from_hist(h: np.ndarray) -> int:
    """Otsu bin index from a 256-bin histogram (class 0 = bins <= index)."""
    p = h.astype(np.float64) / h.sum()
    w0, m = np.cumsum(p), np.cumsum(p * np.arange(256))
    with np.errstate(divide="ignore", invalid="ignore"):
        between = (m[-1] * w0 - m) ** 2 / (w0 * (1 - w0))
    return int(np.nanargmax(between))


def otsu_threshold(vol: np.ndarray) -> float:
    """Otsu threshold of the whole volume on a 256-bin histogram (values rescaled to 0..255 if needed)."""
    lo, hi = float(vol.min()), float(vol.max())
    if not hi > lo:
        raise ValueError("constant_volume")
    q = vol if (lo >= 0 and hi <= 255) else (vol - lo) * (255.0 / (hi - lo))
    t = otsu_from_hist(np.bincount(np.clip(np.rint(q), 0, 255).astype(np.uint8).ravel(), minlength=256))
    # return the upper edge of bin t, so float values that round into bin t stay in class 0 when compared with "<= thr"
    return t + 0.5 if (lo >= 0 and hi <= 255) else (t + 0.5) * (hi - lo) / 255.0 + lo


def foreground_is_bright(vol: np.ndarray, thr: float) -> bool:
    """Polarity from the frame border (assumed background): background above the threshold => body is dark."""
    b = BORDER_PX
    ring = np.concatenate([vol[:b].ravel(), vol[-b:].ravel(), vol[:, :b].ravel(), vol[:, -b:].ravel()])
    return not (np.median(ring) > thr)


def body_mask(slice2d: np.ndarray, thr: float, bright: bool) -> np.ndarray:
    """Otsu foreground -> largest 8-connected component -> holes filled."""
    raw = slice2d > thr if bright else slice2d <= thr
    lab, n = ndimage.label(raw, structure=np.ones((3, 3)))
    if n == 0:
        return np.zeros_like(raw)
    sizes = ndimage.sum(raw, lab, index=np.arange(1, n + 1))
    return ndimage.binary_fill_holes(lab == (1 + int(np.argmax(sizes))))


def dice(a: np.ndarray, b: np.ndarray) -> float:
    s = a.sum() + b.sum()
    return float(2.0 * np.logical_and(a, b).sum() / s) if s else float("nan")


# ---------------------------------------------------------------- mask_v2 (cryosection, colour distance)
MAX_RGB_DIST = float(np.sqrt(3) * 255)


def border_colour(rgb: np.ndarray) -> np.ndarray:
    """Median RGB of the frame border ring of one slice (H, W, 3)."""
    b = BORDER_PX
    ring = np.concatenate([rgb[:b].reshape(-1, 3), rgb[-b:].reshape(-1, 3), rgb[:, :b].reshape(-1, 3),
                           rgb[:, -b:].reshape(-1, 3)])
    return np.median(ring, axis=0)


def colour_distance(rgb: np.ndarray, bg: np.ndarray) -> np.ndarray:
    return np.sqrt(((rgb.astype(np.float32) - bg.astype(np.float32)) ** 2).sum(-1))


def distance_otsu(dist_slices) -> float:
    """Otsu threshold (in distance units) over the histogram of all slices' colour distances."""
    h = np.zeros(256)
    for d in dist_slices:
        h += np.bincount(np.clip(np.rint(d * (255.0 / MAX_RGB_DIST)), 0, 255).astype(np.uint8).ravel(), minlength=256)
    return (otsu_from_hist(h) + 0.5) * MAX_RGB_DIST / 255.0  # upper edge of the class-0 bin


def largest_filled(raw: np.ndarray) -> np.ndarray:
    lab, n = ndimage.label(raw, structure=np.ones((3, 3)))
    if n == 0:
        return np.zeros_like(raw, dtype=bool)
    sizes = ndimage.sum(raw, lab, index=np.arange(1, n + 1))
    return ndimage.binary_fill_holes(lab == (1 + int(np.argmax(sizes))))


def disk(radius: int) -> np.ndarray:
    r = np.arange(-radius, radius + 1)
    return np.hypot(*np.meshgrid(r, r, indexing="ij")) <= radius


def opened_largest(mask: np.ndarray, radius: int) -> np.ndarray:
    """Holder check: morphological opening removes thin structures; keep the largest component."""
    op = ndimage.binary_opening(mask, structure=disk(radius))
    return largest_filled(op)
