from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import (QApplication, QMainWindow, QDockWidget, QTextEdit, QListWidgetItem, QCheckBox, QRadioButton, QSlider, QSizePolicy,
                             QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel, QToolBar, QMenu, QStatusBar, QListWidget, QPlainTextEdit, QButtonGroup )
from point_cloud_widget import OpenGLWidget
from PyQt6.QtCore import Qt
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

    def update_clouds_list(self):
        self.clouds_list_widget.clear()
        for file_name in self.openGLWidget.point_clouds:
            self.clouds_list_widget.addItem(file_name)

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
            objects_item = QListWidgetItem(self.listWidget)
            objects_checkbox = QCheckBox(objects_cloud_path)
            objects_checkbox.setChecked(True)
            objects_checkbox.setProperty("filePath", objects_cloud_path)
            self.listWidget.setItemWidget(objects_item, objects_checkbox)
            objects_item.setSizeHint(objects_checkbox.sizeHint())
            objects_checkbox.stateChanged.connect(self.checkbox_changed)
        
        self.clouds_list_widget.clear()

 
    
    def segmentation_dock_widget(self):
        dock = QDockWidget('Сегментация')
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        widget = QWidget()
        layout = QVBoxLayout()
        label = QLabel(f"Наполнение сегментации")
        button = QPushButton("ОК")
        layout.addWidget(label)
        layout.addWidget(button)
        widget.setLayout(layout)
        dock.setWidget(widget)
        return dock
    
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
            self.hui_radio = QtWidgets.QRadioButton("Hui")
            self.method_radio_group.addButton(self.bpa_radio)
            self.method_radio_group.addButton(self.mesh_radio)
            self.method_radio_group.addButton(self.hui_radio)
            self.bpa_radio.setChecked(True)

            # Подключение обработчика событий радиокнопок
            self.method_radio_group.buttonClicked.connect(self.on_method_radio_button_clicked)

            layout.addWidget(self.bpa_radio)
            layout.addWidget(self.mesh_radio)
            layout.addWidget(self.hui_radio)

            self.bpa_widget = self.create_specific_modeling_widget("BPA")
            self.mesh_widget = self.create_specific_modeling_widget("Mesh")
            self.hui_widget = self.create_specific_modeling_widget("Hui")

            # Добавляем виджеты в компоновку, но скрываем их
            layout.addWidget(self.bpa_widget)
            layout.addWidget(self.mesh_widget)
            layout.addWidget(self.hui_widget)
            self.show_default_modeling_widget()  # Показываем виджет по умолчанию

            widget.setLayout(layout)
            self.modeling_dock.setWidget(widget)
        return self.modeling_dock

    def create_specific_modeling_widget(self, method):
        widget = QWidget()
        layout = QVBoxLayout()
        label = QLabel(f"Метод моделирования: {method}")
        slider1 = QSlider(Qt.Orientation.Horizontal)
        slider1.setRange(0, 100)
        slider1.setValue(50)
        slider2 = QSlider(Qt.Orientation.Horizontal)
        slider2.setRange(0, 100)
        slider2.setValue(50)
        slider3 = QSlider(Qt.Orientation.Horizontal)
        slider3.setRange(0, 100)
        slider3.setValue(50)
        button = QPushButton("Моделировать")

        layout.addWidget(label)
        layout.addWidget(slider1)
        layout.addWidget(slider2)
        layout.addWidget(slider3)
        layout.addWidget(button)
        widget.setLayout(layout)
        widget.hide()  # Скрываем виджет

        return widget

    def on_method_radio_button_clicked(self, button):
        if button == self.bpa_radio:
            self.show_default_modeling_widget()
        elif button == self.mesh_radio:
            self.bpa_widget.hide()
            self.mesh_widget.show()
            self.hui_widget.hide()
        elif button == self.hui_radio:
            self.bpa_widget.hide()
            self.mesh_widget.hide()
            self.hui_widget.show()

    def show_default_modeling_widget(self):
        self.bpa_widget.show()
        self.mesh_widget.hide()
        self.hui_widget.hide()