from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import (QApplication, QMainWindow, QDockWidget, QTextEdit, QListWidgetItem, QCheckBox, QRadioButton, QSlider, QSizePolicy, QLineEdit,
                             QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel, QToolBar, QMenu, QStatusBar, QListWidget, QPlainTextEdit, QButtonGroup )

from modeler import modeler
from modeler2 import modeler2
from point_cloud_widget import OpenGLWidget
from PyQt6.QtCore import Qt, QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator
from datetime import datetime, timedelta
import os
        
class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.setWindowTitle("LIDAR segmentation and modeling")
        MainWindow.resize(1600, 900)
        # Центральный виджет
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.centralwidget.setProperty("class", "custom-widget")
        # Создаем вертикальную компоновку для centralwidget
        self.centralLayout = QVBoxLayout(self.centralwidget)
        self.centralLayout.setContentsMargins(0, 0, 0, 0)  # Убираем отступы
        
        self.openGLWidget = OpenGLWidget(parent=self.centralwidget)
        self.openGLWidget.setObjectName("openGLWidget")
        self.centralLayout.addWidget(self.openGLWidget)
        
        
        MainWindow.setCentralWidget(self.centralwidget)

        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        
        # Стыковочные виджеты
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.files_dock_widget())
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.properties_dock_widget())

    def update_list(self, list):
        
        list.clear()
        for file_name in self.openGLWidget.point_clouds:
            if self.openGLWidget.point_clouds[file_name]['active']:
                list.addItem(file_name)
            
    def init_dock_widgets(self):
        self.dock_widgets = {
            'ground_extraction': self.ground_extraction_dock_widget(),
            'segmentation': self.segmentation_dock_widget(),
            'taxation': self.taxation_dock_widget(),
            'modeling': self.modeling_dock_widget()
        }

    def properties_dock_widget(self):
        dock = QDockWidget('Свойства')
        dock.setAllowedAreas(QtCore.Qt.DockWidgetArea.AllDockWidgetAreas)
        widget = QWidget()
        layout = QVBoxLayout()
        self.properties_layout = layout  # Сохраняем ссылку на layout для обновления
        widget.setLayout(layout)
        dock.setWidget(widget)
        return dock
    
    def files_dock_widget(self):
        dock = QDockWidget('Файлы')
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        widget = QWidget()
        layout = QVBoxLayout()  # Используем вертикальную компоновку

        # Добавляем QListWidget
        self.listWidget = QListWidget()
        layout.addWidget(self.listWidget)

        # Создаем горизонтальную компоновку для кнопок
        buttons_layout = QHBoxLayout()

        # Добавляем кнопку "Выбрать всё"
        self.select_all_button = QPushButton("Выбрать всё")
        buttons_layout.addWidget(self.select_all_button)

        # Добавляем кнопку "Удалить"
        self.remove_button = QPushButton("Удалить")
        buttons_layout.addWidget(self.remove_button)

        # Добавляем горизонтальную компоновку кнопок в вертикальную компоновку
        layout.addLayout(buttons_layout)

        widget.setLayout(layout)
        dock.setWidget(widget)
        return dock

    def ground_extraction_dock_widget(self):
        if 'ground_extraction' not in self.dock_widgets:
            dock = QDockWidget('Удаление земли')
            dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
            widget = QWidget()
            layout = QVBoxLayout()

            self.clouds_list_widget = QListWidget()
            layout.addWidget(self.clouds_list_widget)

            run_button = QPushButton("Удалить землю")
            run_button.clicked.connect(self.run_ground_extraction)
            layout.addWidget(run_button)

            widget.setLayout(layout)
            dock.setWidget(widget)
            self.dock_widgets['ground_extraction'] = dock
        return self.dock_widgets['ground_extraction']


    def run_ground_extraction(self):
        selected_items = self.clouds_list_widget.selectedItems()
        if selected_items:
            file_path = selected_items[0].text()
            self.perform_ground_extraction(file_path)
            
            # Определяем расширение файла
            file_extension = os.path.splitext(file_path)[1]
            
            # Формируем пути к облакам точек земли и объектов
            ground_cloud_path = file_path.replace(file_extension, "_ground" + file_extension)
            objects_cloud_path = file_path.replace(file_extension, "_objects" + file_extension)
            
            # Добавляем облако точек земли в list_widget
            ground_item = QListWidgetItem(self.listWidget)
            ground_checkbox = QCheckBox(ground_cloud_path)
            ground_checkbox.setChecked(True)
            ground_checkbox.setProperty("filePath", ground_cloud_path)
            self.listWidget.setItemWidget(ground_item, ground_checkbox)
            ground_item.setSizeHint(ground_checkbox.sizeHint())
            ground_checkbox.stateChanged.connect(self.checkbox_changed)
            
            # Добавляем облако точек объектов в list_widget
            self.add_file_to_list_widget(objects_cloud_path)
        
        self.clouds_list_widget.clear()

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
            segmentation_run_button.clicked.connect(self.run_segmentation)
            layout.addWidget(segmentation_run_button)

            widget.setLayout(layout)
            segmentation_dock.setWidget(widget)
            self.dock_widgets['segmentation'] = segmentation_dock
        return self.dock_widgets['segmentation']

    
    def taxation_dock_widget(self):
        dock = QDockWidget('Таксация')
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        widget = QWidget()
        layout = QVBoxLayout()
        label = QLabel(f"Наполнение таксации")
        button = QPushButton("ОК")
        layout.addWidget(label)
        layout.addWidget(button)
        widget.setLayout(layout)
        dock.setWidget(widget)
        return dock

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
            self.method_radio_group.buttonClicked.connect(self.on_method_radio_button_clicked)

            layout.addWidget(self.bpa_radio)
            layout.addWidget(self.mesh_radio)

            self.bpa_widget = self.create_specific_modeling_widget("BPA")
            self.mesh_widget = self.create_specific_modeling_widget("Mesh")

            # Добавляем виджеты в компоновку, но скрываем их
            layout.addWidget(self.bpa_widget)
            layout.addWidget(self.mesh_widget)
            self.show_default_modeling_widget()  # Показываем виджет по умолчанию

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
        button.clicked.connect(lambda: self.start_modeling(slider1.value(), slider2.value(),
                                                           slider3.value()) if method == "BPA" else self.start_modeling2(
            slider1.value(), slider2.value(), slider3.value()))

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
        #Метод для запуска моделирования
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
            self.show_default_modeling_widget()
        elif button == self.mesh_radio:
            self.bpa_widget.hide()
            self.mesh_widget.show()

    def show_default_modeling_widget(self):
        self.bpa_widget.show()
        self.mesh_widget.hide()

    def add_file_to_list_widget(self, file_path):
        # Добавляем облако точек земли в list_widget
        ground_item = QListWidgetItem(self.listWidget)
        ground_checkbox = QCheckBox(file_path)
        ground_checkbox.setChecked(True)
        ground_checkbox.setProperty("filePath", file_path)
        self.listWidget.setItemWidget(ground_item, ground_checkbox)
        ground_item.setSizeHint(ground_checkbox.sizeHint())
        ground_checkbox.stateChanged.connect(self.checkbox_changed)