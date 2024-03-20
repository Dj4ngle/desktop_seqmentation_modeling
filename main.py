from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog
from design import Ui_MainWindow
from modeler import modeler


class MyMainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(MyMainWindow, self).__init__()
        self.setupUi(self)
        self.pushButton.clicked.connect(self.select_files)
        self.pushButton_2.clicked.connect(self.start_modeling)
        self.selected_files = []

    def start_modeling(self):
        tmp = "temp.obj"
        modeler(self.selected_files[0], tmp)
        self.openGLWidget.loadModel(tmp)

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Выбрать файлы", "", "LAS files (*.las)")

        if files:
            print(files)
            self.lineEdit.setText("; ".join(files))
            self.selected_files = self.lineEdit.text().split("; ")
            if self.selected_files:
                self.openGLWidget.loadPointCloud(self.selected_files[0])


if __name__ == "__main__":
    app = QApplication([])
    window = MyMainWindow()
    window.show()
    app.exec()
