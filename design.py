from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import (QApplication, QMainWindow, QDockWidget, QTextEdit,
                             QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel, QToolBar, QMenu, QStatusBar, QListWidget, QPlainTextEdit )
from point_cloud_widget import OpenGLWidget
from PyQt6.QtCore import Qt
from datetime import datetime, timedelta
        
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
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.properties_dock_widget())
        
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
    
    # def ground_extraction_dock_widget(self):
    #     dock = QDockWidget('Удаление земли')
    #     dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
    #     widget = QWidget()
    #     layout = QVBoxLayout()
    #     self.file_list_widget = QListWidget()  # Список для выбора файлов
    #     layout.addWidget(self.file_list_widget)

    #     # Кнопка "ОК" для запуска удаления земли
    #     self.ground_extraction = QPushButton("ОК")
    #     layout.addWidget(self.ground_extraction)
    #     self.ground_extraction.clicked.connect(self.openGLWidget.remove_ground)
        
    #     widget.setLayout(layout)
    #     dock.setWidget(widget)
    #     return dock
    
    def ground_extraction_dock_widget(self):
        dock = QDockWidget('Удаление земли')
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        widget = QWidget()
        layout = QVBoxLayout()

        self.clouds_list_widget = QListWidget()
        layout.addWidget(self.clouds_list_widget)

        update_button = QPushButton("Обновить список")
        update_button.clicked.connect(self.update_clouds_list)
        layout.addWidget(update_button)

        run_button = QPushButton("Удалить землю")
        run_button.clicked.connect(self.run_ground_extraction)
        layout.addWidget(run_button)

        widget.setLayout(layout)
        dock.setWidget(widget)
        return dock

    def update_clouds_list(self):
        self.clouds_list_widget.clear()
        for file_name in self.openGLWidget.point_clouds:
            self.clouds_list_widget.addItem(file_name)

    def run_ground_extraction(self):
        selected_items = self.clouds_list_widget.selectedItems()
        if selected_items:
            file_path = selected_items[0].text()
            self.perform_ground_extraction(file_path)
 
    
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
        dock = QDockWidget('Моделирование')
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        widget = QWidget()
        layout = QVBoxLayout()
        label = QLabel(f"Наполнение моделирования")
        button = QPushButton("ОК")
        layout.addWidget(label)
        layout.addWidget(button)
        widget.setLayout(layout)
        dock.setWidget(widget)
        return dock
    
    