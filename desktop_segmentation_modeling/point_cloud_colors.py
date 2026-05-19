import numpy as np


def build_colors_from_intensity(intensity):
    intensity = np.asarray(intensity, dtype=np.float32)
    min_value = float(np.min(intensity))
    max_value = float(np.max(intensity))
    normalized = (intensity - min_value) / (max_value - min_value + 1e-6)
    return np.stack([normalized, normalized, normalized], axis=1).astype(np.float32)


def should_use_intensity_colors(colors):
    colors = np.asarray(colors, dtype=np.float32)
    if colors.size == 0:
        return True
    luminance = _relative_luminance(colors.reshape(-1, 3))
    return float(np.median(luminance)) < 0.04 or float(np.max(luminance)) < 0.08


def _relative_luminance(colors):
    return (
        colors[:, 0] * 0.2126
        + colors[:, 1] * 0.7152
        + colors[:, 2] * 0.0722
    )


def adapt_point_colors_for_theme(colors, light_background):
    """
    Adjust point colors for contrast against the current viewport background.
    Preserves hue; scales brightness when the cloud is too dark or too light.
    """
    colors = np.asarray(colors, dtype=np.float32)
    if colors.size == 0:
        return colors

    if colors.ndim == 1:
        colors = colors.reshape(-1, 3)

    colors = np.clip(colors, 0.0, 1.0)
    luminance = _relative_luminance(colors)
    median_lum = float(np.median(luminance))
    max_lum = float(np.max(luminance))

    if max_lum < 1e-4:
        # Almost no color information — neutral visible gray ramp
        if light_background:
            base = 0.12
        else:
            base = 0.82
        return np.full((len(colors), 3), base, dtype=np.float32)

    if light_background:
        target_median = 0.38
        upper_trigger = 0.62
        if median_lum > upper_trigger:
            scale = target_median / max(median_lum, 1e-6)
            scale = min(scale, 1.0)
            return np.clip(colors * scale, 0.0, 1.0).astype(np.float32)
        if median_lum > 0.48:
            scale = min(0.48 / max(median_lum, 1e-6), 1.0)
            return np.clip(colors * scale, 0.0, 1.0).astype(np.float32)
        return colors.copy()

    target_median = 0.68
    lower_trigger = 0.28
    if median_lum < lower_trigger:
        scale = target_median / max(median_lum, 1e-6)
        scale = min(scale, 5.0)
        return np.clip(colors * scale, 0.0, 1.0).astype(np.float32)
    if median_lum < 0.45:
        scale = min(0.55 / max(median_lum, 1e-6), 2.5)
        return np.clip(colors * scale, 0.0, 1.0).astype(np.float32)
    return colors.copy()
