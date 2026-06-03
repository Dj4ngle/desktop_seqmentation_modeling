from PyQt6.QtWidgets import (QDockWidget, QCheckBox, QVBoxLayout, QWidget,
                             QPushButton, QLabel, QMessageBox,
                             QGridLayout, QDoubleSpinBox, QScrollArea, QSizePolicy)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import numpy as np
import os
from desktop_segmentation_modeling.point_cloud_data import get_points_array_from_clouds


# Лучший чекпоинт на тестах: одиночные tree_*.pcd 5/5, зал 0/5 (v5 на деревьях 0/5).
TAXATION_CLASSIFIER_MODEL = 'cpl1-1024-rp-s1024-pn2'
MIN_TREE_VOTE_RATIO = 0.8
# Целый файл слишком большой / широкий — таксация одного дерева не имеет смысла.
WHOLE_SCENE_MIN_POINT_COUNT = 250_000
WHOLE_SCENE_MIN_XY_SPAN_M = 18.0


class TaxationWorker(QThread):
    finished_with_results = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, selected_clouds, calculate_dbh, calculate_height, dbh_height):
        super().__init__()
        self.selected_clouds = selected_clouds
        self.calculate_dbh = calculate_dbh
        self.calculate_height = calculate_height
        self.dbh_height = dbh_height

    def run(self):
        try:
            from desktop_segmentation_modeling.Coordinates.predict import StumpPredictor

            predictor = StumpPredictor(TAXATION_CLASSIFIER_MODEL)
            all_results = []
            for file_path, points in self.selected_clouds:
                filename = os.path.basename(file_path)
                model_predictions = {
                    TAXATION_CLASSIFIER_MODEL: predictor.predict_points_detailed(points, votes=5),
                }

                neural_prediction = self.combine_model_predictions(model_predictions)
                neural_label = neural_prediction['label']
                if neural_label == 1 and self.is_whole_scene_not_single_tree(points):
                    neural_label = 0
                    neural_prediction = dict(neural_prediction)
                    neural_prediction['label'] = 0
                    neural_prediction['scene_rejected'] = True
                if neural_label != 1:
                    results = self.build_classification_only_result(points, neural_prediction, neural_label)
                else:
                    results = self.calculate_tree_parameters(points, neural_label, neural_prediction)
                if not results:
                    all_results.append((filename, None, "Расчет не дал результатов"))
                else:
                    all_results.append((filename, results, None))

            self.finished_with_results.emit(all_results)
        except Exception as error:
            self.error.emit(str(error))

    def format_neural_class(self, neural_label, neural_prediction=None):
        if neural_prediction and neural_prediction.get("scene_rejected"):
            neural_class = "Не дерево (сцена / участок)"
        else:
            neural_class = "Дерево" if neural_label == 1 else "Не дерево" if neural_label == 0 else "Не определено"
        if neural_prediction and neural_prediction.get("total_votes", 0) > 0:
            votes_text = (
                f"{neural_prediction['tree_votes']}/{neural_prediction['total_votes']} "
                f"({neural_prediction['confidence'] * 100:.0f}%)"
            )
            neural_class = f"{neural_class} [{votes_text}]"
            model_details = neural_prediction.get("model_details")
            if model_details:
                neural_class = f"{neural_class} | {model_details}"
        return neural_class

    def build_classification_only_result(self, points, neural_prediction, neural_label=0):
        points = np.asarray(points, dtype=np.float32)
        if points.ndim != 2 or points.shape[1] < 3 or len(points) == 0:
            return None

        return {
            'NeuralClass': self.format_neural_class(neural_label, neural_prediction),
            'points_count': len(points),
            'skipped_taxation': True,
        }

    def calculate_tree_parameters(self, points, neural_label, neural_prediction=None):
        points = np.asarray(points, dtype=np.float32)
        if points.ndim != 2 or points.shape[1] < 3 or len(points) == 0:
            return None

        if neural_label != 1:
            return self.build_classification_only_result(points, neural_prediction, neural_label)

        z_min = float(np.min(points[:, 2]))
        z_max = float(np.max(points[:, 2]))
        total_height = z_max - z_min
        if total_height <= 0:
            return None

        xy_center = np.median(points[:, :2], axis=0)
        dbh_radius, stem_xy = self.estimate_stem_center_and_radius(points, z_min, xy_center)
        crown_base = self.estimate_crown_base(points, z_min, z_max, dbh_radius, stem_xy)

        stem_height = max(crown_base - z_min, 0.0)
        crown_height = max(z_max - crown_base, 0.0)
        crown_points = points[points[:, 2] >= crown_base]
        crown_radius = self.estimate_crown_radius(crown_points)

        stem_volume = np.pi * (dbh_radius ** 2) * stem_height
        crown_volume = (np.pi * (crown_radius ** 2) * crown_height) / 3

        neural_class = self.format_neural_class(neural_label, neural_prediction)

        results = {
            'NeuralClass': neural_class,
            'StemRadius': dbh_radius,
            'StemHeight': stem_height,
            'CrownRadius': crown_radius,
            'CrownHeight': crown_height,
            'StemVolume': stem_volume,
            'CrownVolume': crown_volume,
            'TreeVolume': stem_volume + crown_volume,
            'points_count': len(points),
        }

        if self.calculate_height:
            results['Height'] = total_height

        if self.calculate_dbh:
            results['DBH'] = dbh_radius * 2 if dbh_radius > 0 else "Недостаточно точек для DBH"

        return results

    def estimate_stem_center_and_radius(self, points, z_min, fallback_center):
        """
        Ось ствола и радиус на высоте DBH. Медиана по всему облаку смещена к кроне,
        поэтому для поиска основания кроны нужен центр именно среза ствола.
        """
        dbh_section_height = z_min + self.dbh_height
        dbh_section_thickness = 0.1
        z_filter = (points[:, 2] >= dbh_section_height - dbh_section_thickness / 2) & \
                   (points[:, 2] <= dbh_section_height + dbh_section_thickness / 2)
        dbh_points = points[z_filter]

        if len(dbh_points) < 10:
            lower_limit = z_min + max(self.dbh_height, 0.2)
            dbh_points = points[(points[:, 2] >= z_min) & (points[:, 2] <= lower_limit)]

        if len(dbh_points) < 3:
            return 0.0, fallback_center

        center_xy = np.median(dbh_points[:, :2], axis=0) if len(dbh_points) >= 10 else fallback_center
        radii = np.linalg.norm(dbh_points[:, :2] - center_xy, axis=1)
        return float(np.median(radii)), center_xy

    def is_whole_scene_not_single_tree(self, points):
        points = np.asarray(points, dtype=np.float32)
        if points.ndim != 2 or points.shape[1] < 3 or len(points) == 0:
            return False

        xy_span = float(np.max(np.ptp(points[:, :2], axis=0)))
        if xy_span >= WHOLE_SCENE_MIN_XY_SPAN_M:
            return True
        return len(points) >= WHOLE_SCENE_MIN_POINT_COUNT

    def combine_model_predictions(self, model_predictions):
        prediction = model_predictions[TAXATION_CLASSIFIER_MODEL]
        tree_votes = int(prediction.get("tree_votes", 0))
        total_votes = int(prediction.get("total_votes", 0))
        confidence = float(prediction.get("confidence", 0.0))
        label = 1 if confidence >= MIN_TREE_VOTE_RATIO else 0
        short_name = TAXATION_CLASSIFIER_MODEL.split("-")[0]

        return {
            "label": label,
            "tree_votes": tree_votes,
            "total_votes": total_votes,
            "confidence": confidence,
            "model_details": f"{short_name}:{tree_votes}/{total_votes}",
        }

    def estimate_stem_radius(self, points, z_min, fallback_center):
        radius, _ = self.estimate_stem_center_and_radius(points, z_min, fallback_center)
        return radius

    def estimate_crown_base(self, points, z_min, z_max, stem_radius, stem_xy_axis):
        height = z_max - z_min
        if height <= 0:
            return z_min

        bins_count = max(16, min(48, int(height / 0.5)))
        bins = np.linspace(z_min, z_max, bins_count + 1)
        min_search_z = z_min + self.dbh_height
        min_crown_radius = max(stem_radius * 4.0, 0.8)
        min_relative_jump = 0.75

        layer_stats = []
        for low, high in zip(bins[:-1], bins[1:]):
            if high <= min_search_z:
                continue

            layer_points = points[(points[:, 2] >= low) & (points[:, 2] < high)]
            if len(layer_points) < 10:
                continue

            layer_radii = np.linalg.norm(layer_points[:, :2] - stem_xy_axis, axis=1)
            layer_stats.append((float(low), float(np.percentile(layer_radii, 75))))

        if len(layer_stats) < 2:
            return float(z_min + height * 0.55)

        for index in range(1, len(layer_stats)):
            prev_z, prev_radius = layer_stats[index - 1]
            curr_z, curr_radius = layer_stats[index]
            relative_jump = (curr_radius - prev_radius) / max(prev_radius, 1e-6)

            if relative_jump >= min_relative_jump and curr_radius >= min_crown_radius:
                return curr_z

        return float(z_min + height * 0.55)

    def estimate_crown_radius(self, crown_points):
        if len(crown_points) < 3:
            return 0.0

        center_xy = np.median(crown_points[:, :2], axis=0)
        radii = np.linalg.norm(crown_points[:, :2] - center_xy, axis=1)
        return float(np.percentile(radii, 90))


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
        return get_points_array_from_clouds(self.opengl_widget.point_clouds, filename)

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

        # Параметры таксации и настройки
        layout.addWidget(QLabel("⚙️ Нейросетевая таксация PointNet++:"))
        params_layout = QGridLayout()

        # Чекбоксы для выбора параметров
        self.checkbox_dbh = QCheckBox("Диаметр на высоте груди (DBH)")
        self.checkbox_height = QCheckBox("Высота")

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
        layout.addWidget(QLabel("📋 Результаты:"))
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
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid palette(mid);
            }
        """)
        scroll_area.setWidget(self.results_label)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(260)
        scroll_area.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(scroll_area, 1)

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

    if getattr(self, '_taxation_worker', None) and self._taxation_worker.isRunning():
        print("Таксация уже выполняется. Пожалуйста, дождитесь завершения.")
        return

    # Получаем выбранные файлы из главного списка (как в моделировании)
    selected_files = []
    for index in range(self.listWidget.count()):
        item = self.listWidget.item(index)
        checkbox = self.listWidget.itemWidget(item)
        if checkbox and checkbox.isChecked():
            selected_files.append(checkbox.property("filePath"))
    
    if not selected_files:
        self.results_label.setText("⚠️ Ошибка: Выберите хотя бы одно облако точек в виджете 'Файлы'.")
        return

    # Получаем выбранные параметры
    calculate_dbh = self.checkbox_dbh.isChecked()
    calculate_height = self.checkbox_height.isChecked()
    dbh_height = self.spinbox_dbh_height.value()  # Получаем высоту DBH

    selected_clouds = []
    for file_path in selected_files:
        points = self.taxation_logic.get_points(file_path)
        if points is None:
            selected_clouds.append((file_path, None))
        else:
            selected_clouds.append((file_path, points))

    invalid_clouds = [(os.path.basename(file_path), None, "Облако точек не найдено или не имеет полных данных.")
                      for file_path, points in selected_clouds if points is None]
    selected_clouds = [(file_path, points) for file_path, points in selected_clouds if points is not None]

    if not selected_clouds:
        self.results_label.setText(format_taxation_results(invalid_clouds, calculate_dbh, calculate_height, dbh_height))
        return

    self.results_label.setText("Запуск нейросетевой таксации...")
    self._taxation_worker = TaxationWorker(selected_clouds, calculate_dbh, calculate_height, dbh_height)

    def on_finished(worker_results):
        self.results_label.setText(
            format_taxation_results(invalid_clouds + worker_results, calculate_dbh, calculate_height, dbh_height)
        )
        worker = self._taxation_worker
        self._taxation_worker = None
        worker.deleteLater()

    def on_error(error_msg):
        self.results_label.setText(f"Ошибка таксации: {error_msg}")
        worker = self._taxation_worker
        self._taxation_worker = None
        worker.deleteLater()

    self._taxation_worker.finished_with_results.connect(on_finished)
    self._taxation_worker.error.connect(on_error)
    self._taxation_worker.start()


def format_taxation_results(all_results, calculate_dbh, calculate_height, dbh_height):
    result_text = "✅ Результаты нейросетевой таксации:\n\n"
    
    for filename, results, error in all_results:
        if error:
            result_text += f"❌ {filename}: {error}\n\n"
        elif results:
            result_text += f"📊 {filename}:\n"
            result_text += f"  - Класс PointNet++: {results['NeuralClass']}\n"
            result_text += f"  - Количество точек: {results['points_count']}\n"
            if results.get('skipped_taxation'):
                result_text += "  - Таксационные параметры не рассчитывались: объект не распознан как дерево.\n\n"
                continue
            if 'Height' in results and calculate_height:
                result_text += f"  - Высота: {results['Height']:.2f} м\n"
            if 'DBH' in results and calculate_dbh:
                if isinstance(results['DBH'], str):
                    result_text += f"  - DBH: {results['DBH']} (на высоте {dbh_height:.1f} м)\n"
                else:
                    result_text += f"  - DBH: {results['DBH']:.2f} м (на высоте {dbh_height:.1f} м)\n"
            result_text += f"  - Радиус ствола: {results['StemRadius']:.3f} м\n"
            result_text += f"  - Высота ствола: {results['StemHeight']:.2f} м\n"
            result_text += f"  - Радиус кроны: {results['CrownRadius']:.2f} м\n"
            result_text += f"  - Высота кроны: {results['CrownHeight']:.2f} м\n"
            result_text += f"  - Объём ствола: {results['StemVolume']:.3f} м³\n"
            result_text += f"  - Объём кроны: {results['CrownVolume']:.3f} м³\n"
            result_text += f"  - Эффективный объём дерева: {results['TreeVolume']:.3f} м³\n"
            result_text += "\n"

    return result_text