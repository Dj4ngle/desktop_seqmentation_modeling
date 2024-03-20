import numpy as np
import open3d as o3d
import laspy


def read_las_file(filename):
    # Чтение .las файла
    las = laspy.read(filename)
    points = np.vstack((las.x, las.y, las.z)).transpose()

    # Создание объекта облака точек в Open3D
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)

    # Вычисление нормалей для облака точек
    pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30))

    return pcd


def reconstruct_surface_using_ball_pivoting(pcd):
    # Оценка радиусов для Ball Pivoting
    distances = pcd.compute_nearest_neighbor_distance()
    avg_dist = np.mean(distances)
    radius = 1.4 * avg_dist

    # Восстановление поверхности
    bpa_mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(pcd, o3d.utility.DoubleVector(
        [radius, radius * 2]))
    return bpa_mesh


def save_mesh_to_obj(mesh, filename):
    # Сохранение меша в .obj файл
    mesh.compute_vertex_normals()
    o3d.io.write_triangle_mesh(filename, mesh, write_ascii=True)


def modeler(las_filename, obj_filename):

    # Шаг 1: Чтение .las файла и преобразование в облако точек
    pcd = read_las_file(las_filename)

    # Шаг 2: Восстановление поверхности с помощью Ball Pivoting
    mesh = reconstruct_surface_using_ball_pivoting(pcd)

    # Шаг 3: Сохранение результата в .obj файл
    save_mesh_to_obj(mesh, obj_filename)

    # Опционально: Визуализация результата
    #o3d.visualization.draw_geometries([mesh])
