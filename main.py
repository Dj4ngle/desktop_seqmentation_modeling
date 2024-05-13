from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QCheckBox, QFileDialog, QListWidgetItem, QVBoxLayout, QHBoxLayout
from PyQt6.QtGui import QAction
from design import Ui_MainWindow, Ui_StartWindow
from modeler import modeler
from point_cloud_widget import OpenGLWidget

class StartWindow(QMainWindow, Ui_StartWindow):
    def __init__(self):
        super(StartWindow, self).__init__()
        
        toolbar = self.addToolBar("Toolbar")
        toolbar.addAction("Action 1")
        toolbar.addAction("Action 2")
        toolbar.addAction("Action 3")
        toolbar.addAction("Action 4")
        
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
        
        toolbar = self.addToolBar("Toolbar")
        toolbar.addAction("Action 1")
        toolbar.addAction("Action 2")
        toolbar.addAction("Action 3")
        toolbar.addAction("Action 4")
        
        self.setupUi(self)
        self.pushButton.clicked.connect(self.select_files)
        self.pushButton_2.clicked.connect(self.start_modeling)
        self.frontViewButton.clicked.connect(self.set_front_view)
        self.selected_files = []

    def set_front_view(self):
        self.openGLWidget.resetParameters()

    def start_modeling(self):
        # tmp = "temp.obj"
        # modeler(self.selected_files[0], tmp)
        # self.openGLWidget.loadModel(tmp)
        # пока тут ничего
        pass

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Выбрать файлы", "", "LAS files (*.las)")

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
