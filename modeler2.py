import os
import pyvista as pv
import numpy as np
import open3d as o3d
import laspy
import trimesh

def read_las_file(filename):
    # Чтение .las файла
    las = laspy.read(filename)
    points = np.vstack((las.x, las.y, las.z)).transpose()

    return points


def read_pcd_file(filename):
    # Чтение файла PCD
    pcd = o3d.io.read_point_cloud(filename)
    points_np = np.asarray(pcd.points)

    return points_np.shape


def reconstruct_surface_using_marching_cubes(points, alpha, radius_normals, max_nn):
    # Оценка радиуса для поиска ближайших соседей
    #pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=radius_normals, max_nn=max_nn))

    # Генерация случайного облака точек
    cloud = pv.PolyData(points)

    # Создание воксельной сетки на основе облака точек
    voxel_grid = cloud.delaunay_3d(alpha=alpha)

    # Применение Marching Cubes для извлечения поверхности
    surface = voxel_grid.extract_geometry()
    return surface


def visualize_mesh(mesh):
    # Визуализация результата
    o3d.visualization.draw_geometries([mesh])


def save_mesh_to_obj(mesh, filename):
    # Сохранение меша в .obj файл
    if isinstance(mesh, pv.core.pointset.PolyData):
        # Конвертируем из PyVista PolyData в trimesh Trimesh
        mesh_tri = trimesh.Trimesh(vertices=mesh.points, faces=mesh.faces.reshape((-1, 4))[:, 1:])
    else:
        # Предполагаем, что mesh уже в подходящем формате
        mesh_tri = mesh

        # Сохраняем файл
    mesh_tri.export(filename)


def modeler2(las_filename, obj_filename, slider1, slider2, slider3):
    # Шаг 1: Чтение .las файла и преобразование в облако точек
    _, original_ext = os.path.splitext(las_filename)
    if original_ext == '.pcd':
        #points = read_pcd_file(las_filename)
        print(f"Файл: {obj_filename} не формата .las его расширение: {original_ext}")
        return
    elif original_ext == '.las':
        points = read_las_file(las_filename)
    else:
        print(f"Файл: {obj_filename} не формата .las его расширение: {original_ext}")
        return

    radius_normals = float(slider1 / 100)
    max_nn = slider2
    alpha = slider3 / 1000

    # Шаг 2: Восстановление поверхности с помощью Marching Cubes
    mesh = reconstruct_surface_using_marching_cubes(points, alpha, radius_normals, max_nn)

    # Шаг 3: Сохранение результата в .obj файл
    save_mesh_to_obj(mesh, obj_filename)

    return obj_filename
