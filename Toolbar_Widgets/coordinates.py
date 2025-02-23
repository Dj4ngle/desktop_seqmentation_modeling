import os
import numpy as np
import pandas as pd
from OpenGL.arrays import vbo
import open3d as o3d

from PyQt6.QtWidgets import (QDockWidget, QVBoxLayout, QWidget, QPushButton, QLabel, QListWidget, QLineEdit)
from PyQt6.QtCore import Qt, QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator

from Coordinates import coordinates, coord_settings


def coordinates_dock_widget(self):
    """Создает виджет для обнаружения координат пней."""
    if 'coordinates' not in self.dock_widgets:
        dock = QDockWidget("Обнаружение координат")
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        widget = QWidget()
        layout = QVBoxLayout()

        # Список облаков точек
        self.coordinates_list_widget = QListWidget()
        layout.addWidget(self.coordinates_list_widget)

        # Поле ввода для intensity_cut_make
        self.intensity_cut_input = QLineEdit()
        self.intensity_cut_input.setPlaceholderText("Введите интенсивность (напр. 7000)")
        self.intensity_cut_input.setText("7000")  # Устанавливаем значение по умолчанию

        # Валидатор для чисел
        regex = QRegularExpression(r"^\d+$")  # Только цифры
        validator = QRegularExpressionValidator(regex)
        self.intensity_cut_input.setValidator(validator)

        layout.addWidget(QLabel("Интенсивность обрезки точек:"))
        layout.addWidget(self.intensity_cut_input)

        # Кнопка запуска
        run_button = QPushButton("Обнаружить координаты")
        run_button.clicked.connect(lambda: run_coordinates(self))
        layout.addWidget(run_button)

        widget.setLayout(layout)
        dock.setWidget(widget)
        self.dock_widgets['coordinates'] = dock
    return self.dock_widgets['coordinates']


def run_coordinates(self):
    """Запускает процесс обнаружения координат деревьев."""
    selected_files = []
    for index in range(self.listWidget.count()):
        item = self.listWidget.item(index)
        checkbox = self.listWidget.itemWidget(item)
        if checkbox.isChecked():
            selected_files.append(checkbox.property("filePath"))
    if not selected_files:
        print("Ошибка: Не выбрано облако точек для обнаружения координат.")
        return

    file_path = selected_files[0]

    if not self.intensity_cut_input.text():
        print("Ошибка: Не указана интенсивность обрезки точек.")
        return

    intensity_cut_make = int(self.intensity_cut_input.text())

    print(f"Запуск обнаружения координат с интенсивностью {intensity_cut_make} для {file_path}")

    # Загружаем настройки CS
    cs = coord_settings.CS()
    cs.fname_points = file_path
    cs.path_base = os.path.dirname(file_path)

    created_files = coordinates.coordinates(intensity_cut_make, cs)

    # Загружаем файлы в OpenGL и добавляем в ListWidget
    for file_path in created_files:
        self.openGLWidget.load_point_cloud(file_path)
        self.add_file_to_list_widget(file_path)

    print("Обнаружение координат завершено.")
