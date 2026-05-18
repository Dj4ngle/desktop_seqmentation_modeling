from PyQt6.QtWidgets import (QDockWidget, QCheckBox, QVBoxLayout, QWidget,
                             QPushButton, QLabel, QMessageBox,
                             QGridLayout, QDoubleSpinBox, QApplication, QScrollArea)
from PyQt6.QtCore import Qt
import numpy as np
import open3d as o3d  # Используем Open3D для обработки облаков точек
import os


# TreeTaxationLogic - это класс для реализации таксации
class TreeTaxationLogic:
    """
    Класс для расчета параметров дерева (DBH, Высота) из облака точек.
    Предполагается, что облако точек центрировано или находится в реальных координатах,
    где Z - это высота.
    """

    def __init__(self, opengl_widget):
        self.opengl_widget = opengl_widget

    def get_points(self, filename):
        cloud_info = self.opengl_widget.point_clouds.get(filename)
        if not cloud_info:
            return None

        points = cloud_info.get('full_data')
        if points is None:
            points = cloud_info.get('data')

        if isinstance(points, o3d.geometry.PointCloud):
            points = np.asarray(points.points)
        elif points is not None:
            points = np.asarray(points)

        if points is None or points.ndim != 2 or points.shape[1] < 3 or len(points) == 0:
            return None

        return points[:, :3]

    def calculate_tree_parameters(self, filename, calculate_dbh=True, calculate_height=True):
        """
        Рассчитывает параметры для выбранного облака точек.

        :param filename: Имя файла облака точек, которое было загружено в OpenGLWidget.
        :param calculate_dbh: Флаг для расчета DBH.
        :param calculate_height: Флаг для расчета Высоты.
        :return: Словарь с результатами {'DBH': value, 'Height': value} или None в случае ошибки.
        """
        points = self.get_points(filename)
        if points is None:
            return None, "Облако точек не найдено или не имеет полных данных."

        # Используем "полные" (неотцентрированные) данные для более точных расчетов высот

        # Если облако точек LAS, оно может быть в метрах или футах, но мы предполагаем,
        # что оси X, Y, Z согласованы и Z соответствует высоте.

        results = {}

        # 1. Расчет Высоты
        if calculate_height:
            z_min = np.min(points[:, 2])
            z_max = np.max(points[:, 2])
            height = z_max - z_min
            results['Height'] = height

        # 2. Расчет DBH (Диаметра на Высоте Груди)
        # Стандартная высота груди - 1.3 метра (или 4.5 фута, если используем футы)
        if calculate_dbh:
            # Предполагаем, что минимальная Z-координата - это уровень земли (0)
            dbh_height = z_min + 1.3
            dbh_section_thickness = 0.1  # Толщина "среза" в метрах (10 см)

            # Выделение точек в области DBH
            z_filter = (points[:, 2] >= dbh_height - dbh_section_thickness / 2) & \
                       (points[:, 2] <= dbh_height + dbh_section_thickness / 2)
            dbh_points = points[z_filter, :]

            if len(dbh_points) < 10:
                results['DBH'] = "Недостаточно точек для DBH"
            else:
                # Используем RANSAC для подгонки круга в плоскости XY
                # Создаем облако точек Open3D для подгонки
                pcd_section = o3d.geometry.PointCloud()
                pcd_section.points = o3d.utility.Vector3dVector(dbh_points)

                # Проекция на плоскость XY
                # DBH = диаметр, поэтому подгоняем круг к проекции точек

                # Это простая аппроксимация, в реальных системах используют более сложный RANSAC
                # или подгонку цилиндра. Здесь мы используем простейший: подгонка круга к точкам XY.
                xy_points = dbh_points[:, :2]

                # Расчет центра масс (грубая оценка центра)
                center_x, center_y = np.mean(xy_points, axis=0)

                # Расчет радиусов до центра
                radii = np.sqrt((xy_points[:, 0] - center_x) ** 2 + (xy_points[:, 1] - center_y) ** 2)

                # DBH - это медианный или средний диаметр
                # Используем медиану для устойчивости к выбросам
                median_radius = np.median(radii)
                dbh = median_radius * 2

                results['DBH'] = dbh

        return results, None


# --- GUI Часть ---

