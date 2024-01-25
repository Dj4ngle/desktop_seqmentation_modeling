from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog
from design import Ui_MainWindow

class MyMainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(MyMainWindow, self).__init__()
        self.setupUi(self)
        self.pushButton.clicked.connect(self.select_files)
        self.pushButton_2.clicked.connect(self.start_modeling)

    def start_modeling(self):
        selected_files = self.lineEdit.text().split("; ")
        if selected_files:
            self.openGLWidget.loadPointCloud(selected_files[0])

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Выбрать файлы")

        if files:
            print(files)
            self.lineEdit.setText("; ".join(files))

if __name__ == "__main__":
    app = QApplication([])
    window = MyMainWindow()
    window.show()
    app.exec()
