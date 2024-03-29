from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QListWidgetItem, QCheckBox
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
        # tmp = "temp.obj"
        # modeler(self.selected_files[0], tmp)
        # self.openGLWidget.loadModel(tmp)
        # пока тут ничего
        pass

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Выбрать файлы", "", "LAS files (*.las)")

        if files:
            print(files)
            self.lineEdit.setText("; ".join(files))
            self.selected_files = self.lineEdit.text().split("; ")

            self.listWidget.clear()  # Очистить список перед добавлением новых элементов

            for file in self.selected_files:
                # Создание нового QListWidgetItem
                item = QListWidgetItem(self.listWidget)

                # Создание чекбокса с именем файла
                checkbox = QCheckBox(file)
                checkbox.setChecked(False)

                checkbox.setProperty("filePath", file)

                # Добавляем чекбокс в QListWidgetItem
                self.listWidget.setItemWidget(item, checkbox)
                # Устанавливаем размер элемента списка для чекбокса
                item.setSizeHint(checkbox.sizeHint())

                checkbox.stateChanged.connect(self.checkbox_changed)

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
    window = MyMainWindow()
    window.show()
    app.exec()
