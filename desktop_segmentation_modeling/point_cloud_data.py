import numpy as np


def get_points_array_from_clouds(point_clouds, file_path):
    cloud_info = point_clouds.get(file_path)
    if not cloud_info:
        return None

    points = cloud_info.get('full_data')
    if points is None:
        points = cloud_info.get('data')

    if hasattr(points, 'points') and not isinstance(points, np.ndarray):
        points = np.asarray(points.points)
    elif points is not None:
        points = np.asarray(points)

    if points is None or points.ndim != 2 or points.shape[1] < 3 or len(points) == 0:
        return None

    return points[:, :3]
