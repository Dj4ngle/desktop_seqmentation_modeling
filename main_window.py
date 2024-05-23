import os
import sys
from datetime import datetime, timedelta
import open3d as o3d
from OpenGL.GL import glDeleteBuffers
from OpenGL.raw.GL.VERSION.GL_1_0 import glFlush, glFinish
from OpenGL.raw.GL.VERSION.GL_1_5 import glBindBuffer, GL_ARRAY_BUFFER, GL_ELEMENT_ARRAY_BUFFER
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QListWidgetItem, QCheckBox, QApplication, QLabel
import numpy as np
from design import Ui_MainWindow
from console_manager import ConsoleManager
from menu_bar import MenuBar
from tool_bar import ToolBar
from sklearn.cluster import DBSCAN
import pylas


class MyMainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(MyMainWindow, self).__init__()
        self.dock_widgets = {}
        self.current_dock = None
        self.current_file_path = None

        self.setWindowIcon(QIcon("images/Icon.png"))

        self.setupUi(self)

        # Создаем экземпляр для управления консолью
        self.consoleManager = ConsoleManager(self)
        # Создаем виджет док-панели для консоли
        self.console_dock_widget = self.consoleManager.create_console_dock_widget()
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.console_dock_widget)
        # Перенаправляем стандартный вывод в консоль
        self.consoleManager.redirect_console_output()

        self.ground_extraction_dock_widget()

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
        self.toolbarsCreator.earthExtractionAction.triggered.connect(self.update_clouds_list)
        self.toolbarsCreator.segmentationAction.triggered.connect(lambda:
                                                                     self.toggle_dock_widget('segmentation',
                                                                        Qt.DockWidgetArea.LeftDockWidgetArea))
        self.toolbarsCreator.taxationAction.triggered.connect(lambda:
                                                                     self.toggle_dock_widget('taxation',
                                                                        Qt.DockWidgetArea.LeftDockWidgetArea))
        self.toolbarsCreator.modelingAction.triggered.connect(lambda:
                                                                     self.toggle_dock_widget('modeling',
                                                                        Qt.DockWidgetArea.LeftDockWidgetArea))
        self.toolbarsCreator.modelingAction.triggered.connect(self.show_default_modeling_widget)

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


    # def perform_ground_extraction(self, file_path):
    #     if file_path in self.openGLWidget.point_clouds:
    #         original_pcd = self.openGLWidget.point_clouds[file_path]

    #         # Пример простой сегментации земли
    #         plane_model, inliers = original_pcd.segment_plane(distance_threshold=0.6,
    #                                                         ransac_n=4,
    #                                                         num_iterations=1000)
    #         ground = original_pcd.select_by_index(inliers)
    #         objects = original_pcd.select_by_index(inliers, invert=True)

    #         # Изменяем расширение файла и добавляем _ground и _objects
    #         file_extension = os.path.splitext(file_path)[1]
    #         ground_file_path = file_path.replace(file_extension, "_ground" + file_extension)
    #         objects_file_path = file_path.replace(file_extension, "_objects" + file_extension)

    #         # Добавляем результаты в виджет для визуализации
    #         self.openGLWidget.point_clouds[ground_file_path] = ground
    #         self.openGLWidget.point_clouds[objects_file_path] = objects
    #         self.openGLWidget.update()

    def perform_ground_extraction(self, file_path):
        if file_path in self.openGLWidget.point_clouds:
            points = self.openGLWidget.point_clouds[file_path]['data']

            original_pcd = o3d.geometry.PointCloud()
            original_pcd.points = o3d.utility.Vector3dVector(points)
            
            # 0.3, 30, 0.1, 5
            # Оценка нормалей
            original_pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.3, max_nn=30))
            normals = np.asarray(original_pcd.normals)
            normal_threshold=0.1
            height_offset=5

            # Фильтрация нормалей и высоты
            idx_normals = np.where((abs(normals[:, 1]) < normal_threshold))
            idx_ground = np.where(points[:, 1] > np.min(points[:, 1]) + height_offset)
            idx_wronglyfiltered = np.setdiff1d(idx_ground[0], idx_normals[0])
            idx_retained = np.append(idx_normals[0], idx_wronglyfiltered)

            # Оставшиеся точки
            points_retained = points[idx_retained]

            # Точки земли
            idx_all = np.arange(points.shape[0])
            idx_inv = np.setdiff1d(idx_all, idx_retained)
            points_ground = points[idx_inv]

            # Создание облаков точек
            ground = o3d.geometry.PointCloud()
            ground.points = o3d.utility.Vector3dVector(points_ground)

            objects = o3d.geometry.PointCloud()
            objects.points = o3d.utility.Vector3dVector(points_retained)

            # Окрашивание точек земли
            colors_ground = np.zeros(points_ground.shape)
            colors_ground[:, 0] = 1
            colors_ground[:, 1] = 0.2
            colors_ground[:, 2] = 0.2
            ground.colors = o3d.utility.Vector3dVector(colors_ground)

            # Изменяем расширение файла и добавляем _ground и _objects
            file_extension = os.path.splitext(file_path)[1]
            ground_file_path = file_path.replace(file_extension, "_ground" + file_extension)
            objects_file_path = file_path.replace(file_extension, "_objects" + file_extension)

            # Добавляем результаты в виджет для визуализации
            self.openGLWidget.point_clouds[ground_file_path] = {'active': True, 'data': ground}
            self.openGLWidget.point_clouds[objects_file_path] = {'active': True, 'data': objects}
            self.openGLWidget.update()

    def select_files(self):
        # Метод для выбора файлов
        files, _ = QFileDialog.getOpenFileNames(self, "Выбрать файлы", "", "LAS and PCD files (*.las *.obj *.pcd)")

        if files:
            for file in files:
                # Создание нового элемента QListWidgetItem
                item = QListWidgetItem(self.listWidget)

                # Создание чекбокса с именем файла
                checkbox = QCheckBox(file)
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
                if os.path.exists(file_path):
                    _, file_extension = os.path.splitext(file_path)
                    if file_extension == ".obj":
                        self.openGLWidget.load_model(file_path)
                        self.update_properties_dock(file_path)
                    else:
                        self.openGLWidget.load_point_cloud(file_path)
                        self.update_properties_dock(file_path)
                else:
                    print(f"Файл {file_path} не найден")
            elif state == 0:  # Checkbox is unchecked
                if file_path in self.openGLWidget.point_clouds:
                    del self.openGLWidget.point_clouds[file_path]
                    self.openGLWidget.update()
                    self.clear_properties_dock()
                elif file_path in self.openGLWidget.models:
                    del self.openGLWidget.models[file_path]
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
                                                   "LAS Files (*.las);;PCD Files (*.pcd)")
        if save_path:
            # Определяем расширение файла
            file_extension = os.path.splitext(save_path)[1]

            if file_extension == ".las":
                las = pylas.read(file_path)
                las.write(save_path)
                print(f"Файл: {file_path} сохранён как: {save_path}")
            elif file_extension == ".pcd":
                points = self.openGLWidget.point_clouds[file_path]['data']
                # Создаем объект PointCloud
                pcd = o3d.geometry.PointCloud()
                # Устанавливаем точки в объект PointCloud
                pcd.points = o3d.utility.Vector3dVector(points)
                o3d.io.write_point_cloud(save_path, pcd)
                print(f"Файл: {file_path} сохранён как: {save_path}")

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
                    points = self.openGLWidget.point_clouds[file_path]['data']
                    # Создаем объект PointCloud
                    pcd = o3d.geometry.PointCloud()
                    # Устанавливаем точки в объект PointCloud
                    pcd.points = o3d.utility.Vector3dVector(points)
                    o3d.io.write_point_cloud(output_path, pcd)
                    print(f"Файл: {file_path} сохранён как: {output_path}")

                else:
                    print(f"Неподдерживаемый формат файла: {file_path}")