def taxation_dock_widget(self):
    """Создает и возвращает виджет-док для таксации."""
    if 'taxation' not in self.dock_widgets:
        taxation_dock = QDockWidget("🌳 Таксация деревьев")
        taxation_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        widget = QWidget()
        layout = QVBoxLayout()

        # 1. Информация о выборе файлов
        layout.addWidget(QLabel("📂 **Облака точек** (Выберите файлы из списка 'Файлы'):"))
        info_label = QLabel("Используйте чекбоксы в виджете 'Файлы' для выбора облаков точек")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-size: 10pt;")
        layout.addWidget(info_label)

        # 2. Параметры таксации и настройки
        layout.addWidget(QLabel("⚙️ **Параметры для расчета:**"))
        params_layout = QGridLayout()

        # Чекбоксы для выбора параметров
        self.checkbox_dbh = QCheckBox("Диаметр на высоте груди (DBH)")
        self.checkbox_height = QCheckBox("Высота")
        # Ширину кроны оставим для будущей реализации
        # self.checkbox_volume = QCheckBox("Ширина кроны")

        self.checkbox_dbh.setChecked(True)
        self.checkbox_height.setChecked(True)

        params_layout.addWidget(self.checkbox_dbh, 0, 0)
        params_layout.addWidget(self.checkbox_height, 1, 0)
        # params_layout.addWidget(self.checkbox_volume, 2, 0)

        # Поле для ввода высоты DBH
        params_layout.addWidget(QLabel("Высота DBH (м):"), 3, 0)
        self.spinbox_dbh_height = QDoubleSpinBox()
        self.spinbox_dbh_height.setRange(0.1, 3.0)
        self.spinbox_dbh_height.setSingleStep(0.1)
        self.spinbox_dbh_height.setValue(1.3)  # Стандарт 1.3 метра
        params_layout.addWidget(self.spinbox_dbh_height, 3, 1)

        layout.addLayout(params_layout)

        # 3. Кнопка расчета
        get_parameters_button = QPushButton("📊 Рассчитать параметры")
        get_parameters_button.clicked.connect(lambda: run_taxation_calculation(self))
        layout.addWidget(get_parameters_button)

        # 4. Поле для вывода результатов
        layout.addWidget(QLabel("📋 **Результаты:**"))
        self.results_label = QLabel("Выберите облака точек в виджете 'Файлы' и нажмите 'Рассчитать параметры'.")
        self.results_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)  # Чтобы можно было копировать текст
        self.results_label.setWordWrap(True)  # Перенос текста
        self.results_label.setStyleSheet("""
            QLabel {
                padding: 5px;
                border-radius: 3px;
            }
        """)
        
        # Создаем скроллируемую область для результатов
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.results_label)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(200)  # Ограничиваем максимальную высоту
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(scroll_area)

        widget.setLayout(layout)
        taxation_dock.setWidget(widget)
        self.dock_widgets['taxation'] = taxation_dock

        # Инициализация логики
        if not hasattr(self, 'taxation_logic') and hasattr(self, 'openGLWidget'):
            self.taxation_logic = TreeTaxationLogic(self.openGLWidget)

    return self.dock_widgets['taxation']


def run_taxation_calculation(self):
    """
    Выполняет логику расчета таксации при нажатии на кнопку.
    """
    if not hasattr(self, 'taxation_logic'):
        QMessageBox.warning(self, "Ошибка", "Логика таксации не инициализирована.")
        return

    # Получаем выбранные файлы из главного списка (как в моделировании)
    selected_files = []
    for index in range(self.listWidget.count()):
        item = self.listWidget.item(index)
        checkbox = self.listWidget.itemWidget(item)
        if checkbox and checkbox.isChecked():
            selected_files.append(checkbox.property("filePath"))
    
    if not selected_files:
        self.results_label.setText("⚠️ **Ошибка:** Выберите хотя бы одно облако точек в виджете 'Файлы'.")
        return

    # Получаем выбранные параметры
    calculate_dbh = self.checkbox_dbh.isChecked()
    calculate_height = self.checkbox_height.isChecked()
    dbh_height = self.spinbox_dbh_height.value()  # Получаем высоту DBH

    # Обновляем логику для использования dbh_height
    # Создаем временный класс или обновляем существующий
    class TaxationLogicWithDBHHeight(TreeTaxationLogic):
        def calculate_tree_parameters(self, filename, calculate_dbh=True, calculate_height=True, dbh_height=1.3):
            points = self.get_points(filename)
            if points is None:
                return None, "Облако точек не найдено или не имеет полных данных."

            results = {}
            
            if calculate_height:
                z_min = np.min(points[:, 2])
                z_max = np.max(points[:, 2])
                height = z_max - z_min
                results['Height'] = height
            
            if calculate_dbh:
                z_min = np.min(points[:, 2])
                dbh_section_height = z_min + dbh_height
                dbh_section_thickness = 0.1
                
                z_filter = (points[:, 2] >= dbh_section_height - dbh_section_thickness / 2) & \
                           (points[:, 2] <= dbh_section_height + dbh_section_thickness / 2)
                dbh_points = points[z_filter, :]
                
                if len(dbh_points) < 10:
                    results['DBH'] = "Недостаточно точек для DBH"
                else:
                    xy_points = dbh_points[:, :2]
                    center_x, center_y = np.mean(xy_points, axis=0)
                    radii = np.sqrt((xy_points[:, 0] - center_x) ** 2 + (xy_points[:, 1] - center_y) ** 2)
                    median_radius = np.median(radii)
                    dbh = median_radius * 2
                    results['DBH'] = dbh
            
            return results, None
    
    # Используем обновленную логику
    taxation_logic = TaxationLogicWithDBHHeight(self.openGLWidget)
    
    # Выполняем расчет для каждого выбранного файла
    all_results = []
    for file_path in selected_files:
        filename = os.path.basename(file_path)
        self.results_label.setText(f"Расчет параметров для: **{filename}**...")
        QApplication.processEvents()  # Обновляем UI
        
        results, error = taxation_logic.calculate_tree_parameters(
            file_path,
            calculate_dbh=calculate_dbh,
            calculate_height=calculate_height,
            dbh_height=dbh_height
        )
        
        if error:
            all_results.append((filename, None, error))
        elif not results:
            all_results.append((filename, None, "Расчет не дал результатов"))
        else:
            all_results.append((filename, results, None))
    
    # Форматирование и вывод результатов
    result_text = "✅ **Результаты таксации:**\n\n"
    
    for filename, results, error in all_results:
        if error:
            result_text += f"❌ **{filename}:** {error}\n\n"
        elif results:
            result_text += f"📊 **{filename}:**\n"
            if 'Height' in results and calculate_height:
                result_text += f"  - Высота: {results['Height']:.2f} м\n"
            if 'DBH' in results and calculate_dbh:
                if isinstance(results['DBH'], str):
                    result_text += f"  - DBH: {results['DBH']} (на высоте {dbh_height:.1f} м)\n"
                else:
                    result_text += f"  - DBH: {results['DBH']:.2f} м (на высоте {dbh_height:.1f} м)\n"
            result_text += "\n"
    
    self.results_label.setText(result_text)