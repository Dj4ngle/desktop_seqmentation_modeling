import json
import os
import re
import sys

import numpy as np
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import (QDockWidget, QSlider, QVBoxLayout, QWidget, QPushButton, QLabel)
from PyQt6.QtCore import Qt, QProcess


RESULT_PREFIX = "DSM_MODELING_RESULT="
ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")

def show_default_modeling_widget(self):
    self.bpa_widget.show()
    self.mesh_widget.hide()

def modeling_dock_widget(self):
    if not hasattr(self, 'modeling_dock'):
        self.modeling_dock = QDockWidget('Моделирование')
        self.modeling_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        widget = QWidget()
        layout = QVBoxLayout()

        # Создаем группу радиокнопок
        self.method_radio_group = QtWidgets.QButtonGroup()
        self.bpa_radio = QtWidgets.QRadioButton("BPA")
        self.mesh_radio = QtWidgets.QRadioButton("Mesh")
        self.method_radio_group.addButton(self.bpa_radio)
        self.method_radio_group.addButton(self.mesh_radio)
        self.bpa_radio.setChecked(True)

        # Подключение обработчика событий радиокнопок
        self.method_radio_group.buttonClicked.connect(
            lambda button: on_method_radio_button_clicked(self, button)
        )

        layout.addWidget(self.bpa_radio)
        layout.addWidget(self.mesh_radio)

        self.bpa_widget = create_specific_modeling_widget(self, "BPA")
        self.mesh_widget = create_specific_modeling_widget(self, "Mesh")

        # Добавляем виджеты в компоновку, но скрываем их
        layout.addWidget(self.bpa_widget)
        layout.addWidget(self.mesh_widget)
        show_default_modeling_widget(self)  # Показываем виджет по умолчанию

        widget.setLayout(layout)
        self.modeling_dock.setWidget(widget)
    return self.modeling_dock

def create_specific_modeling_widget(self, method):
    widget = QWidget()
    layout = QVBoxLayout()
    label = QLabel(f"Метод моделирования: {method}")

    # Создаем слайдер 1 для настройки радиуса нормалей
    slider1 = QSlider(Qt.Orientation.Horizontal)
    slider1.setRange(1, 100)  # Работаем с целыми числами для лучшей гранулярности
    slider1.setValue(10)  # Начальное значение 0.1 (10 / 100)
    label1 = QLabel(f"Радиус нормалей: {slider1.value() / 100:.2f}")
    slider1.valueChanged.connect(lambda value: label1.setText(f"Радиус нормалей: {value / 100:.2f}"))

    # Создаем слайдер 2 для максимального количества соседей
    slider2 = QSlider(Qt.Orientation.Horizontal)
    slider2.setRange(5, 100)
    slider2.setValue(30)
    label2 = QLabel(f"Макс. кол-во соседей: {slider2.value()}")
    slider2.valueChanged.connect(lambda value: label2.setText(f"Макс. кол-во соседей: {value}"))

    # Создаем слайдер 3 для настройки радиуса пивота или глубины
    slider3 = QSlider(Qt.Orientation.Horizontal)

    # Настройка слайдера в зависимости от метода
    if method == "BPA":
        slider3.setRange(10, 200)  # Диапазон для метода BPA
        slider3.setValue(140)  # Начальное значение 1.4 (140 / 100)
        label_text = f"Радиус пивота: {slider3.value() / 100:.1f}"
    else:
        slider3.setRange(1, 150)  # Диапазон для других методов
        slider3.setValue(5)  # Начальное значение 9
        label_text = f"Глубина: {slider3.value() / 1000:.3f}"

    # Создаем метку с текстом в зависимости от метода
    label3 = QLabel(label_text)

    # Подключаем сигнал изменения значения слайдера к слоту для обновления метки
    def update_label():
        if method == "BPA":
            label3.setText(f"Радиус пивота: {slider3.value() / 100:.1f}")
        else:
            label3.setText(f"Глубина: {slider3.value() / 1000:.3f}")

    slider3.valueChanged.connect(update_label)

    button = QPushButton("Моделировать")
    button.clicked.connect(
        lambda: start_modeling(self, slider1.value(), slider2.value(), slider3.value(), method)
    )

    layout.addWidget(label)
    layout.addWidget(label1)
    layout.addWidget(slider1)
    layout.addWidget(label2)
    layout.addWidget(slider2)
    layout.addWidget(label3)
    layout.addWidget(slider3)
    layout.addWidget(button)
    widget.setLayout(layout)
    widget.hide()  # Скрываем виджет

    return widget

