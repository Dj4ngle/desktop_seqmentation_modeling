from PyQt6 import QtCore, QtGui, QtWidgets
from point_cloud_widget import OpenGLWidget

class Ui_StartWindow(object):
    def setupUi(self, StartWindow):
        StartWindow.setWindowTitle("Окно входа")
        StartWindow.resize(1024, 768)
        StartWindow.setStyleSheet(
            """
            background:#000000;
            background-color: #3F3F46;
            color: #CCCEDB;
                                  """)
        self.startButton = QtWidgets.QPushButton("Начать", self)  
        
class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1920, 1080)
        MainWindow.setStyleSheet(
            """
            background-color: #3F3F46;
            color: #CCCEDB;
                                  """)
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.lineEdit = QtWidgets.QLineEdit(parent=self.centralwidget)
        self.lineEdit.setGeometry(QtCore.QRect(170, 40, 471, 20))
        self.lineEdit.setObjectName("lineEdit")
        self.pushButton = QtWidgets.QPushButton(parent=self.centralwidget)
        self.pushButton.setGeometry(QtCore.QRect(60, 40, 101, 21))
        self.pushButton.setObjectName("pushButton")
        self.pushButton_2 = QtWidgets.QPushButton(parent=self.centralwidget)
        self.pushButton_2.setGeometry(QtCore.QRect(60, 90, 211, 81))
        self.pushButton_2.setObjectName("pushButton_2")
        self.frontViewButton = QtWidgets.QPushButton(parent=self.centralwidget)
        self.frontViewButton.setGeometry(QtCore.QRect(60, 180, 130, 31))
        self.frontViewButton.setObjectName("frontViewButton")
        self.label = QtWidgets.QLabel(parent=self.centralwidget)
        self.label.setGeometry(QtCore.QRect(40, 210, 181, 51))
        self.label.setObjectName("label")
        self.openGLWidget = OpenGLWidget(parent=self.centralwidget)
        self.openGLWidget.setGeometry(QtCore.QRect(290, 90, 1400, 800))
        self.openGLWidget.setObjectName("openGLWidget")
        self.listWidget = QtWidgets.QListWidget(parent=self.centralwidget)
        self.listWidget.setGeometry(QtCore.QRect(30, 260, 231, 301))
        self.listWidget.setObjectName("listWidget")
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "LIDAR Modeler"))
        self.pushButton.setText(_translate("MainWindow", "Выбрать файлы"))
        self.pushButton_2.setText(_translate("MainWindow", "Начать моделирование"))
        self.label.setText(_translate("MainWindow", "TextLabel"))
        self.frontViewButton.setText(_translate("MainWindow", "Сбросить параметры"))

