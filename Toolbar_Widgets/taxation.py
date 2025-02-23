import os

import numpy as np
import open3d as o3d

from PyQt6.QtWidgets import (QDockWidget, QCheckBox, QVBoxLayout, QWidget, QPushButton, QLabel, QListWidget)
from PyQt6.QtCore import Qt

from OpenGL.raw.GL.VERSION.GL_1_5 import GL_ARRAY_BUFFER, glGetBufferSubData
from scipy.spatial import distance_matrix


def taxation_dock_widget(self):
    if 'taxation' not in self.dock_widgets:
        taxation_dock = QDockWidget("Таксация деревьев")
        taxation_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        widget = QWidget()
        layout = QVBoxLayout()

        # Список для выбора облака точек
        self.taxation_list_widget = QListWidget()
        layout.addWidget(self.taxation_list_widget)

        # Флажки для выбора метрик
        self.checkbox_dbh = QCheckBox("Диаметр на высоте груди")
        self.checkbox_height = QCheckBox("Высота")
        self.checkbox_volume = QCheckBox("Ширина кроны")

        layout.addWidget(self.checkbox_dbh)
        layout.addWidget(self.checkbox_height)
        layout.addWidget(self.checkbox_volume)

        # Кнопка для получения параметров
        get_parameters_button = QPushButton("Получить параметры")
        get_parameters_button.clicked.connect(lambda: get_taxation_parameters(self))
        layout.addWidget(get_parameters_button)

        # Поле для вывода результатов
        self.results_label = QLabel("")
        layout.addWidget(self.results_label)

        widget.setLayout(layout)
        taxation_dock.setWidget(widget)
        self.dock_widgets['taxation'] = taxation_dock
    return self.dock_widgets['taxation']

def get_taxation_parameters(self):
    selected_items = self.taxation_list_widget.selectedItems()
    if not selected_items:
        print("Не выбрано облако точек для таксации")
        return
    file_path = selected_items[0].text()

    results = []
    if self.checkbox_dbh.isChecked():
        results.append(f"Диаметр на высоте груди: {calc_diametr(self, file_path)/6}")
    if self.checkbox_height.isChecked():
        results.append(f"Высота: {calculate_height(self, file_path)}")
    if self.checkbox_volume.isChecked():
        results.append(f"Ширина кроны: {calculate_crown_width(self, file_path)}")

    if results:
        print("Результаты для облака точек:" + os.path.basename(file_path) + "\n" + "\n".join(results))
        self.results_label.setText("Результаты:\n" + "\n".join(results))
    else: self.results_label.setText("")

def calc_diametr(self, file_path):
    points = self.openGLWidget.vbo_data[file_path][0]
    points_array = points.reshape(-1, 3)
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points_array)
    # Создание матрицы поворота на 90 градусов вокруг оси X
    rotation_matrix = o3d.geometry.get_rotation_matrix_from_axis_angle([np.pi / 2, 0, 0])

    # Применение поворота к облаку точек
    pcd.rotate(rotation_matrix, center=(0, 0, 0))  # Поворот вокруг центра координат
    # Подсчёт точек на разных высотах
    intervals, counts = count_points_at_different_heights(pcd)

    # Поиск и вывод диаметра в наименее плотной части ствола
    least_dense_diameter = find_diameter_in_least_dense_part(pcd, intervals, counts)

    return least_dense_diameter

def calculate_height(self, file_path):
    # Получаем данные
    points = read_data_from_vbo(self.openGLWidget.vbo_data[file_path][0])

    # Преобразуем одномерный массив в двумерный формат (предполагая 3 координаты на точку)
    if points.ndim == 1:
        points = points.reshape(-1, 3)

    # Извлекаем координаты y для определения высоты
    heights = points[:, 1]
    min_height = np.min(heights)
    max_height = np.max(heights)
    tree_height = max_height - min_height

    return tree_height

def calculate_crown_width(self, file_path):
    # Пример функции для вычисления Volume
    points = read_data_from_vbo(self.openGLWidget.vbo_data[file_path][0])

    heights = points[:, 1]
    # Инициализируем переменную для диаметра
    max_diameter = 0

    # Проходим по всем уровням высоты и находим максимальное расстояние на каждом уровне
    unique_heights = np.unique(heights)
    for height in unique_heights:
        # Выбираем точки на данной высоте
        level_points = points[heights == height, :1]  # Игнорируем z координату

        # Вычисляем матрицу расстояний для точек на этом уровне
        distances = distance_matrix(level_points, level_points)

        # Находим максимальное расстояние на этом уровне
        max_diameter_at_level = np.max(distances)

        # Обновляем максимальный диаметр, если нашли большее значение
        if max_diameter_at_level > max_diameter:
            max_diameter = max_diameter_at_level

    return max_diameter

def count_points_at_different_heights(pcd, num_intervals=10):
    points = np.asarray(pcd.points)
    heights = points[:, 2]
    min_height = np.min(heights)
    max_height = np.max(heights)

    # Создание интервалов высоты
    intervals = np.linspace(min_height, max_height, num_intervals + 1)
    counts = np.zeros(num_intervals, dtype=int)

    # Подсчёт точек в каждом интервале
    interval_index = np.digitize(heights, intervals) - 1
    for i in range(num_intervals):
        counts[i] = np.sum(interval_index == i)

    return intervals, counts

def find_diameter_in_least_dense_part(pcd, intervals, counts):
    # Нахождение интервала с наименьшим количеством точек
    min_count_index = np.argmin(counts)
    lower_bound = intervals[min_count_index]
    upper_bound = intervals[min_count_index + 1]

    points = np.asarray(pcd.points)
    heights = points[:, 2]

    # Фильтрация точек в найденном диапазоне высот
    filtered_points = points[(heights >= lower_bound) & (heights <= upper_bound)]

    if filtered_points.size == 0:
        return 0

    # Расчёт максимального расстояния между точками в плоскости XY
    max_distance = 0
    for i in range(len(filtered_points)):
        for j in range(i + 1, len(filtered_points)):
            distance = np.linalg.norm(filtered_points[i][:2] - filtered_points[j][:2])
            if distance > max_distance:
                max_distance = distance

    return max_distance

def read_data_from_vbo(vbo_obj):
    vbo_obj.bind()
    data_buffer = np.empty(vbo_obj.data.size, dtype=np.float32)
    glGetBufferSubData(GL_ARRAY_BUFFER, 0, vbo_obj.data.nbytes, data_buffer)
    vbo_obj.unbind()
    # Предполагаем, что каждая вершина имеет 3 координаты (x, y, z)
    reshaped_data = data_buffer.reshape(-1, 3)  # Изменение формы массива
    return reshaped_data