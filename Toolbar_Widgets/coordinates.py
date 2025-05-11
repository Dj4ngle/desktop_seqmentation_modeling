import os

from PyQt6.QtWidgets import (QDockWidget, QVBoxLayout, QWidget, QPushButton, QLabel, QComboBox, QLineEdit, QCheckBox)
from PyQt6.QtCore import Qt, QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator

from Coordinates import coordinates, coord_settings, merge_coordinates, clear_excess_stumps
from Segmentation import seg_settings, segmentation_vor, segmentation_ram, segmentation_clear


def coordinates_dock_widget(self):
    """Создает виджет для обнаружения координат пней."""
    if 'coordinates' not in self.dock_widgets:
        dock = QDockWidget("Обнаружение координат")
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        widget = QWidget()
        layout = QVBoxLayout()

        # Флажки для выбора метода сегментации
        self.checkbox_vot = QCheckBox("Segmentation Voronoi")
        self.checkbox_ram = QCheckBox("Segmentation RAM")
        self.checkbox_clear = QCheckBox("Segmentation Clear")

        layout.addWidget(self.checkbox_vot)
        layout.addWidget(self.checkbox_ram)
        layout.addWidget(self.checkbox_clear)

        # Выпадающий список
        self.intensity_selection = QComboBox()
        self.intensity_selection.addItems(["-1", "0", "1"])  # Добавляем элементы в выпадающий список
        layout.addWidget(QLabel("Порог:"))
        layout.addWidget(self.intensity_selection)

        # Поля ввода для intensity_cut_make
        self.intensity_inputs = []
        self.multiplier_input = QLineEdit()
        self.multiplier_input.setPlaceholderText("Введите множитель (например, 2)")
        self.multiplier_input.setText("1")  # Default value

        regex = QRegularExpression(r"^\d+$")
        validator = QRegularExpressionValidator(regex)
        self.multiplier_input.setValidator(validator)

        layout.addWidget(QLabel("Нужное количество:"))
        layout.addWidget(self.multiplier_input)

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

    multiplier = int(self.multiplier_input.text())

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

        # мерджим координаты
        merge_coordinates.merge_coordinates(cs)
        csv_output_file = clear_excess_stumps.clear_excess_stumps(cs)
        self.openGLWidget.load_point_cloud(csv_output_file)
        self.add_file_to_list_widget(csv_output_file)

        # Загружаем настройки SS
        ss = seg_settings.SS()
        ss.fname_points = file_path
        ss.path_base = tmp_dir
        ss.csv_name_coord = csv_output_file

        # Проводим сегментацию
        tr_val = int(self.intensity_selection.currentText())

        # Вызываем только выбранные методы
        if self.checkbox_clear.isChecked():
            segmented_files_vot = segmentation_vor.segmentation_vor(ss, tr_val, multiplier, make_binding=True)
            for file in segmented_files_vot:
                self.openGLWidget.load_point_cloud(file)
                self.add_file_to_list_widget(file)
            segmented_files_ram = segmentation_ram.segmentation_ram(ss, tr_val, multiplier)
            for file in segmented_files_ram:
                self.openGLWidget.load_point_cloud(file)
                self.add_file_to_list_widget(file)
            segmented_files_clear = segmentation_clear.segmentation_clear(ss, tr_val, multiplier)
            for file in segmented_files_clear:
                self.openGLWidget.load_point_cloud(file)
                self.add_file_to_list_widget(file)
        elif self.checkbox_ram.isChecked():
            segmented_files_vot = segmentation_vor.segmentation_vor(ss, tr_val, multiplier, make_binding=True)
            for file in segmented_files_vot:
                self.openGLWidget.load_point_cloud(file)
                self.add_file_to_list_widget(file)
            segmented_files_ram = segmentation_ram.segmentation_ram(ss, tr_val, multiplier)
            for file in segmented_files_ram:
                self.openGLWidget.load_point_cloud(file)
                self.add_file_to_list_widget(file)
        elif self.checkbox_vot.isChecked():
            segmented_files_vot = segmentation_vor.segmentation_vor(ss, tr_val, multiplier, make_binding=True)
            for file in segmented_files_vot:
                self.openGLWidget.load_point_cloud(file)
                self.add_file_to_list_widget(file)


    print("Обнаружение координат завершено.")
