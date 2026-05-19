import os
import open3d as o3d
import numpy as np
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QListWidgetItem, QCheckBox, QApplication, QLabel, QSizePolicy
from .Toolbar_Widgets import modeling
from desktop_segmentation_modeling.config import base_path
from desktop_segmentation_modeling.point_cloud_data import get_points_array_from_clouds
from .Toolbar_Widgets.design import Ui_MainWindow
from .Toolbar_Widgets.console_manager import ConsoleManager
from .menu_bar import MenuBar
from .Toolbar.tool_bar import ToolBar


def get_las_point_format_id(las):
    header = getattr(las, "header", None)
    if header is None:
        return "неизвестно"

    point_format_id = getattr(header, "point_format_id", None)
    if point_format_id is not None:
        return point_format_id

    point_format = getattr(header, "point_format", None)
    if point_format is None:
        return "неизвестно"

    if isinstance(point_format, (int, np.integer)):
        return int(point_format)

    return getattr(point_format, "id", "неизвестно")


class PointCloudLoadWorker(QThread):
    loaded = pyqtSignal(str, object, object, object, object)
    error = pyqtSignal(str, str)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            file_extension = os.path.splitext(self.file_path)[1].lower()
            if file_extension == ".las":
                points, colors, file_metadata = self.load_las()
            elif file_extension == ".pcd":
                points, colors, file_metadata = self.load_pcd()
            else:
                self.error.emit(self.file_path, f"Неподдерживаемый формат файла: {file_extension}")
                return

            render_metadata = self.build_render_metadata(points)
            self.loaded.emit(self.file_path, points, colors, render_metadata, file_metadata)
        except Exception as error:
            self.error.emit(self.file_path, str(error))

    def load_las(self):
        import pylas

        las = pylas.read(self.file_path)
        points = np.column_stack((las.x, las.y, las.z))

        has_rgb = all(hasattr(las, name) for name in ("red", "green", "blue"))
        if has_rgb:
            colors = np.column_stack((las.red, las.green, las.blue)).astype(np.float32)
            color_scale = 65535.0 if np.max(colors) > 255 else 255.0
            colors = np.clip(colors / color_scale, 0.0, 1.0)
        else:
            colors = np.ones((len(points), 3), dtype=np.float32)

        file_metadata = [
            ("Версия", getattr(las.header, "version", "неизвестно")),
            ("Формат точек", get_las_point_format_id(las)),
            ("Scale", self.format_sequence(getattr(las.header, "scales", []))),
            ("Offset", self.format_sequence(getattr(las.header, "offsets", []))),
        ]

        intensity = self.get_las_dimension(las, "intensity")
        if intensity is not None and len(intensity) > 0:
            file_metadata.extend([
                ("Intensity min", int(np.min(intensity))),
                ("Intensity max", int(np.max(intensity))),
                ("Intensity mean", f"{np.mean(intensity):.1f}"),
            ])

        classification = self.get_las_dimension(las, "classification")
        if classification is not None and len(classification) > 0:
            file_metadata.append(("Классов", len(np.unique(classification))))

        return_number = self.get_las_dimension(las, "return_number")
        if return_number is not None and len(return_number) > 0:
            file_metadata.append(("Returns", ", ".join(map(str, np.unique(return_number)))))

        file_metadata.append(("RGB", "есть" if has_rgb else "нет"))

        try:
            crs = las.header.parse_crs()
            if crs:
                file_metadata.append(("CRS", str(crs)))
        except Exception:
            pass

        return points, colors, file_metadata

    def load_pcd(self):
        pcd = o3d.io.read_point_cloud(self.file_path)
        points = np.asarray(pcd.points)
        colors = np.asarray(pcd.colors, dtype=np.float32) if pcd.has_colors() else np.ones_like(points, dtype=np.float32)
        file_metadata = [
            ("Цвета", "есть" if pcd.has_colors() else "нет"),
            ("Нормали", "есть" if pcd.has_normals() else "нет"),
            ("Источник", "файл"),
        ]
        return points, colors, file_metadata

    def build_render_metadata(self, points):
        min_bounds = np.min(points[:, :3], axis=0)
        max_bounds = np.max(points[:, :3], axis=0)
        size = max_bounds - min_bounds
        return {
            'min': min_bounds,
            'max': max_bounds,
            'center': (min_bounds + max_bounds) / 2,
            'max_size': float(np.max(size)),
        }

    def get_las_dimension(self, las, name):
        try:
            return np.asarray(getattr(las, name))
        except Exception:
            return None

    def format_sequence(self, values):
        try:
            return ", ".join(f"{float(value):.6g}" for value in values)
        except Exception:
            return "неизвестно"

class MyMainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(MyMainWindow, self).__init__()
        self.dock_widgets = {}
        self.current_dock = None
        self.current_theme = "dark"

        self.setWindowIcon(QIcon(os.path.join(base_path, "images/Icon.png")))

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
        self.toolbarsCreator.modelingAction.triggered.connect(lambda:
                                                                     self.toggle_dock_widget('modeling',
                                                                        Qt.DockWidgetArea.LeftDockWidgetArea))
        self.toolbarsCreator.modelingAction.triggered.connect(
            lambda checked=False: modeling.show_default_modeling_widget(self)
        )

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
        self._point_cloud_load_workers = {}
        self._cancelled_load_paths = set()
        
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
                    self.cancel_point_cloud_load(file_path)
                    self.openGLWidget.release_model(file_path)
                    print(f"Удалён файл: {file_path}")

                elif file_extension in (".las", ".pcd"):
                    self.cancel_point_cloud_load(file_path)
                    self.openGLWidget.release_point_cloud(file_path)
                    print(f"Удалён файл: {file_path}")

        if not self._has_visible_scene_content():
            self.openGLWidget.reset_camera_view()
        else:
            self.openGLWidget.scale_factor = self.openGLWidget.calculate_scale_factor_for_all()

        self.openGLWidget.update()

    def _has_visible_scene_content(self):
        for path, cloud in self.openGLWidget.point_clouds.items():
            if cloud.get('active') and path in self.openGLWidget.vbo_data:
                return True
        for path, model in self.openGLWidget.models.items():
            if model.get('active') and path in self.openGLWidget.vbo_data_models:
                return True
        return False

    def _file_is_listed(self, file_path):
        for index in range(self.listWidget.count()):
            item = self.listWidget.item(index)
            checkbox = self.listWidget.itemWidget(item)
            if checkbox and checkbox.property("filePath") == file_path:
                return True
        return False

    def cancel_point_cloud_load(self, file_path):
        self._cancelled_load_paths.add(file_path)
        worker = self._point_cloud_load_workers.pop(file_path, None)
        if worker:
            try:
                worker.loaded.disconnect()
                worker.error.disconnect()
            except TypeError:
                pass
            worker.deleteLater()

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
                    self.load_point_cloud_async(file_path)
                else:
                    # Работа с форматом csv
                    pass

            elif state == 0:  # Checkbox is unchecked
                if file_path in self.openGLWidget.point_clouds:
                    self.openGLWidget.point_clouds[file_path]['active'] = False
                    self.openGLWidget.update()
                    self.clear_properties_dock()
                elif file_path in self.openGLWidget.models:
                    self.openGLWidget.models[file_path]['active'] = False
                    self.openGLWidget.update()
                    self.clear_properties_dock()

    def load_point_cloud_async(self, file_path):
        self._cancelled_load_paths.discard(file_path)

        if file_path in self.openGLWidget.vbo_data:
            if file_path not in self.openGLWidget.point_clouds:
                self.openGLWidget.point_clouds[file_path] = {
                    'active': True,
                    'data': None,
                    'full_data': None,
                    'metadata': self.openGLWidget.render_metadata.get(file_path),
                }
            else:
                self.openGLWidget.point_clouds[file_path]['active'] = True
            self.openGLWidget.scale_factor = self.openGLWidget.calculate_scale_factor_for_all()
            self.openGLWidget.update()
            self.update_properties_dock(file_path)
            return

        if file_path in self._point_cloud_load_workers:
            print(f"Файл уже загружается: {file_path}")
            return

        reset_view = not self._has_visible_scene_content()
        worker = PointCloudLoadWorker(file_path)

        def on_loaded(loaded_path, points, colors, render_metadata, file_metadata):
            if loaded_path in self._cancelled_load_paths or not self._file_is_listed(loaded_path):
                self._cancelled_load_paths.discard(loaded_path)
                cleanup_worker(loaded_path)
                return

            self.openGLWidget.load_point_cloud_from_arrays(
                loaded_path,
                points,
                colors=colors,
                full_data=points,
                metadata=render_metadata,
            )
            self.openGLWidget.point_clouds[loaded_path]['file_metadata'] = file_metadata
            if reset_view:
                self.openGLWidget.reset_camera_view()
            else:
                self.openGLWidget.scale_factor = self.openGLWidget.calculate_scale_factor_for_all()
            self.update_properties_dock(loaded_path)
            self.openGLWidget.update()
            cleanup_worker(loaded_path)

        def on_error(loaded_path, error_msg):
            print(f"Ошибка загрузки облака точек {loaded_path}: {error_msg}")
            cleanup_worker(loaded_path)

        def cleanup_worker(loaded_path):
            finished_worker = self._point_cloud_load_workers.pop(loaded_path, None)
            if finished_worker:
                finished_worker.deleteLater()

        worker.loaded.connect(on_loaded)
        worker.error.connect(on_error)
        self._point_cloud_load_workers[file_path] = worker
        print(f"Загрузка облака точек в фоновом потоке: {file_path}")
        worker.start()

    def update_properties_dock(self, file_path):
        if file_path in self.openGLWidget.point_clouds:
            if self.openGLWidget.point_clouds[file_path]['active']:
                self.clear_properties_dock()
                self.add_properties_section("Основные свойства")
                for label, value in self.get_basic_point_cloud_properties(file_path):
                    self.add_property_row(label, value)

                file_extension = os.path.splitext(file_path)[1].lower()
                if file_extension == ".las":
                    self.add_properties_section("LAS")
                    for label, value in self.get_las_properties(file_path):
                        self.add_property_row(label, value)
                elif file_extension == ".pcd":
                    self.add_properties_section("PCD")
                    for label, value in self.get_pcd_properties(file_path):
                        self.add_property_row(label, value)
                self.properties_layout.addStretch()

        if file_path in self.openGLWidget.models:
            if self.openGLWidget.models[file_path]['active']:
                triangles = self.openGLWidget.vbo_data_models[file_path][2] / 3

                self.clear_properties_dock()
                self.add_properties_section("Основные свойства")
                self.add_property_row("Файл", os.path.basename(file_path))
                self.add_property_row("Путь", file_path)
                self.add_property_row("Формат", os.path.splitext(file_path)[1].lower() or "неизвестно")
                self.add_property_row("Тип", "3D-модель")
                self.add_property_row("Статус", "активен")
                self.add_property_row("Полигонов", int(triangles))
                self.properties_layout.addStretch()

    def add_properties_section(self, title):
        label = QLabel(title)
        label.setStyleSheet(
            "font-weight: bold; padding-top: 10px; padding-bottom: 4px;"
        )
        label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.properties_layout.addWidget(label)

    def add_property_row(self, label, value):
        property_label = QLabel(f"{label}: {value}")
        property_label.setWordWrap(True)
        property_label.setStyleSheet(
            "padding-top: 0px; padding-bottom: 0px; margin: 0px;"
        )
        property_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.properties_layout.addWidget(property_label)

    def get_basic_point_cloud_properties(self, file_path):
        file_extension = os.path.splitext(file_path)[1].lower() or "неизвестно"
        points = self.get_point_cloud_points(file_path)
        num_points = len(points) if points is not None else self.openGLWidget.vbo_data.get(file_path, (None, None, 0))[2]

        properties = [
            ("Файл", os.path.basename(file_path)),
            ("Путь", file_path),
            ("Формат", file_extension),
            ("Тип", "облако точек"),
            ("Статус", "активен"),
            ("Количество точек", num_points),
            ("Размер файла", self.format_file_size(file_path)),
        ]

        return properties

    def get_point_cloud_points(self, file_path):
        return get_points_array_from_clouds(self.openGLWidget.point_clouds, file_path)

    def format_file_size(self, file_path):
        if not os.path.exists(file_path):
            return "нет на диске"

        size_bytes = os.path.getsize(file_path)
        units = ["Б", "КБ", "МБ", "ГБ"]
        size = float(size_bytes)
        for unit in units:
            if size < 1024 or unit == units[-1]:
                return f"{size:.1f} {unit}"
            size /= 1024

    def get_las_properties(self, file_path):
        cached_metadata = self.openGLWidget.point_clouds.get(file_path, {}).get('file_metadata')
        if cached_metadata is not None:
            return cached_metadata

        if not os.path.exists(file_path):
            return [("Метаданные", "файл не найден на диске")]

        try:
            las = pylas.read(file_path)
        except Exception as error:
            return [("Ошибка чтения", error)]

        properties = [
            ("Версия", getattr(las.header, "version", "неизвестно")),
            ("Формат точек", get_las_point_format_id(las)),
            ("Scale", self.format_sequence(getattr(las.header, "scales", []))),
            ("Offset", self.format_sequence(getattr(las.header, "offsets", []))),
        ]

        intensity = self.get_las_dimension(las, "intensity")
        if intensity is not None and len(intensity) > 0:
            properties.extend([
                ("Intensity min", int(np.min(intensity))),
                ("Intensity max", int(np.max(intensity))),
                ("Intensity mean", f"{np.mean(intensity):.1f}"),
            ])

        classification = self.get_las_dimension(las, "classification")
        if classification is not None and len(classification) > 0:
            properties.append(("Классов", len(np.unique(classification))))

        return_number = self.get_las_dimension(las, "return_number")
        if return_number is not None and len(return_number) > 0:
            properties.append(("Returns", ", ".join(map(str, np.unique(return_number)))))

        has_rgb = all(self.get_las_dimension(las, name) is not None for name in ("red", "green", "blue"))
        properties.append(("RGB", "есть" if has_rgb else "нет"))

        try:
            crs = las.header.parse_crs()
            if crs:
                properties.append(("CRS", str(crs)))
        except Exception:
            pass

        return properties

    def get_las_dimension(self, las, name):
        try:
            return np.asarray(getattr(las, name))
        except Exception:
            return None

    def get_pcd_properties(self, file_path):
        cached_metadata = self.openGLWidget.point_clouds.get(file_path, {}).get('file_metadata')
        if cached_metadata is not None:
            return cached_metadata

        pcd = None

        if os.path.exists(file_path):
            try:
                pcd = o3d.io.read_point_cloud(file_path)
            except Exception as error:
                return [("Ошибка чтения", error)]
        else:
            cloud_info = self.openGLWidget.point_clouds.get(file_path, {})
            data = cloud_info.get('data')
            if isinstance(data, o3d.geometry.PointCloud):
                pcd = data

        if pcd is None:
            return [("Источник", "сгенерировано в приложении")]

        properties = [
            ("Цвета", "есть" if pcd.has_colors() else "нет"),
            ("Нормали", "есть" if pcd.has_normals() else "нет"),
            ("Источник", "файл" if os.path.exists(file_path) else "память приложения"),
        ]

        return properties

    def format_sequence(self, values):
        try:
            return ", ".join(f"{float(value):.6g}" for value in values)
        except Exception:
            return "неизвестно"

    def clear_properties_dock(self):
        if self.properties_layout:
            for i in reversed(range(self.properties_layout.count())):
                item = self.properties_layout.itemAt(i)
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                else:
                    self.properties_layout.removeItem(item)

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
        self.apply_adaptive_dock_sizes()

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
                import pylas

                las = pylas.read(file_path)
                las.write(save_path)
                print(f"Файл: {file_path} сохранён как: {save_path}")
            elif file_extension == ".pcd":
                points = self.get_point_cloud_points(file_path)
                if points is None:
                    print(f"Не удалось получить точки для сохранения: {file_path}")
                    return
                # Создаем объект PointCloud
                pcd = o3d.geometry.PointCloud()
                # Устанавливаем точки в объект PointCloud
                pcd.points = o3d.utility.Vector3dVector(points)
                o3d.io.write_point_cloud(save_path, pcd)
                print(f"Файл: {file_path} сохранён как: {save_path}")

            elif file_extension == ".csv":
                import pandas as pd

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
                    import pylas

                    # Сохраняем файл как .las
                    output_path = os.path.join(save_dir, file_name)
                    las = pylas.read(file_path)
                    las.write(output_path)
                    print(f"Файл: {file_path} сохранён как: {output_path}")

                elif original_ext == ".pcd":
                    # Сохраняем файл как .pcd
                    output_path = os.path.join(save_dir, file_name)
                    points = self.get_point_cloud_points(file_path)
                    if points is None:
                        print(f"Не удалось получить точки для сохранения: {file_path}")
                        continue
                    # Создаем объект PointCloud
                    pcd = o3d.geometry.PointCloud()
                    # Устанавливаем точки в объект PointCloud
                    pcd.points = o3d.utility.Vector3dVector(points)
                    o3d.io.write_point_cloud(output_path, pcd)
                    print(f"Файл: {file_path} сохранён как: {output_path}")

                elif original_ext == ".csv":
                    import pandas as pd

                    # Сохраняем файл как .csv
                    output_path = os.path.join(save_dir, file_name)
                    df = pd.read_csv(file_path)
                    df.to_csv(output_path, index=False, sep=";")
                    print(f"Файл: {file_path} сохранён как: {output_path}")

                else:
                    print(f"Неподдерживаемый формат файла: {file_path}")
        