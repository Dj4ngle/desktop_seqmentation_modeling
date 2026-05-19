import numpy as np


def _decode_pcd_text(data: bytes) -> str:
    for encoding in ("utf-8", "cp1251", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _extract_rgb_colors(data, rgb_index):
    rgb_values = np.asarray(data[:, rgb_index], dtype=np.float32).view(np.uint32).reshape(-1)
    red = ((rgb_values >> 16) & 0xFF).astype(np.float32)
    green = ((rgb_values >> 8) & 0xFF).astype(np.float32)
    blue = (rgb_values & 0xFF).astype(np.float32)
    colors = np.column_stack((red, green, blue))
    color_scale = 65535.0 if np.max(colors) > 255 else 255.0
    return np.clip(colors / color_scale, 0.0, 1.0)


def _field_index(fields, name):
    lowered = {field.lower(): index for index, field in enumerate(fields)}
    if name not in lowered:
        raise ValueError(f"В PCD отсутствует поле '{name}'")
    return lowered[name]


def _read_pcd_with_open3d(file_path):
    import open3d as o3d

    pcd = o3d.io.read_point_cloud(file_path)
    points = np.asarray(pcd.points, dtype=np.float32)
    if len(points) == 0:
        raise ValueError("PCD не содержит точек")
    if pcd.has_colors():
        colors = np.asarray(pcd.colors, dtype=np.float32)
    else:
        colors = np.ones((len(points), 3), dtype=np.float32)
    return points, colors, {"data": "open3d"}


def read_pcd_points_and_colors(file_path):
    """
    Read PCD file without Open3D when possible (Cyrillic paths, non-UTF8 headers).
    """
    try:
        return _read_pcd_with_py_pcd(file_path)
    except NotImplementedError:
        return _read_pcd_with_open3d(file_path)


def _read_pcd_with_py_pcd(file_path):
    from desktop_segmentation_modeling.classes.Py_PCD import PointCloudPCD

    cloud = PointCloudPCD.from_path(file_path)
    metadata = cloud.get_metadata()
    fields = metadata["fields"]
    data = cloud.pc_data.view(np.float32).reshape(cloud.pc_data.shape[0], -1)

    x_index = _field_index(fields, "x")
    points = data[:, x_index:x_index + 3].astype(np.float32)

    lowered = {field.lower(): index for index, field in enumerate(fields)}
    if "rgb" in lowered:
        colors = _extract_rgb_colors(data, lowered["rgb"])
    elif all(channel in lowered for channel in ("r", "g", "b")):
        colors = data[:, [lowered["r"], lowered["g"], lowered["b"]]].astype(np.float32)
        color_scale = 65535.0 if np.max(colors) > 255 else 255.0
        colors = np.clip(colors / color_scale, 0.0, 1.0)
    else:
        colors = np.ones((len(points), 3), dtype=np.float32)

    return points, colors, metadata


def get_pcd_file_properties(file_path):
    from desktop_segmentation_modeling.classes.Py_PCD import PointCloudPCD

    cloud = PointCloudPCD.from_path(file_path)
    metadata = cloud.get_metadata()
    fields = metadata.get("fields", [])
    has_rgb = "rgb" in fields or all(channel in fields for channel in ("r", "g", "b"))
    has_normals = all(axis in fields for axis in ("normal_x", "normal_y", "normal_z"))
    return [
        ("Цвета", "есть" if has_rgb else "нет"),
        ("Нормали", "есть" if has_normals else "нет"),
        ("Источник", "файл"),
        ("Точек", metadata.get("points", "неизвестно")),
        ("Формат данных", metadata.get("data", "неизвестно")),
    ]
