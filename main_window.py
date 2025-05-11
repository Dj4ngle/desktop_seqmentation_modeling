import os
import open3d as o3d
import pandas as pd
from OpenGL.GL import glDeleteBuffers
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QListWidgetItem, QCheckBox, QApplication, QLabel
from Toolbar_Widgets import modeling
from config import base_path
from Toolbar_Widgets.design import Ui_MainWindow
from Toolbar_Widgets.console_manager import ConsoleManager
from menu_bar import MenuBar
from Toolbar.tool_bar import ToolBar
import pylas

# Пример!!!
# from Toolbar_Widgets import example_widget

class MyMainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(MyMainWindow, self).__init__()
        self.dock_widgets = {}
        self.current_dock = None

        self.setWindowIcon(QIcon(os.path.join(base_path,"images/Icon.png")))

        self.setupUi(self)

        # Создаем экземпляр для управления консолью
        self.consoleManager = ConsoleManager(self)
        # Создаем виджет док-панели для консоли
        self.console_dock_widget = self.consoleManager.create_console_dock_widget()
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.console_dock_widget)
        # Перенаправляем стандартный вывод в консоль
        self.consoleManager.redirect_console_output()

        # Создаем меню
        self.menuCreator = MenuBar(self)
        self.menuCreator.create_actions()
        self.menuCreator.create_menu_bar()

        # Создаем панель инструментов
        self.toolbarsCreator = ToolBar(self)
        self.toolbarsCreator.create_actions()
        self.toolbarsCreator._createToolBars()

        # Подключаем обработчики событий для элементов меню и панели инструментов
        self.menuCreator.openAction.triggered.connect(self.select_files)
        self.menuCreator.saveAction.triggered.connect(self.save_selected_tree)
        self.menuCreator.exitAction.triggered.connect(QApplication.instance().quit)
        self.toolbarsCreator.earthExtractionAction.triggered.connect(lambda:
                                                                     self.toggle_dock_widget('ground_extraction',
                                                                        Qt.DockWidgetArea.LeftDockWidgetArea))
        self.toolbarsCreator.earthExtractionAction.triggered.connect(lambda:
                                                                     self.update_list(self.clouds_list_widget))
        self.toolbarsCreator.segmentationAction.triggered.connect(lambda:
                                                                     self.toggle_dock_widget('segmentation',
                                                                        Qt.DockWidgetArea.LeftDockWidgetArea))
        self.toolbarsCreator.segmentationAction.triggered.connect(lambda:
                                                                     self.update_list(self.segmentation_list_widget))
        self.toolbarsCreator.taxationAction.triggered.connect(lambda:
                                                                     self.toggle_dock_widget('taxation',
                                                                        Qt.DockWidgetArea.LeftDockWidgetArea))
        self.toolbarsCreator.taxationAction.triggered.connect(lambda:
                                                                     self.update_list(self.taxation_list_widget))
        self.toolbarsCreator.modelingAction.triggered.connect(lambda:
                                                                     self.toggle_dock_widget('modeling',
                                                                        Qt.DockWidgetArea.LeftDockWidgetArea))
        self.toolbarsCreator.modelingAction.triggered.connect(modeling.show_default_modeling_widget)

        self.toolbarsCreator.coordinatesAction.triggered.connect(lambda:
                                                              self.toggle_dock_widget('coordinates',
                                                                                      Qt.DockWidgetArea.LeftDockWidgetArea))

        # Пример!!!
        # self.toolbarsCreator.exampleAction.triggered.connect(
        #     lambda: self.toggle_dock_widget(
        #         'example',  # ключ из init_dock_widgets
        #         Qt.DockWidgetArea.LeftDockWidgetArea
        #     )
        # )

        self.toolbarsCreator.frontViewAction.triggered.connect(lambda: self.openGLWidget.set_view_parameters(1, 1, 1))
        self.toolbarsCreator.backViewAction.triggered.connect(lambda: self.openGLWidget.set_view_parameters(1, 180, 1))
        self.toolbarsCreator.leftSideViewAction.triggered.connect(lambda: self.openGLWidget.set_view_parameters(1, 90, 1))
        self.toolbarsCreator.rightSideViewAction.triggered.connect(lambda: self.openGLWidget.set_view_parameters(1, 270, 1))
        self.toolbarsCreator.topViewAction.triggered.connect(lambda: self.openGLWidget.set_view_parameters(90, 1, 1))
        self.toolbarsCreator.bottomViewAction.triggered.connect(lambda: self.openGLWidget.set_view_parameters(270, 1, 1))

        # Подключаем кнопку и обработчик
        self.select_all_button.clicked.connect(self.toggle_select_all)
        # Подключаем обработчик события нажатия кнопки "Удалить"
        self.remove_button.clicked.connect(self.remove_selected_items)

        self.selected_files = []
        
        # Инициализация атрибута для DockWidget "Свойства"
        self.properties_dock = None
        self.properties_widget = None

        self.init_dock_widgets()

    def select_files(self):
        # Метод для выбора файлов
        files, _ = QFileDialog.getOpenFileNames(self, "Выбрать файлы", "", "LAS and PCD files (*.las *.obj *.pcd)")
        if files:
            for file in files:
                # Создание нового элемента QListWidgetItem
                item = QListWidgetItem(self.listWidget)

                # Создание чекбокса с именем файла
                checkbox = QCheckBox(os.path.basename(file))
                checkbox.setChecked(False)

                checkbox.setProperty("filePath", file)
                print(f"Загружен файл: {file}")

                # Добавляем чекбокс в элемент QListWidgetItem
                self.listWidget.setItemWidget(item, checkbox)
                # Устанавливаем размер элемента списка для чекбокса
                item.setSizeHint(checkbox.sizeHint())

                checkbox.stateChanged.connect(self.checkbox_changed)
                
    def toggle_select_all(self):
        # Метод для переключения всех чекбоксов
        all_checked = all(self.listWidget.itemWidget(self.listWidget.item(index)).isChecked() 
                          for index in range(self.listWidget.count()))

        # Устанавливаем новое состояние для всех чекбоксов
        new_state = Qt.CheckState.Unchecked if all_checked else Qt.CheckState.Checked
        new_state_bool = new_state == Qt.CheckState.Checked

        # Проходим по всем элементам в списке и устанавливаем новое состояние
        for index in range(self.listWidget.count()):
            item = self.listWidget.item(index)
            checkbox = self.listWidget.itemWidget(item)
            if checkbox:
                checkbox.setChecked(new_state_bool)
                
    def remove_selected_items(self):
        # Метод для удаления выбранных элементов
        items = []
        for index in range(self.listWidget.count()):
            items.append(self.listWidget.item(index))
        
        # Проходим в обратном порядке по всем элементам и удаляем выбранные
        for item in reversed(items):
            checkbox = self.listWidget.itemWidget(item)
            if checkbox and checkbox.isChecked():
                file_path = checkbox.property("filePath")
                
                # Удаляем элемент из QListWidget
                row = self.listWidget.row(item)
                self.listWidget.takeItem(row)

                _, file_extension = os.path.splitext(file_path)
                if file_extension == ".obj":
                    # Удаляем точку из OpenGLWidget, если файл загружен
                    if file_path and file_path in self.openGLWidget.models:
                        del self.openGLWidget.models[file_path]
                    if file_path and file_path in self.openGLWidget.vbo_data_models:
                        # Получаем информацию о VBO, которую нужно удалить
                        vbo_info = self.openGLWidget.vbo_data_models[file_path]

                        # Вызываем функцию удаления VBO
                        self.delete_vbo(vbo_info)

                        # Удаляем запись из словаря
                        del self.openGLWidget.vbo_data_models[file_path]

                    print(f"Удалён файл: {file_path}")

                elif file_extension == ".las" or file_extension == ".pcd":
                    # Удаляем точку из OpenGLWidget, если файл загружен
                    if file_path and file_path in self.openGLWidget.point_clouds:
                        del self.openGLWidget.point_clouds[file_path]
                    if file_path and file_path in self.openGLWidget.vbo_data:
                        # Получаем информацию о VBO, которую нужно удалить
                        vbo_info = self.openGLWidget.vbo_data[file_path]

                        # Вызываем функцию удаления VBO
                        self.delete_vbo(vbo_info)

                        # Удаляем запись из словаря
                        del self.openGLWidget.vbo_data[file_path]

                    print(f"Удалён файл: {file_path}")

        
        # Обновляем отображение в OpenGLWidget
        self.openGLWidget.update()

    def delete_vbo(self, vbo_info):
        # vbo_info предполагается быть кортежем (point_vbo, color_vbo, _)
        point_vbo, color_vbo, _ = vbo_info

        # Освобождение ресурсов VBO для точек
        if point_vbo is not None:
            glDeleteBuffers(1, [point_vbo])

        # Освобождение ресурсов VBO для цветов
        if color_vbo is not None:
            glDeleteBuffers(1, [color_vbo])

    def checkbox_changed(self, state):
        checkbox = self.sender()
        if checkbox:
            file_path = checkbox.property("filePath")
            if state == 2:  # Checkbox is checked
                _, file_extension = os.path.splitext(file_path)
                if file_extension == ".obj":
                    self.openGLWidget.load_model(file_path)
                    self.update_properties_dock(file_path)
                elif file_extension == ".las" or file_extension == ".pcd":
                    self.openGLWidget.load_point_cloud(file_path)
                    self.update_properties_dock(file_path)
                else:
                    # Работа с форматом csv
                    pass

            elif state == 0:  # Checkbox is unchecked
                if file_path in self.openGLWidget.point_clouds:
                    self.openGLWidget.point_clouds[file_path] = {'active': False, 'data': None}
                    self.openGLWidget.update()
                    self.clear_properties_dock()
                elif file_path in self.openGLWidget.models:
                    self.openGLWidget.models[file_path] = {'active': False, 'data': None}
                    self.openGLWidget.update()
                    self.clear_properties_dock()

    def update_properties_dock(self, file_path):
        if file_path in self.openGLWidget.point_clouds:
            if self.openGLWidget.point_clouds[file_path]['active']:
                num_points = self.openGLWidget.vbo_data[file_path][2]

                self.clear_properties_dock()
                file_label = QLabel(f"Файл: {os.path.basename(file_path)}")
                num_points_label = QLabel(f"Количество точек: {num_points}")

                self.properties_layout.addWidget(file_label)
                self.properties_layout.addWidget(num_points_label)
        if file_path in self.openGLWidget.models:
            if self.openGLWidget.models[file_path]['active']:
                triangles = self.openGLWidget.vbo_data_models[file_path][2] / 3

                self.clear_properties_dock()
                file_label = QLabel(f"Файл: {os.path.basename(file_path)}")
                num_points_label = QLabel(f"Количество полигонов: {int(triangles)}")
                self.properties_layout.addWidget(file_label)
                self.properties_layout.addWidget(num_points_label)

    def clear_properties_dock(self):
        if self.properties_layout:
            for i in reversed(range(self.properties_layout.count())):
                widget = self.properties_layout.itemAt(i).widget()
                if widget:
                    widget.setParent(None)

    def toggle_dock_widget(self, dock_widget_name, dock_area):
        dock_widget = self.dock_widgets.get(dock_widget_name)
        # Сначала проверяем, открыт ли данный виджет
        if dock_widget.isVisible():
            # Если виджет уже открыт и видим, просто его скрываем
            dock_widget.hide()
        else:
            # Если виджет закрыт, скрываем все остальные виджеты
            for widget in self.dock_widgets.values():
                widget.hide()
            # И отображаем нужный виджет
            self.addDockWidget(dock_area, dock_widget)
            dock_widget.show()

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
        save_path, _ = QFileDialog.getSaveFileName(self, "Сохранить выбранный файл", "",
                                                   "LAS Files (*.las);;PCD Files (*.pcd);;CSV Files (*.csv)")
        if save_path:
            # Определяем расширение файла
            file_extension = os.path.splitext(save_path)[1]

            if file_extension == ".las":
                las = pylas.read(file_path)
                las.write(save_path)
                print(f"Файл: {file_path} сохранён как: {save_path}")
            elif file_extension == ".pcd":
                points = self.openGLWidget.vbo_data[file_path][0]
                # Создаем объект PointCloud
                pcd = o3d.geometry.PointCloud()
                # Устанавливаем точки в объект PointCloud
                pcd.points = o3d.utility.Vector3dVector(points)
                o3d.io.write_point_cloud(save_path, pcd)
                print(f"Файл: {file_path} сохранён как: {save_path}")

            elif file_extension == ".csv":
                # Сохраняем файл как .csv
                df = pd.read_csv(file_path)
                df.to_csv(save_path, index=False, sep=";")
                print(f"Файл: {file_path} сохранён как: {save_path}")

            else:
                print(f"Неподдерживаемый формат файла: {file_path}")

    def save_multiple_files(self, file_paths):
        save_dir = QFileDialog.getExistingDirectory(self, "Выбрать папку для сохранения файлов")
        if save_dir:
            for file_path in file_paths:
                file_name = os.path.basename(file_path)
                base_name, original_ext = os.path.splitext(file_name)

                if original_ext == ".las":
                    # Сохраняем файл как .las
                    output_path = os.path.join(save_dir, file_name)
                    las = pylas.read(file_path)
                    las.write(output_path)
                    print(f"Файл: {file_path} сохранён как: {output_path}")

                elif original_ext == ".pcd":
                    # Сохраняем файл как .pcd
                    output_path = os.path.join(save_dir, file_name)
                    points = self.openGLWidget.vbo_data[file_path][0]
                    # Создаем объект PointCloud
                    pcd = o3d.geometry.PointCloud()
                    # Устанавливаем точки в объект PointCloud
                    pcd.points = o3d.utility.Vector3dVector(points)
                    o3d.io.write_point_cloud(output_path, pcd)
                    print(f"Файл: {file_path} сохранён как: {output_path}")

                elif original_ext == ".csv":
                    # Сохраняем файл как .csv
                    output_path = os.path.join(save_dir, file_name)
                    df = pd.read_csv(file_path)
                    df.to_csv(output_path, index=False, sep=";")
                    print(f"Файл: {file_path} сохранён как: {output_path}")

                else:
                    print(f"Неподдерживаемый формат файла: {file_path}")
        