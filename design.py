from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import (QApplication, QMainWindow, QDockWidget, QTextEdit,
                             QVBoxLayout, QWidget, QPushButton, QLabel, QToolBar, QMenu, QStatusBar, QListWidget )
from point_cloud_widget import OpenGLWidget
from PyQt6.QtCore import Qt
        
class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1600, 900)
        MainWindow.setStyleSheet(
            """
            background-color: #3F3F46;
            color: #CCCEDB;
                                  """)
        # Центральный виджет
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        # Создаем вертикальную компоновку для centralwidget
        self.centralLayout = QVBoxLayout(self.centralwidget)
        self.centralLayout.setContentsMargins(0, 0, 0, 0)  # Убираем отступы
        
        self.openGLWidget = OpenGLWidget(parent=self.centralwidget)
        self.openGLWidget.setObjectName("openGLWidget")
        self.centralLayout.addWidget(self.openGLWidget)
        
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        
        # Стыковочные виджеты
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.createFilesDockWidget())
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.createDockWidget('Свойства'))
        consoleDock = self.createDockWidget('Консоль')
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, consoleDock)
        

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "LIDAR segmentation and modeling"))
        
        
    def createDockWidget(self, title):
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
    
    def createFilesDockWidget(self):
        dock = QDockWidget('Файлы')
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        widget = QWidget()
        layout = QVBoxLayout()

        # Добавляем QListWidget и QPushButton в стыковочный виджет
        self.listWidget = QListWidget()
        self.frontViewButton = QPushButton("Сбросить параметры")
        
        layout.addWidget(self.listWidget)
        layout.addWidget(self.frontViewButton)

        widget.setLayout(layout)
        dock.setWidget(widget)
        return dock
