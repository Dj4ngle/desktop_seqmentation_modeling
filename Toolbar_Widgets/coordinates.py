import os

from PyQt6.QtWidgets import (QDockWidget, QVBoxLayout, QWidget, QPushButton, QLabel, QListWidget, QLineEdit)
from PyQt6.QtCore import Qt, QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator

from Coordinates import coordinates, coord_settings, merge_coordinates, clear_excess_stumps


def coordinates_dock_widget(self):
    """Создает виджет для обнаружения координат пней."""
    if 'coordinates' not in self.dock_widgets:
        dock = QDockWidget("Обнаружение координат")
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        widget = QWidget()
        layout = QVBoxLayout()

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

    for file_path in selected_files:
        if not self.intensity_cut_input.text():
            print("Ошибка: Не указана интенсивность обрезки точек.")
            return

        intensity_cut_make = int(self.intensity_cut_input.text())

        print(f"Запуск обнаружения координат с интенсивностью {intensity_cut_make} для {file_path}")

        # Определяем абсолютный путь к текущему файлу
        script_path = os.path.abspath(__file__)
        # Определяем директорию, в которой находится этот файл
        script_dir = os.path.dirname(script_path)
        # Определяем родительскую директорию (папку, содержащую script_dir)
        parent_dir = os.path.dirname(script_dir)

        # Создаём путь к tmp внутри родительской директории
        tmp_dir = os.path.join(parent_dir, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)

        # Загружаем настройки CS
        cs = coord_settings.CS()
        cs.fname_points = file_path
        cs.path_base = tmp_dir

        coordinates.coordinates(intensity_cut_make, cs)
        # Также делаем прогон с интенсивностью 5000 и 1000
        coordinates.coordinates(5000, cs)
        coordinates.coordinates(1000, cs)


        merge_coordinates.merge_coordinates(cs)
        csv_output_file = clear_excess_stumps.clear_excess_stumps(cs)
        self.openGLWidget.load_point_cloud(csv_output_file)
        self.add_file_to_list_widget(csv_output_file)


    print("Обнаружение координат завершено.")
