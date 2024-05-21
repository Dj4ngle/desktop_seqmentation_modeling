import json
import os
import sys
from datetime import datetime, timedelta

import numpy as np
import pylas
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
    QDockWidget,
    QPlainTextEdit,
    )

class MenuBar:
    def __init__(self, parent=None):
        self.parent = parent
        
    def create_menu_bar(self):
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
        
    def create_actions(self):
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
        editToolBar = QToolBar("Панель управления взаимодействия", self.parent)
        editToolBar.addAction(self.earthExtractionAction)
        editToolBar.addAction(self.segmentationAction)
        editToolBar.addAction(self.taxationAction)
        editToolBar.addAction(self.modelingAction)
        self.parent.addToolBar(editToolBar)
        # Using a QToolBar object and a toolbar area
        interactionToolBar = QToolBar("Панел управления вращения", self.parent)
        interactionToolBar.addAction(self.frontViewAction)
        interactionToolBar.addAction(self.backViewAction)
        interactionToolBar.addAction(self.leftSideViewAction)
        interactionToolBar.addAction(self.rightSideViewAction)
        interactionToolBar.addAction(self.topViewAction)
        interactionToolBar.addAction(self.bottomViewAction)
        self.parent.addToolBar(Qt.ToolBarArea.LeftToolBarArea, interactionToolBar)
        
    def create_actions(self):
        self.earthExtractionAction = QAction(QIcon("images/ground_extraction.png"), "Удаление земли", self.parent)
        self.segmentationAction = QAction(QIcon("images/segmentation.png"), "Сегментация", self.parent)
        self.taxationAction = QAction(QIcon("images/taxation.png"), "Таксация", self.parent)
        self.modelingAction = QAction(QIcon("images/check1True.png"), "Моделирование", self.parent)
        self.frontViewAction = QAction(QIcon("images/FrontView.png"), "Вид спереди", self.parent)
        self.backViewAction = QAction(QIcon("images/BackView.png"), "Вид сзади", self.parent)
        self.leftSideViewAction = QAction(QIcon("images/SideViewLeft.png"), "Вид сбоку", self.parent)
        self.rightSideViewAction = QAction(QIcon("images/SideViewRight.png"), "Вид сбоку", self.parent)
        self.topViewAction = QAction(QIcon("images/TopView.png"), "Вид сверху", self.parent)
        self.bottomViewAction = QAction(QIcon("images/BottomView.png"), "Вид снизу", self.parent)
        
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
        
