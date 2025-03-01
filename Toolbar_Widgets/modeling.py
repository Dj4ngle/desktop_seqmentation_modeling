import os

from PyQt6 import QtWidgets
from PyQt6.QtWidgets import (QDockWidget, QSlider, QVBoxLayout, QWidget, QPushButton, QLabel)
from PyQt6.QtCore import Qt

from Modeling.modeler import modeler
from Modeling.modeler2 import modeler2

# TODO починить
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
        self.method_radio_group.buttonClicked.connect(on_method_radio_button_clicked)

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
    button.clicked.connect(lambda: start_modeling(self, slider1.value(), slider2.value(),
                                                       slider3.value()) if method == "BPA" else start_modeling2(
        self, slider1.value(), slider2.value(), slider3.value()))

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

def start_modeling(self, slider1, slider2, slider3):
    # Метод для запуска моделирования
    selected_files = []
    for index in range(self.listWidget.count()):
        item = self.listWidget.item(index)
        checkbox = self.listWidget.itemWidget(item)
        if checkbox.isChecked():
            selected_files.append(checkbox.property("filePath"))
    print("Выбранные для моделирования файлы: ", selected_files)
    for file in selected_files:
        base_name, _ = os.path.splitext(file)
        new_file_path = base_name + '.obj'
        path = modeler(file, new_file_path, slider1, slider2, slider3)
        if path:
            self.openGLWidget.load_model(path)
            self.add_file_to_list_widget(path)



def start_modeling2(self, slider1, slider2, slider3):
    # Метод для запуска моделирования
    selected_files = []
    for index in range(self.listWidget.count()):
        item = self.listWidget.item(index)
        checkbox = self.listWidget.itemWidget(item)
        if checkbox.isChecked():
            selected_files.append(checkbox.property("filePath"))
    print("Выбранные для моделирования файлы: ", selected_files)
    for file in selected_files:
        base_name, _ = os.path.splitext(file)
        new_file_path = base_name + '.obj'
        path = modeler2(file, new_file_path, slider1, slider2, slider3)
        if path:
            self.openGLWidget.load_model(path)
            self.add_file_to_list_widget(path)

def on_method_radio_button_clicked(self, button):
    if button == self.bpa_radio:
        show_default_modeling_widget()
    elif button == self.mesh_radio:
        self.bpa_widget.hide()
        self.mesh_widget.show()
