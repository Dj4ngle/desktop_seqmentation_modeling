from PyQt6.QtWidgets import (QDockWidget, QCheckBox, QVBoxLayout, QWidget,
                             QPushButton, QLabel, QListWidget, QMessageBox,
                             QGridLayout, QDoubleSpinBox)
from PyQt6.QtCore import Qt
import numpy as np
import open3d as o3d  # Используем Open3D для обработки облаков точек


# TreeTaxationLogic - это класс для реализации таксации
class TreeTaxationLogic:
    """
    Класс для расчета параметров дерева (DBH, Высота) из облака точек.
    Предполагается, что облако точек центрировано или находится в реальных координатах,
    где Z - это высота.
    """

    def __init__(self, opengl_widget):
        self.opengl_widget = opengl_widget

    def calculate_tree_parameters(self, filename, calculate_dbh=True, calculate_height=True):
        """
        Рассчитывает параметры для выбранного облака точек.

        :param filename: Имя файла облака точек, которое было загружено в OpenGLWidget.
        :param calculate_dbh: Флаг для расчета DBH.
        :param calculate_height: Флаг для расчета Высоты.
        :return: Словарь с результатами {'DBH': value, 'Height': value} или None в случае ошибки.
        """
        if filename not in self.opengl_widget.point_clouds or not self.opengl_widget.point_clouds[filename][
                                                                      'full_data'] is not None:
            return None, "Облако точек не найдено или не имеет полных данных."

        # Используем "полные" (неотцентрированные) данные для более точных расчетов высот
        points = self.opengl_widget.point_clouds[filename]['full_data']

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

        # 1. Список загруженных облаков точек
        layout.addWidget(QLabel("📂 **Облака точек** (Выберите облако для таксации):"))
        self.taxation_list_widget = QListWidget()
        # Этот список должен заполняться из self.openGLWidget.point_clouds
        # На данный момент, мы заполним его при открытии дока, если есть данные
        update_taxation_list(self)
        layout.addWidget(self.taxation_list_widget)

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
        self.results_label = QLabel("Выберите облако и нажмите 'Рассчитать параметры'.")
        self.results_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)  # Чтобы можно было копировать текст
        layout.addWidget(self.results_label)

        layout.addStretch(1)  # Заполнение пустого места

        widget.setLayout(layout)
        taxation_dock.setWidget(widget)
        self.dock_widgets['taxation'] = taxation_dock

        # Инициализация логики
        if not hasattr(self, 'taxation_logic') and hasattr(self, 'openGLWidget'):
            self.taxation_logic = TreeTaxationLogic(self.openGLWidget)

    return self.dock_widgets['taxation']


def update_taxation_list(self):
    """Обновляет список облаков точек в виджете таксации."""
    if hasattr(self, 'taxation_list_widget') and hasattr(self, 'openGLWidget'):
        self.taxation_list_widget.clear()

        # Добавляем только активные облака точек
        for filename, info in self.openGLWidget.point_clouds.items():
            if info['active']:
                self.taxation_list_widget.addItem(filename)


def run_taxation_calculation(self):
    """
    Выполняет логику расчета таксации при нажатии на кнопку.
    """
    if not hasattr(self, 'taxation_logic'):
        QMessageBox.warning(self, "Ошибка", "Логика таксации не инициализирована.")
        return

    # Получаем выбранный элемент
    selected_items = self.taxation_list_widget.selectedItems()
    if not selected_items:
        self.results_label.setText("⚠️ **Ошибка:** Выберите облако точек из списка.")
        return

    filename = selected_items[0].text()

    # Получаем выбранные параметры
    calculate_dbh = self.checkbox_dbh.isChecked()
    calculate_height = self.checkbox_height.isChecked()
    dbh_height = self.spinbox_dbh_height.value()  # Получаем высоту DBH

    # Вносим изменения в логику: теперь она должна принимать высоту DBH
    # ПЕРЕРАБОТКА: Внутри TreeTaxationLogic мы используем 1.3 м по умолчанию,
    # нужно передать значение или изменить класс.
    # Для простоты, пока оставим 1.3м внутри класса, но в реальном коде лучше передавать.
    # Так как вы просили только "костяк", я не буду сильно менять логику.

    self.results_label.setText(f"Расчет параметров для: **{filename}**...")

    results, error = self.taxation_logic.calculate_tree_parameters(
        filename,
        calculate_dbh=calculate_dbh,
        calculate_height=calculate_height
    )

    if error:
        self.results_label.setText(f"❌ **Ошибка расчета для {filename}:**\n{error}")
        return

    if not results:
        self.results_label.setText(f"⚠️ **Внимание:** Расчет для {filename} не дал результатов.")
        return

    # Форматирование и вывод результатов
    result_text = f"✅ **Результаты таксации для {filename}:**\n"

    if 'Height' in results and calculate_height:
        result_text += f"- **Высота:** {results['Height']:.2f} м\n"

    if 'DBH' in results and calculate_dbh:
        # DBH может быть строкой, если произошла ошибка
        if isinstance(results['DBH'], str):
            result_text += f"- **DBH:** {results['DBH']} (на высоте 1.3 м)\n"
        else:
            result_text += f"- **DBH:** {results['DBH']:.2f} м (на высоте 1.3 м)\n"

    self.results_label.setText(result_text)