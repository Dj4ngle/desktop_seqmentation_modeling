import os

import open3d as o3d
import numpy as np

from OpenGL.arrays import vbo

from PyQt6.QtWidgets import (QDockWidget, QVBoxLayout, QWidget, QPushButton, QListWidget)
from PyQt6.QtCore import Qt

def ground_extraction_dock_widget(self):
    if 'ground_extraction' not in self.dock_widgets:
        dock = QDockWidget('Удаление земли')
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        widget = QWidget()
        layout = QVBoxLayout()

        self.clouds_list_widget = QListWidget()
        layout.addWidget(self.clouds_list_widget)

        run_button = QPushButton("Удалить землю")
        run_button.clicked.connect(lambda: run_ground_extraction(self))
        layout.addWidget(run_button)

        widget.setLayout(layout)
        dock.setWidget(widget)
        self.dock_widgets['ground_extraction'] = dock
    return self.dock_widgets['ground_extraction']


def run_ground_extraction(self):
    selected_items = self.clouds_list_widget.selectedItems()
    if not selected_items:
        print("Не выбрано облако точек для удаления земли")
        return
    if selected_items:
        file_path = selected_items[0].text()
        perform_ground_extraction(self, file_path)

def perform_ground_extraction(self, file_path):
    if file_path not in self.openGLWidget.point_clouds:
        print(f"Ошибка: Файл {file_path} отсутствует в point_clouds")
        return

    points = self.openGLWidget.point_clouds[file_path]['data']

    if points is None or not isinstance(points, np.ndarray) or points.shape[1] != 3:
        print(
            f"Ошибка: данные {file_path} некорректны. Ожидался массив (N, 3), получено {type(points)} с shape {points.shape if isinstance(points, np.ndarray) else 'None'}")
        return

    original_pcd = o3d.geometry.PointCloud()
    original_pcd.points = o3d.utility.Vector3dVector(points)

    # 0.3, 30, 0.1, 5
    # Оценка нормалей
    original_pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.3, max_nn=30))
    normals = np.asarray(original_pcd.normals)
    normal_threshold = 0.1
    height_offset = 5

    # Фильтрация нормалей и высоты
    idx_normals = np.where((abs(normals[:, 1]) < normal_threshold))
    idx_ground = np.where(points[:, 1] > np.min(points[:, 1]) + height_offset)
    idx_wronglyfiltered = np.setdiff1d(idx_ground[0], idx_normals[0])
    idx_retained = np.append(idx_normals[0], idx_wronglyfiltered)

    # Оставшиеся точки
    points_retained = points[idx_retained]

    # Точки земли
    idx_all = np.arange(points.shape[0])
    idx_inv = np.setdiff1d(idx_all, idx_retained)
    points_ground = points[idx_inv]

    # Создание облаков точек
    ground = o3d.geometry.PointCloud()
    ground.points = o3d.utility.Vector3dVector(points_ground)

    objects = o3d.geometry.PointCloud()
    objects.points = o3d.utility.Vector3dVector(points_retained)

    # Окрашивание точек земли
    colors_ground = np.zeros(points_ground.shape)
    colors_ground[:, 0] = 1
    colors_ground[:, 1] = 0.2
    colors_ground[:, 2] = 0.2
    ground.colors = o3d.utility.Vector3dVector(colors_ground)

    # Изменяем расширение файла и добавляем _ground и _objects
    file_extension = os.path.splitext(file_path)[1]
    ground_file_path = file_path.replace(file_extension, "_ground" + file_extension)
    ground_file_path = os.path.basename(ground_file_path)
    objects_file_path = file_path.replace(file_extension, "_objects" + file_extension)
    objects_file_path = os.path.basename(objects_file_path)

    print("Земля удалена. Исходное облако точек разделено на:\n" + ground_file_path + "\n" + objects_file_path)

    for k, v in self.openGLWidget.point_clouds.items():
        print(f"Ключ: {k} | Значение: {v}")
    # TODO починить код ниже
    # Добавляем результаты в виджет для визуализации
    self.openGLWidget.point_clouds[ground_file_path] = {'active': True, 'data': ground}
    ground_points = np.asarray(ground.points)
    ground_colors = np.asarray(ground.colors)
    point_vbo = vbo.VBO(ground_points.astype(np.float32))
    color_vbo = vbo.VBO(ground_colors.astype(np.float32))
    self.openGLWidget.vbo_data[ground_file_path] = (point_vbo, color_vbo, len(ground_points))
    self.openGLWidget.load_point_cloud(ground_file_path)
    self.add_file_to_list_widget(ground_file_path)

    self.openGLWidget.point_clouds[objects_file_path] = {'active': True, 'data': objects}
    objects_points = np.asarray(objects.points)
    objects_colors = np.ones_like(points)  # Белый цвет по умолчанию
    point_vbo = vbo.VBO(objects_points.astype(np.float32))
    color_vbo = vbo.VBO(objects_colors.astype(np.float32))
    self.openGLWidget.vbo_data[objects_file_path] = (point_vbo, color_vbo, len(objects_points))
    self.openGLWidget.load_point_cloud(objects_file_path)
    self.add_file_to_list_widget(objects_file_path)

    self.openGLWidget.update()