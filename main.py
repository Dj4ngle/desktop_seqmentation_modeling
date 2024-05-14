from PyQt6.QtCore import Qt
from PyQt6 import QtCore
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QCheckBox, QFileDialog, QListWidgetItem, QVBoxLayout, QHBoxLayout, QToolBar
from PyQt6.QtGui import QAction
from design import Ui_MainWindow, Ui_StartWindow
from modeler import modeler
from point_cloud_widget import OpenGLWidget

class Toolbar(QToolBar):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.addAction("Action 1")
        self.addAction("Action 2")
        self.addAction("Action 3")
        self.addAction("Action 4")

class StartWindow(QMainWindow, Ui_StartWindow):
    def __init__(self):
        super(StartWindow, self).__init__()
        self.setupUi(self)
        self.startButton.clicked.connect(self.openMainWindow)
        # Создаем тулбар
        self.toolbar = Toolbar(self)
        self.addToolBar(self.toolbar)  # Добавляем тулбар в главное окно
        
        # Создаем центральный виджет
        central_widget = QWidget(self)
        
        self.setupUi(self)
        self.startButton.clicked.connect(self.openMainWindow)
        
       # Создаем вертикальную компоновку
        layout = QVBoxLayout(central_widget)

        # Добавляем метку в компоновку и выравниваем по центру
        layout.addWidget(self.startButton, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        # Устанавливаем центральный виджет в главное окно
        self.setCentralWidget(central_widget)

    def openMainWindow(self):
        self.main_window = MyMainWindow()
        self.main_window.show()
        self.close()

class MyMainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(MyMainWindow, self).__init__()
        
        # Создаем тулбар
        self.toolbar = Toolbar(self)
        self.addToolBar(self.toolbar)  # Добавляем тулбар в главное окно
        
        self.setupUi(self)
        self.pushButton.clicked.connect(self.select_files)
        self.pushButton_2.clicked.connect(self.start_modeling)
        self.frontViewButton.clicked.connect(self.set_front_view)
        self.selected_files = []
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Обновляем размеры элементов интерфейса
        self.resizeUI()
    
    def resizeUI(self):
        # Расчет новых размеров элементов интерфейса
        new_width = self.width()
        new_height = self.height()
        print (self.width(), self.height())
        
        button_width = new_width * 0.06
        self.openGLWidget.setGeometry(QtCore.QRect(290, 90, new_width - 320, new_height - 200))
        self.listWidget.setGeometry(QtCore.QRect(30, 260, 231, new_height - new_height*0.3 - 210))
        self.lineEdit.setGeometry(QtCore.QRect(170, 40, new_width - 210, 20))

    def set_front_view(self):
        self.openGLWidget.resetParameters()

    def start_modeling(self):
        # tmp = "temp.obj"
        # modeler(self.selected_files[0], tmp)
        # self.openGLWidget.loadModel(tmp)
        # пока тут ничего
        pass

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Выбрать файлы", "", "LAS and PCD files (*.las *.pcd)")

        if files:
            for file in files:
                # Создание нового QListWidgetItem
                item = QListWidgetItem(self.listWidget)

                # Создание чекбокса с именем файла
                checkbox = QCheckBox(file)
                checkbox.setChecked(False)

                checkbox.setProperty("filePath", file)
                print("filePath ", file)

                # Добавляем чекбокс в QListWidgetItem
                self.listWidget.setItemWidget(item, checkbox)
                # Устанавливаем размер элемента списка для чекбокса
                item.setSizeHint(checkbox.sizeHint())

                checkbox.stateChanged.connect(self.checkbox_changed)

            # Добавление новых файлов в список файлов
            self.lineEdit.setText("; ".join(files))
            self.selected_files.extend(self.lineEdit.text().split("; "))

    def checkbox_changed(self, state):
        checkbox = self.sender()
        if checkbox:
            # Извлекаем полный путь к файлу
            file_path = checkbox.property("filePath")
            if state == 2:
                self.openGLWidget.loadPointCloud(file_path)
            elif state == 0:
                if file_path in self.openGLWidget.point_clouds:
                    del self.openGLWidget.point_clouds[file_path]
                    self.openGLWidget.update()


if __name__ == "__main__":
    app = QApplication([])
    start_window = StartWindow()
    start_window.show()
    app.exec()
