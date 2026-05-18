import os

import open3d as o3d
import numpy as np

from OpenGL.arrays import vbo

from PyQt6.QtWidgets import (QDockWidget, QVBoxLayout, QWidget, QPushButton, QListWidget)
from PyQt6.QtCore import Qt, QThread, pyqtSignal


class GroundExtractionWorker(QThread):
    finished_with_result = pyqtSignal(str, str, object, object, object, object)
    error = pyqtSignal(str)

    def __init__(self, file_path, points):
        super().__init__()
        self.file_path = file_path
        self.points = points

    def run(self):
        try:
            original_pcd = o3d.geometry.PointCloud()
            original_pcd.points = o3d.utility.Vector3dVector(self.points)

            original_pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.3, max_nn=30))
            normals = np.asarray(original_pcd.normals)
            normal_threshold = 0.1
            height_offset = 5

            idx_normals = np.where((abs(normals[:, 1]) < normal_threshold))
            idx_ground = np.where(self.points[:, 1] > np.min(self.points[:, 1]) + height_offset)
            idx_wronglyfiltered = np.setdiff1d(idx_ground[0], idx_normals[0])
            idx_retained = np.append(idx_normals[0], idx_wronglyfiltered)

            points_retained = self.points[idx_retained]
            idx_all = np.arange(self.points.shape[0])
            idx_inv = np.setdiff1d(idx_all, idx_retained)
            points_ground = self.points[idx_inv]

            colors_ground = np.zeros(points_ground.shape)
            colors_ground[:, 0] = 1
            colors_ground[:, 1] = 0.2
            colors_ground[:, 2] = 0.2
            colors_objects = np.ones_like(points_retained)

            file_extension = os.path.splitext(self.file_path)[1]
            ground_file_path = os.path.basename(self.file_path.replace(file_extension, "_ground" + file_extension))
            objects_file_path = os.path.basename(self.file_path.replace(file_extension, "_objects" + file_extension))

            self.finished_with_result.emit(
                ground_file_path,
                objects_file_path,
                points_ground,
                colors_ground,
                points_retained,
                colors_objects,
            )
        except Exception as error:
            self.error.emit(str(error))

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
    if getattr(self, '_ground_extraction_worker', None) and self._ground_extraction_worker.isRunning():
        print("Удаление земли уже выполняется. Пожалуйста, дождитесь завершения.")
        return

    selected_items = self.clouds_list_widget.selectedItems()
    if not selected_items:
        print("Не выбрано облако точек для удаления земли")
        return
    if selected_items:
        file_path = selected_items[0].text()
        perform_ground_extraction(self, file_path)

def perform_ground_extraction(self, file_path):
    points = get_points_array(self, file_path)

    if points is None or not isinstance(points, np.ndarray) or points.shape[1] != 3:
        print(
            f"Ошибка: данные {file_path} некорректны. Ожидался массив (N, 3), получено {type(points)} с shape {points.shape if isinstance(points, np.ndarray) else 'None'}")
        return

    self._ground_extraction_worker = GroundExtractionWorker(file_path, points)

    def on_finished(ground_file_path, objects_file_path, ground_points, ground_colors, objects_points, objects_colors):
        print("Земля удалена. Исходное облако точек разделено на:\n" + ground_file_path + "\n" + objects_file_path)
        add_result_cloud(self, ground_file_path, ground_points, ground_colors)
        add_result_cloud(self, objects_file_path, objects_points, objects_colors)
        self.openGLWidget.update()
        worker = self._ground_extraction_worker
        self._ground_extraction_worker = None
        worker.deleteLater()

    def on_error(error_msg):
        print(f"Ошибка удаления земли: {error_msg}")
        worker = self._ground_extraction_worker
        self._ground_extraction_worker = None
        worker.deleteLater()

    self._ground_extraction_worker.finished_with_result.connect(on_finished)
    self._ground_extraction_worker.error.connect(on_error)
    print("Запуск удаления земли в фоновом потоке...")
    self._ground_extraction_worker.start()


def add_result_cloud(self, file_path, points, colors):
    self.openGLWidget.point_clouds[file_path] = {
        'active': True,
        'data': points,
        'full_data': points,
    }
    point_vbo = vbo.VBO(points.astype(np.float32))
    color_vbo = vbo.VBO(colors.astype(np.float32))
    self.openGLWidget.vbo_data[file_path] = (point_vbo, color_vbo, len(points))
    self.add_file_to_list_widget(file_path)


def get_points_array(self, file_path):
    cloud_info = self.openGLWidget.point_clouds.get(file_path)
    if not cloud_info:
        return None

    points = cloud_info.get('full_data')
    if points is None:
        points = cloud_info.get('data')

    if isinstance(points, o3d.geometry.PointCloud):
        points = np.asarray(points.points)
    elif points is not None:
        points = np.asarray(points)

    if points is None or points.ndim != 2 or points.shape[1] < 3:
        return None

    return points[:, :3]