def start_modeling(self, slider1, slider2, slider3, method="BPA"):
    # Метод для запуска моделирования
    if getattr(self, '_modeling_process', None) and self._modeling_process.state() != QProcess.ProcessState.NotRunning:
        print("Моделирование уже выполняется. Пожалуйста, дождитесь завершения.")
        return

    selected_files = []
    for index in range(self.listWidget.count()):
        item = self.listWidget.item(index)
        checkbox = self.listWidget.itemWidget(item)
        if checkbox.isChecked():
            selected_files.append(checkbox.property("filePath"))
    if not selected_files:
        print("Ошибка: Не выбраны файлы для моделирования.")
        return

    print("Выбранные для моделирования файлы: ", selected_files)

    self._modeling_results = []
    self._modeling_output_buffer = ""
    self._modeling_process = QProcess(self)
    self._modeling_process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

    def on_ready_read():
        output = bytes(self._modeling_process.readAllStandardOutput()).decode(
            "utf-8",
            errors="replace",
        )
        handle_modeling_output(self, output)

    def on_finished(exit_code, exit_status):
        if self._modeling_output_buffer:
            handle_modeling_output(self, "\n")

        if exit_status != QProcess.ExitStatus.NormalExit or exit_code != 0:
            print(f"Моделирование завершилось с ошибкой. Код: {exit_code}")
        else:
            for result in self._modeling_results:
                load_modeling_result(self, result)
            print("Моделирование завершено.")

        process = self._modeling_process
        self._modeling_process = None
        process.deleteLater()

    def on_error(error):
        print(f"Ошибка запуска процесса моделирования: {error}")

    self._modeling_process.readyReadStandardOutput.connect(on_ready_read)
    self._modeling_process.finished.connect(on_finished)
    self._modeling_process.errorOccurred.connect(on_error)

    args = [
        "-m",
        "desktop_segmentation_modeling.Modeling.modeling_process",
        method,
        str(slider1),
        str(slider2),
        str(slider3),
        *selected_files,
    ]
    print("Запуск моделирования в отдельном процессе...")
    self._modeling_process.start(sys.executable, args)


def start_modeling2(self, slider1, slider2, slider3):
    start_modeling(self, slider1, slider2, slider3, method="Mesh")


def load_modeling_results(self, result_paths):
    for path in result_paths:
        if path:
            self.openGLWidget.load_model(path)
            self.add_file_to_list_widget(path)


def handle_modeling_output(self, output):
    self._modeling_output_buffer += output
    lines = self._modeling_output_buffer.splitlines(keepends=True)

    if lines and not lines[-1].endswith(("\n", "\r")):
        self._modeling_output_buffer = lines.pop()
    else:
        self._modeling_output_buffer = ""

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith(RESULT_PREFIX):
            self._modeling_results.append(json.loads(line[len(RESULT_PREFIX):]))
        else:
            clean_line = ANSI_ESCAPE_PATTERN.sub("", line).strip()
            if clean_line:
                print(clean_line)


def load_modeling_result(self, result):
    obj_path = result["obj_path"]
    cache_path = result.get("cache_path")

    if cache_path and os.path.exists(cache_path):
        with np.load(cache_path) as cache:
            points = cache["points"]
        self.openGLWidget.load_model_from_arrays(obj_path, points)
        try:
            os.remove(cache_path)
        except OSError:
            pass
    else:
        self.openGLWidget.load_model(obj_path)

    self.add_file_to_list_widget(obj_path)

def on_method_radio_button_clicked(self, button):
    if button == self.bpa_radio:
        show_default_modeling_widget(self)
    elif button == self.mesh_radio:
        self.bpa_widget.hide()
        self.mesh_widget.show()
