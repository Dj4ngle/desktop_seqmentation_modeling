import os
import random
import numpy as np
from sklearn.cluster import DBSCAN
from OpenGL.arrays import vbo
import open3d as o3d

from PyQt6.QtWidgets import (QDockWidget, QLineEdit, QVBoxLayout, QWidget, QPushButton, QLabel, QListWidget)
from PyQt6.QtCore import Qt, QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator

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
    selected_items = self.segmentation_list_widget.selectedItems()
    if not selected_items:
        print("Не выбрано облако точек для сегментации")
        return

    file_path = selected_items[0].text()
    eps = float(self.segmentation_eps_input.text())  # 0.78
    min_samples = int(self.segmentation_min_samples_input.text())  # 132
    print(f"Сегментация запускается с eps: {eps} и min_samples: {min_samples}")

    # Загрузка и сегментация облака точек
    points = self.openGLWidget.vbo_data[file_path][0]
    points_array = points.reshape(-1, 3)
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points_array)

    db = DBSCAN(eps=eps, min_samples=min_samples).fit(points_array)
    labels = db.labels_

    # Создание и добавление сегментированных облаков точек в список и в VBO
    unique_labels = np.unique(labels)
    for label in unique_labels:
        if label == -1:
            continue  # Пропустить шум
        segment_points = points_array[labels == label]
        segment_file_path = f"{file_path}_segment_{label}.pcd"
        print(segment_file_path)
        self.openGLWidget.point_clouds[segment_file_path] = {'active': True, 'data': segment_points}

        # Создаем массив цветов для каждой точки в сегменте
        colors_ground = np.zeros((len(segment_points), 3))  # создаем массив для RGB значений
        colors_ground[:, 0] = random.random()  # случайный красный компонент для всех точек сегмента
        colors_ground[:, 1] = random.random()  # случайный зеленый компонент
        colors_ground[:, 2] = random.random()  # случайный синий компонент

        # Добавление в список и в VBO
        objects_points = segment_points
        objects_colors = colors_ground  # Белый цвет по умолчанию
        point_vbo = vbo.VBO(objects_points.astype(np.float32))
        color_vbo = vbo.VBO(objects_colors.astype(np.float32))
        self.openGLWidget.vbo_data[segment_file_path] = (point_vbo, color_vbo, len(objects_points))

        self.openGLWidget.load_point_cloud(segment_file_path)
        self.add_file_to_list_widget(segment_file_path)

    print(f"Сегментация завершена, найдено {len(unique_labels)} компонентов")