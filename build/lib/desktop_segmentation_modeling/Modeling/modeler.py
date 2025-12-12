import os

import numpy as np
import open3d as o3d
import laspy


def read_las_file(filename, radius_normals, max_nn):
    # Чтение .las файла
    las = laspy.read(filename)
    points = np.vstack((las.x, las.y, las.z)).transpose()

    # Создание объекта облака точек в Open3D
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)

    # Вычисление нормалей для облака точек
    pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius_normals, max_nn))

    return pcd
def read_pcd_file(filename, radius_normals, max_nn):
    # Чтение файла PCD
    pcd = o3d.io.read_point_cloud(filename)

    # Вычисление нормалей
    pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=radius_normals, max_nn=max_nn))

    return pcd


def reconstruct_surface_using_ball_pivoting(pcd, radius_pivot):
    # Оценка радиусов для Ball Pivoting
    distances = pcd.compute_nearest_neighbor_distance()
    avg_dist = np.mean(distances)
    radius = radius_pivot * avg_dist

    # Восстановление поверхности
    bpa_mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(pcd, o3d.utility.DoubleVector(
        [radius, radius * 2]))
    return bpa_mesh


def save_mesh_to_obj(mesh, filename):
    # Сохранение меша в .obj файл
    mesh.compute_vertex_normals()
    o3d.io.write_triangle_mesh(filename, mesh, write_ascii=True)


def modeler(las_filename, obj_filename, slider1, slider2, slider3):
    radius_normals = float(slider1 / 100)
    max_nn = slider2
    radius_pivot = float(slider3 / 100)

    # Шаг 1: Чтение .las файла и преобразование в облако точек
    _, original_ext = os.path.splitext(las_filename)
    if original_ext == '.pcd':
        pcd = read_pcd_file(las_filename, radius_normals, max_nn)
    elif original_ext == '.las':
        pcd = read_las_file(las_filename, radius_normals, max_nn)
    else:
        print(f"Файл: {obj_filename} не формата .las его расширение: {original_ext}")
        return

    # Шаг 2: Восстановление поверхности с помощью Ball Pivoting
    mesh = reconstruct_surface_using_ball_pivoting(pcd, radius_pivot)

    # Шаг 3: Сохранение результата в .obj файл
    save_mesh_to_obj(mesh, obj_filename)

    return obj_filename

    # Опционально: Визуализация результата
    #o3d.visualization.draw_geometries([mesh])
