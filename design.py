from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import (QApplication, QMainWindow, QDockWidget, QTextEdit,
                             QVBoxLayout, QWidget, QPushButton, QLabel, QToolBar, QMenu, QStatusBar, QListWidget, QPlainTextEdit )
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
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_widget('Свойства'))
        
    def dock_widget(self, title):
        dock = QDockWidget(title)
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        widget = QWidget()
        layout = QVBoxLayout()
        label = QLabel(f"Content of {title}")
        button = QPushButton("Click me")
        layout.addWidget(label)
        layout.addWidget(button)
        widget.setLayout(layout)
        dock.setWidget(widget)
        return dock
    
    def files_dock_widget(self):
        dock = QDockWidget('Файлы')
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        widget = QWidget()
        layout = QVBoxLayout()

        # Добавляем QListWidget и QPushButton в стыковочный виджет
        self.listWidget = QListWidget()
        self.select_all_button = QPushButton("Выбрать всё")
        
        layout.addWidget(self.listWidget)
        layout.addWidget(self.select_all_button)

        widget.setLayout(layout)
        dock.setWidget(widget)
        return dock
    
    def ground_extraction_dock_widget(self):
        dock = QDockWidget('Удаление земли')
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        widget = QWidget()
        layout = QVBoxLayout()
        label = QLabel(f"Наполнение удаления земли")
        button = QPushButton("ОК")
        layout.addWidget(label)
        layout.addWidget(button)
        widget.setLayout(layout)
        dock.setWidget(widget)
        return dock
    
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
    
    