class ConsoleManager:
    def __init__(self, parent=None):
        self.parent = parent
        self.consoleWidget = None

    def create_console_dock_widget(self):
        dock = QDockWidget('Консоль', self.parent)
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.consoleWidget = ConsoleWidget()
        dock.setWidget(self.consoleWidget)
        return dock

    def redirect_console_output(self):
        if self.consoleWidget:
            sys.stdout = ConsoleOutput(self.consoleWidget)
            sys.stderr = ConsoleOutput(self.consoleWidget)
        
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
        
        self.setWindowIcon(QIcon("images/Icon.png"))
        
        self.setupUi(self)
        
        self.consoleManager = ConsoleManager(self)
        self.console_dock_widget = self.consoleManager.create_console_dock_widget()
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.console_dock_widget)
        self.consoleManager.redirect_console_output()
        
        # Инициализация атрибута для DockWidget "Удаление земли"
        self.groundExtractionDock = None
        
        # Создание меню
        self.menuCreator = MenuBar(self)
        self.menuCreator.create_actions()
        self.menuCreator.create_menu_bar()
        # Создание панелеи инструментов
        self.toolbarsCreator = ToolBar(self)
        self.toolbarsCreator.create_actions()
        self.toolbarsCreator._createToolBars()
        
        
        self.menuCreator.openAction.triggered.connect(self.select_files)
        self.menuCreator.saveAction.triggered.connect(self.save_selected_tree)
        self.menuCreator.exitAction.triggered.connect(QApplication.instance().quit)
        self.toolbarsCreator.earthExtractionAction.triggered.connect(lambda:
                                                                     self.toggle_dock_widget('sampleDock',
                                                                        self.ground_extraction_dock_widget,
                                                                        Qt.DockWidgetArea.RightDockWidgetArea))
        self.toolbarsCreator.segmentationAction.triggered.connect(lambda:
                                                                     self.toggle_dock_widget('sampleDock',
                                                                        self.segmentation_dock_widget,
                                                                        Qt.DockWidgetArea.RightDockWidgetArea))
        self.toolbarsCreator.taxationAction.triggered.connect(lambda:
                                                                     self.toggle_dock_widget('sampleDock',
                                                                        self.taxation_dock_widget,
                                                                        Qt.DockWidgetArea.RightDockWidgetArea))
        self.toolbarsCreator.modelingAction.triggered.connect(lambda:
                                                                     self.toggle_dock_widget('sampleDock',
                                                                        self.modeling_dock_widget,
                                                                        Qt.DockWidgetArea.RightDockWidgetArea))
        
        self.toolbarsCreator.frontViewAction.triggered.connect(lambda: self.openGLWidget.set_view_parameters(-90, 0, 0))
        self.toolbarsCreator.backViewAction.triggered.connect(lambda: self.openGLWidget.set_view_parameters(-90, 0, 180))
        self.toolbarsCreator.leftSideViewAction.triggered.connect(lambda: self.openGLWidget.set_view_parameters(-90, 0, 90))
        self.toolbarsCreator.rightSideViewAction.triggered.connect(lambda: self.openGLWidget.set_view_parameters(-90, 0, 270))
        self.toolbarsCreator.topViewAction.triggered.connect(lambda: self.openGLWidget.set_view_parameters(0, 0, 0))
        self.toolbarsCreator.bottomViewAction.triggered.connect(lambda: self.openGLWidget.set_view_parameters(180, 0, 0))
        
        self.selected_files = []
        self.dockWidgets = {}

    def start_modeling(self):
        # tmp = "temp.obj"
        # modeler(self.selected_files[0], tmp)
        # self.openGLWidget.load_model(tmp)
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

    def checkbox_changed(self, state):
        checkbox = self.sender()
        if checkbox:
            # Извлекаем полный путь к файлу
            file_path = checkbox.property("filePath")
            if state == 2:
                self.openGLWidget.load_point_cloud(file_path)
            elif state == 0:
                if file_path in self.openGLWidget.point_clouds:
                    del self.openGLWidget.point_clouds[file_path]
                    self.openGLWidget.update()
                    

    def toggle_dock_widget(self, widget_id, create_widget_func, dock_area):
        if widget_id in self.dockWidgets:
            dock_widget = self.dockWidgets.pop(widget_id)
            self.removeDockWidget(dock_widget)
            dock_widget.deleteLater()
        else:
            dock_widget = create_widget_func()
            self.addDockWidget(dock_area, dock_widget)
            self.dockWidgets[widget_id] = dock_widget

    def save_selected_tree(self):
        selected_files = []
        for index in range(self.listWidget.count()):
            item = self.listWidget.item(index)
            checkbox = self.listWidget.itemWidget(item)
            if checkbox.isChecked():
                selected_files.append(checkbox.property("filePath"))

        if not selected_files:
            print("Нет выбранных файлов для сохранения")
            return

        if len(selected_files) == 1:
            self.save_single_file(selected_files[0])
        else:
            self.save_multiple_files(selected_files)

    def save_single_file(self, file_path):
        save_path, _ = QFileDialog.getSaveFileName(self, "Сохранить выбранный файл", "", "LAS Files (*.las)")
        if save_path:
            las = pylas.read(file_path)
            las.write(save_path)
            print(f"Файл: {file_path} сохранён как: {save_path}")

    def save_multiple_files(self, file_paths):
        save_dir = QFileDialog.getExistingDirectory(self, "Выбрать папку для сохранения файлов")
        if save_dir:
            for file_path in file_paths:
                las = pylas.read(file_path)
                file_name = os.path.basename(file_path)
                output_path = os.path.join(save_dir, file_name)
                las.write(output_path)
                print(f"Файл: {file_path} сохранён как: {output_path}")

if __name__ == "__main__":
    app = QApplication([])
    
    # Применяем стили
    app.setStyleSheet(open("style.qss").read())
    
    main_window = MyMainWindow()
    main_window.show()
    app.exec()
