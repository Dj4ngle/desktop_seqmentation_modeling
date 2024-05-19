import sys
from PyQt6.QtCore import Qt
from PyQt6 import QtCore
from PyQt6.QtGui import QAction, QIcon
from design import Ui_MainWindow
from modeler import modeler
from point_cloud_widget import OpenGLWidget
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QCheckBox,
    QFileDialog,
    QListWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
    QToolBar,
    QMenuBar,
    QMenu,
    QStatusBar,
    QToolTip,
    )

class MenuBar:
    def __init__(self, parent=None):
        self.parent = parent
        
    def _createMenuBar(self):
        menuBar = QMenuBar(self.parent)
        self.parent.setMenuBar(menuBar)
        # Creating File menu using a QMenu object
        fileMenu = QMenu("Файл", self.parent)
        menuBar.addMenu(fileMenu)
        # fileMenu.addAction(self.newAction)
        fileMenu.addAction(self.openAction)
        fileMenu.addAction(self.saveAction)
        fileMenu.addAction(self.exitAction)
        # Edit menu
        editMenu = menuBar.addMenu("Правка")
        # Color submenu in the Edit menu
        findMenu = editMenu.addMenu("Цвет")
        findMenu.addAction(self.selectFromListAction)
        findMenu.addAction(self.createNewColorAction)
        # Help menu
        helpMenu = menuBar.addMenu("Помощь")
        helpMenu.addAction(self.helpContentAction)
        helpMenu.addAction(self.aboutAction)
        
    def _createActions(self):
        # Creating action using the first constructor
        # self.newAction = QAction(self)
        # self.newAction.setText("&New")
        # Creating actions using the second constructor
        # Действия в меню "Файл"
        self.openAction = QAction("Открыть", self.parent)
        self.saveAction = QAction("Сохранить", self.parent)
        self.exitAction = QAction("Выйти", self.parent)
        # Действия в меню "Правка"
        self.colorAction = QAction("Цвет", self.parent)
        # Действия в подменю "Цвет"
        self.selectFromListAction = QAction("Выбрать из списка", self.parent)
        self.createNewColorAction = QAction("Создать новый цвет", self.parent)
        # Действия в меню "Помощь"
        self.helpContentAction = QAction("Справочный материал", self.parent)
        self.aboutAction = QAction("О приложении", self.parent)

class ToolBar:
    def __init__(self, parent=None):
        self.parent = parent

    def _createToolBars(self):
        # Using a title
        # fileToolBar = self.addToolBar("File")
        # Using a QToolBar object
        editToolBar = QToolBar("Панель управления взаимодействия", self.parent)
        editToolBar.addAction(self.earthExtractionAction)
        self.parent.addToolBar(editToolBar)
        # Using a QToolBar object and a toolbar area
        interactionToolBar = QToolBar("Панел управления вращения", self.parent)
        interactionToolBar.addAction(self.frontViewAction)
        self.parent.addToolBar(Qt.ToolBarArea.LeftToolBarArea, interactionToolBar)
        
    def _createActions(self):
        self.earthExtractionAction = QAction(QIcon("images/FrontView.png"), "Earth extraction", self.parent)
        self.earthExtractionAction.setToolTip("Это подсказка с использованием стилей CSS")
        self.frontViewAction = QAction(QIcon("images/view.png"), "Front view", self.parent)
        # self.saveAction = QAction(QIcon("images/view.png"))
        # self.exitAction = QAction("Выйти", self.parent)
        # # Действия в меню "Правка"
        # self.colorAction = QAction("Цвет", self.parent)
        # # Действия в подменю "Цвет"
        # self.selectFromListAction = QAction("Выбрать из списка", self.parent)
        # self.createNewColorAction = QAction("Создать новый цвет", self.parent)
        # # Действия в меню "Помощь"
        # self.helpContentAction = QAction("Справочный материал", self.parent)
        # self.aboutAction = QAction("О приложении", self.parent)

        
class ConsoleOutput:
    def __init__(self, console_widget):
        self.console_widget = console_widget
        self.stdout = sys.stdout
        self.stderr = sys.stderr

    def write(self, message):
        # Передаем сообщение в стандартный вывод
        self.stdout.write(message)
        self.stdout.flush()  # Обязательно вызываем flush, чтобы сообщение сразу же отобразилось в консоли

        # Отображаем сообщение в виджете консоли
        self.console_widget.write(message)

    def flush(self):
        self.stdout.flush()
        self.console_widget.flush()

class MyMainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(MyMainWindow, self).__init__()
        
        self.setupUi(self)
        self.consoleWidget = self.getConsoleWidget()  # Получаем consoleWidget
        self.redirect_console_output()
        # Создание меню
        self.menuCreator = MenuBar(self)
        self.menuCreator._createActions()
        self.menuCreator._createMenuBar()
        # Создание панелеи инструментов
        self.toolbarsCreator = ToolBar(self)
        self.toolbarsCreator._createActions()
        self.toolbarsCreator._createToolBars()
        
        
        self.frontViewButton.clicked.connect(self.set_front_view)
        self.menuCreator.openAction.triggered.connect(self.select_files)
        self.menuCreator.exitAction.triggered.connect(QApplication.instance().quit)
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
        files, _ = QFileDialog.getOpenFileNames(self, "Выбрать файлы", "", "LAS and PCD files (*.las *.pcd)")

        if files:
            for file in files:
                # Создание нового QListWidgetItem
                item = QListWidgetItem(self.listWidget)

                # Создание чекбокса с именем файла
                checkbox = QCheckBox(file)
                checkbox.setChecked(False)

                checkbox.setProperty("filePath", file)
                print(f"Загружен файл: {file}")

                # Добавляем чекбокс в QListWidgetItem
                self.listWidget.setItemWidget(item, checkbox)
                # Устанавливаем размер элемента списка для чекбокса
                item.setSizeHint(checkbox.sizeHint())

                checkbox.stateChanged.connect(self.checkbox_changed)

            # Добавление новых файлов в список файлов
            # self.lineEdit.setText("; ".join(files))
            # self.selected_files.extend(self.lineEdit.text().split("; "))

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
                    
    def redirect_console_output(self):
        sys.stdout = ConsoleOutput(self.consoleWidget)
        sys.stderr = ConsoleOutput(self.consoleWidget)

if __name__ == "__main__":
    app = QApplication([])
    
    # Применяем стили
    app.setStyleSheet(open("style.qss").read())
    
    main_window = MyMainWindow()
    main_window.show()
    app.exec()
