import os
import random
import numpy as np
from sklearn.cluster import DBSCAN
from OpenGL.arrays import vbo
import open3d as o3d

from PyQt6.QtWidgets import (QDockWidget, QLineEdit, QVBoxLayout, QWidget, QPushButton, QLabel, QListWidget)
from PyQt6.QtCore import Qt, QRegularExpression, QThread, pyqtSignal
from PyQt6.QtGui import QRegularExpressionValidator


class SegmentationWorker(QThread):
    finished_with_segments = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, file_path, points_array, eps, min_samples):
        super().__init__()
        self.file_path = file_path
        self.points_array = points_array
        self.eps = eps
        self.min_samples = min_samples

    def run(self):
        try:
            db = DBSCAN(eps=self.eps, min_samples=self.min_samples).fit(self.points_array)
            labels = db.labels_
            segments = []

            for label in np.unique(labels):
                if label == -1:
                    continue

                segment_points = self.points_array[labels == label]
                segment_file_path = f"{self.file_path}_segment_{label}.pcd"
                colors = np.zeros((len(segment_points), 3))
                colors[:, 0] = random.random()
                colors[:, 1] = random.random()
                colors[:, 2] = random.random()
                segments.append((segment_file_path, segment_points, colors))

            self.finished_with_segments.emit(segments)
        except Exception as error:
            self.error.emit(str(error))


def segmentation_dock_widget(self):
    if 'segmentation' not in self.dock_widgets:
        segmentation_dock = QDockWidget("Сегментация деревьев")
        segmentation_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        widget = QWidget()
        layout = QVBoxLayout()
        # Список для выбора облака точек
        self.segmentation_list_widget = QListWidget()
        layout.addWidget(self.segmentation_list_widget)

        # Параметры для сегментации
        params_layout = QVBoxLayout()
        self.segmentation_eps_input = QLineEdit()
        self.segmentation_min_samples_input = QLineEdit()

        # Создаем валидатор для QLineEdit, который позволяет вводить только цифры и точку
        regex = QRegularExpression(r"^[0-9]*\.?[0-9]*$")
        validator = QRegularExpressionValidator(regex)

        self.segmentation_eps_input.setValidator(validator)
        self.segmentation_min_samples_input.setValidator(validator)

        params_layout.addWidget(QLabel("Epsilon (eps):"))
        params_layout.addWidget(self.segmentation_eps_input)
        params_layout.addWidget(QLabel("Min Samples:"))
        params_layout.addWidget(self.segmentation_min_samples_input)

        layout.addLayout(params_layout)

        # Кнопка запуска сегментации
        segmentation_run_button = QPushButton("Сегментировать")
        segmentation_run_button.clicked.connect(lambda: run_segmentation(self))
        layout.addWidget(segmentation_run_button)

        widget.setLayout(layout)
        segmentation_dock.setWidget(widget)
        self.dock_widgets['segmentation'] = segmentation_dock
    return self.dock_widgets['segmentation']

def run_segmentation(self):
    if getattr(self, '_segmentation_worker', None) and self._segmentation_worker.isRunning():
        print("Сегментация уже выполняется. Пожалуйста, дождитесь завершения.")
        return

    selected_items = self.segmentation_list_widget.selectedItems()
    if not selected_items:
        print("Не выбрано облако точек для сегментации")
        return

    file_path = selected_items[0].text()
    if not self.segmentation_eps_input.text() or not self.segmentation_min_samples_input.text():
        print("Ошибка: заполните параметры сегментации.")
        return

    eps = float(self.segmentation_eps_input.text())  # 0.78
    min_samples = int(float(self.segmentation_min_samples_input.text()))  # 132
    print(f"Сегментация запускается с eps: {eps} и min_samples: {min_samples}")

    points_array = get_points_array(self, file_path)
    if points_array is None:
        print(f"Ошибка: данные {file_path} не найдены или имеют некорректный формат.")
        return

    self._segmentation_worker = SegmentationWorker(file_path, points_array, eps, min_samples)

    def on_finished(segments):
        for segment_file_path, segment_points, colors in segments:
            print(segment_file_path)
            self.openGLWidget.point_clouds[segment_file_path] = {
                'active': True,
                'data': segment_points,
                'full_data': segment_points,
            }

            point_vbo = vbo.VBO(segment_points.astype(np.float32))
            color_vbo = vbo.VBO(colors.astype(np.float32))
            self.openGLWidget.vbo_data[segment_file_path] = (point_vbo, color_vbo, len(segment_points))
            self.add_file_to_list_widget(segment_file_path)

        self.openGLWidget.update()
        print(f"Сегментация завершена, найдено {len(segments)} компонентов")
        worker = self._segmentation_worker
        self._segmentation_worker = None
        worker.deleteLater()

    def on_error(error_msg):
        print(f"Ошибка сегментации: {error_msg}")
        worker = self._segmentation_worker
        self._segmentation_worker = None
        worker.deleteLater()

    self._segmentation_worker.finished_with_segments.connect(on_finished)
    self._segmentation_worker.error.connect(on_error)
    self._segmentation_worker.start()


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