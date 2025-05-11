import os

from PyQt6 import QtCore, QtWidgets
from PyQt6.QtWidgets import (QHBoxLayout, QListWidget, QDockWidget,QListWidgetItem, QCheckBox, QVBoxLayout, QWidget, QPushButton)

from Toolbar_Widgets import ground_extraction, taxation, segmentation, modeling, coordinates
from point_cloud_widget import OpenGLWidget
from PyQt6.QtCore import Qt

# Пример!!!
# from Toolbar_Widgets import example_widget

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
            'ground_extraction': ground_extraction.ground_extraction_dock_widget(self),
            'segmentation': segmentation.segmentation_dock_widget(self),
            'taxation': taxation.taxation_dock_widget(self),
            'modeling': modeling.modeling_dock_widget(self),
            'coordinates': coordinates.coordinates_dock_widget(self),

            # Пример!!!
            # 'example': example_widget.example_dock_widget(self)  # ← наш виджет
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

    def add_file_to_list_widget(self, file_path):
        # Добавляем облако точек земли в list_widget
        ground_item = QListWidgetItem(self.listWidget)
        ground_checkbox = QCheckBox(os.path.basename(file_path))
        ground_checkbox.setChecked(True)
        ground_checkbox.setProperty("filePath", file_path)
        self.listWidget.setItemWidget(ground_item, ground_checkbox)
        ground_item.setSizeHint(ground_checkbox.sizeHint())
        ground_checkbox.stateChanged.connect(self.checkbox_changed)