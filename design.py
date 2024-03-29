from PyQt6 import QtCore, QtGui, QtWidgets
from point_cloud_widget import OpenGLWidget

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1920, 1080)
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.lineEdit = QtWidgets.QLineEdit(parent=self.centralwidget)
        self.lineEdit.setGeometry(QtCore.QRect(160, 40, 471, 20))
        self.lineEdit.setObjectName("lineEdit")
        self.pushButton = QtWidgets.QPushButton(parent=self.centralwidget)
        self.pushButton.setGeometry(QtCore.QRect(60, 40, 91, 21))
        self.pushButton.setObjectName("pushButton")
        self.pushButton_2 = QtWidgets.QPushButton(parent=self.centralwidget)
        self.pushButton_2.setGeometry(QtCore.QRect(60, 90, 211, 81))
        self.pushButton_2.setObjectName("pushButton_2")
        self.label = QtWidgets.QLabel(parent=self.centralwidget)
        self.label.setGeometry(QtCore.QRect(40, 180, 181, 51))
        self.label.setObjectName("label")
        self.openGLWidget = OpenGLWidget(parent=self.centralwidget)
        self.openGLWidget.setGeometry(QtCore.QRect(290, 90, 1400, 800))
        self.openGLWidget.setObjectName("openGLWidget")
        self.listWidget = QtWidgets.QListWidget(parent=self.centralwidget)
        self.listWidget.setGeometry(QtCore.QRect(30, 220, 231, 301))
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

