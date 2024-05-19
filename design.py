from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import (QApplication, QMainWindow, QDockWidget, QTextEdit,
                             QVBoxLayout, QWidget, QPushButton, QLabel, QToolBar, QMenu, QStatusBar, QListWidget, QPlainTextEdit )
from point_cloud_widget import OpenGLWidget
from PyQt6.QtCore import Qt
from datetime import datetime, timedelta

class ConsoleWidget(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)

    def write(self, message):
        # Проверяем, является ли сообщение строкой
        if (isinstance(message, str) and message != '\n'):
            # Получаем текущее время с учетом часового пояса UTC+3
            time_now = datetime.utcnow() + timedelta(hours=3)
            # Форматируем время в строку
            time_str = time_now.strftime("%Y-%m-%d %H:%M:%S")
            # Добавляем дату к сообщению
            message_with_time = f"[{time_str}] {message}"
            # Отображаем сообщение в виджете консоли
            self.appendPlainText(message_with_time.strip())
        elif message != '\n':
            # Если сообщение не является строкой, просто выводим его как есть
            self.appendPlainText(str(message))

    def flush(self):
        pass
        
class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.setWindowTitle("LIDAR segmentation and modeling")
        MainWindow.resize(1600, 900)
        MainWindow.setStyleSheet(
            """
            background-color: #3F3F46;
            color: #CCCEDB;
                                  """)
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
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.createFilesDockWidget())
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.createDockWidget('Свойства'))
        self.consoleDock = self.createConsoleDockWidget()
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.consoleDock)
        
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
    
    def createConsoleDockWidget(self):
        dock = QDockWidget('Консоль')
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.consoleWidget = ConsoleWidget()
        dock.setWidget(self.consoleWidget)
        return dock

    def getConsoleWidget(self):
        return self.consoleWidget
    
    
