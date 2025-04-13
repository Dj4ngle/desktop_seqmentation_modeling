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

        # Поля ввода для intensity_cut_make
        self.intensity_inputs = []
        default_values = ["7000", "5000", "1000"]

        for val in default_values:
            input_field = QLineEdit()
            input_field.setPlaceholderText("Введите интенсивность (например, 7000)")
            input_field.setText(val)

            regex = QRegularExpression(r"^\d+$")
            validator = QRegularExpressionValidator(regex)
            input_field.setValidator(validator)

            layout.addWidget(QLabel(f"Интенсивность:"))
            layout.addWidget(input_field)

            self.intensity_inputs.append(input_field)

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
        if not self.intensity_inputs:
            print("Ошибка: Не указана интенсивность обрезки точек.")
            return

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

        for input_field in self.intensity_inputs:
            if not input_field.text():
                print("Ошибка: одно из полей интенсивности не заполнено.")
                return
            intensity_cut_make = int(input_field.text())
            print(f"Запуск обнаружения координат с интенсивностью {intensity_cut_make} для {file_path}")
            coordinates.coordinates(intensity_cut_make, cs)

        merge_coordinates.merge_coordinates(cs)
        csv_output_file = clear_excess_stumps.clear_excess_stumps(cs)
        self.openGLWidget.load_point_cloud(csv_output_file)
        self.add_file_to_list_widget(csv_output_file)


    print("Обнаружение координат завершено.")
