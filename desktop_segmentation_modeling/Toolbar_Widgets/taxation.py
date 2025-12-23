from PyQt6.QtWidgets import (QDockWidget, QCheckBox, QVBoxLayout, QWidget,
                             QPushButton, QLabel, QMessageBox,
                             QGridLayout, QDoubleSpinBox, QApplication, QScrollArea)
from PyQt6.QtCore import Qt
import numpy as np
import open3d as o3d  # Используем Open3D для обработки облаков точек
import os
import time
import logging
import torch
from pathlib import Path
from pyntcloud import PyntCloud
import desktop_segmentation_modeling
from desktop_segmentation_modeling.Coordinates.predictmdl.models.pointnet2_cls_ssg import get_model
import desktop_segmentation_modeling.Coordinates.predictmdl.utils.pointcloud_utils as pcu

# Настройка логирования для измерения производительности
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('taxation_performance.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
performance_logger = logging.getLogger('performance')


class PerformanceMeasurement:
    """
    Класс для измерения производительности автоматизированной таксации леса.
    Измеряет время трёх этапов: загрузка данных, инициализация модели, инференс.
    Сравнивает экспериментальные результаты с теоретическими значениями.
    
    Формулы для расчета теоретического времени:
    
    1. Загрузка данных:
       T_load = V_points / B_io
       где V_points = N_points * bytes_per_point
    
    2. Инициализация модели:
       T_init = T_model_load + T_memory_alloc + T_config
       где:
       - T_model_load = (model_params_count * bytes_per_param) / B_io + overhead
       - T_memory_alloc = (model_params_count * bytes_per_param) / memory_bandwidth + overhead
       - T_config = overhead
    
    3. Инференс:
       T_inference = (N_points * FLOPs_per_point) / GPU_FLOPS + T_overhead
       где T_overhead включает передачу данных CPU->GPU и задержки батчей
    
    Пример использования:
        >>> perf = PerformanceMeasurement(model_name='cpl1-1024-rp-s1024-pn2')
        >>> points, _ = perf.load_data(file_path="data.pcd")
        >>> perf.initialize_model()  # Реальная загрузка PointNet2
        >>> results, _ = perf.run_inference(points)  # Реальный инференс
        >>> summary = perf.print_summary()
    """
    
    def __init__(self, model_name='cpl1-1024-rp-s1024-pn2'):
        """
        :param model_name: Имя модели из папки checkpoints (по умолчанию 'cpl1-1024-rp-s1024-pn2')
        """
        # Параметры системы (можно настроить под конкретное оборудование)
        self.bytes_per_point = 12  # 3 координаты (x, y, z) по 4 байта (float32)
        self.B_io = 50 * 1024 * 1024  # Пропускная способность интерфейса: 50 MB/s
        
        # Параметры модели нейросети
        self.model_name = model_name
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model_params_count = None  # Будет рассчитано после загрузки модели
        self.bytes_per_param = 4  # float32
        self.memory_bandwidth = 100 * 1024 * 1024 * 1024  # 100 GB/s пропускная способность памяти
        self.T_model_load_overhead = 0.1  # Накладные расходы на загрузку модели (сек)
        self.T_memory_alloc_overhead = 0.05  # Накладные расходы на аллокацию памяти (сек)
        self.T_config_overhead = 0.02  # Накладные расходы на конфигурацию (сек)
        
        # Параметры инференса
        self.FLOPs_per_point = 1000  # Количество операций с плавающей точкой на точку (приблизительно)
        self.GPU_FLOPS = 10 * 10**12  # 10 TFLOPS производительность GPU (приблизительно)
        self.sample_points = 2048  # Количество точек для семплирования (FPS)
        self.CPU_GPU_transfer_overhead = 0.001  # Накладные расходы на передачу батча CPU->GPU (сек)
        
        self.results = {}

        torch.set_num_threads(16)
    
    def load_data(self, file_path=None, n_points=None):
        """
        Этап 1: Загрузка данных.
        
        Теоретическое время: T_load = V_points / B_io
        где V_points = N_points * bytes_per_point
        
        :param file_path: Путь к файлу облака точек (опционально)
        :param n_points: Количество точек для синтетической генерации (если file_path не указан)
        :return: numpy array с точками, фактическое время загрузки
        """
        start_time = time.time()
        pcd = o3d.io.read_point_cloud(file_path)
        points = np.asarray(pcd.points)
        actual_time = time.time() - start_time
        
        # Расчет теоретического времени
        N_points = len(points)
        V_points = N_points * self.bytes_per_point
        theoretical_time = V_points / self.B_io
        
        # Логирование результатов
        error = abs(actual_time - theoretical_time) / theoretical_time if theoretical_time > 0 else 0
        
        performance_logger.info("=" * 60)
        performance_logger.info("ЭТАП 1: ЗАГРУЗКА ДАННЫХ")
        performance_logger.info(f"  Количество точек: {N_points:,}")
        performance_logger.info(f"  Объём данных: {V_points / (1024**2):.2f} MB")
        performance_logger.info(f"  Фактическое время: {actual_time:.4f} сек")
        performance_logger.info("=" * 60)
        
        self.results['load'] = {
            'theoretical_time': theoretical_time,
            'actual_time': actual_time,
            'error': error,
            'n_points': N_points,
            'data_volume_mb': V_points / (1024**2)
        }
        
        return points, actual_time
    
    def farthest_point_sample(self, xyz, npoint):
        """Farthest Point Sampling для уменьшения количества точек"""
        device = xyz.device
        batchsize, ndataset, dimension = xyz.shape
        centroids = torch.zeros(batchsize, npoint, dtype=torch.long).to(device)
        distance = torch.ones(batchsize, ndataset).to(device) * 1e10
        farthest = torch.randint(0, ndataset, (batchsize,), dtype=torch.long).to(device)
        batch_indices = torch.arange(batchsize, dtype=torch.long).to(device)
        for i in range(npoint):
            centroids[:, i] = farthest
            centroid = xyz[batch_indices, farthest, :].view(batchsize, 1, 3)
            dist = torch.sum((xyz - centroid) ** 2, -1)
            mask = dist < distance
            distance[mask] = dist[mask]
            farthest = torch.max(distance, -1)[1]
        return centroids

    def initialize_model(self):
        """
        ЭТАП 2: Инициализация нейросети.
        Выполняется замер трех составляющих согласно математическому описанию.
        """

        # --- Подготовка (поиск пути) ---
        package_file = Path(desktop_segmentation_modeling.__file__).resolve()
        package_dir = package_file.parent
        model_path = package_dir / 'Coordinates' / 'predictmdl' / 'checkpoints' / self.model_name / 'models' / 'model.t7'

        if not os.path.exists(model_path):
            checkpoints_dir = package_dir / 'Coordinates' / 'predictmdl' / 'checkpoints'
            available_models = [d for d in os.listdir(checkpoints_dir) if os.path.isdir(checkpoints_dir / d)]
            if available_models:
                self.model_name = available_models[0]
                model_path = checkpoints_dir / self.model_name / 'models' / 'model.t7'

        model_path_str = str(model_path)

        # 1. t_загр.модели — Время чтения файла с диска
        t_load_start = time.time()
        # Загружаем веса в CPU (чистое чтение файла в RAM)
        state_dict = torch.load(model_path_str, map_location='cpu')
        t_model_load = time.time() - t_load_start

        # 2. t_аллокация — Время выделения памяти (RAM/VRAM)
        t_alloc_start = time.time()
        NUM_CLASSES = 2
        # Создаем структуру и переносим на целевое устройство (self.device)
        self.model = get_model(NUM_CLASSES, normal_channel=False).to(self.device)
        t_allocation = time.time() - t_alloc_start

        # 3. t_конфигурация — Время настройки параметров и графа
        t_config_start = time.time()
        # Копируем считанные веса в аллоцированную модель
        self.model.load_state_dict(state_dict)
        self.model.eval()
        t_configuration = time.time() - t_config_start

        # --- Сбор характеристик модели ---
        # Количество параметров
        self.model_params_count = sum(p.numel() for p in self.model.parameters())
        # Вес одного параметра в байтах (element_size)
        first_param = next(self.model.parameters())
        bytes_per_param = first_param.element_size()
        # Общий объем в МБ
        model_size_mb = (self.model_params_count * bytes_per_param) / (1024 ** 2)

        total_actual_time = t_model_load + t_allocation + t_configuration

        # --- Логирование в стиле вашего скриншота ---
        performance_logger.info("=" * 60)
        performance_logger.info("ЭТАП 2: ИНИЦИАЛИЗАЦИЯ НЕЙРОСЕТИ")
        performance_logger.info(f"  Количество параметров: {self.model_params_count:,}")
        performance_logger.info(f"  Вес одного параметра: {bytes_per_param} байта(ов)")
        performance_logger.info(f"  Общий объём модели: {model_size_mb:.2f} MB")
        performance_logger.info(f"  t_загр.модели (чтение): {t_model_load:.4f} сек")
        performance_logger.info(f"  t_аллокация (память): {t_allocation:.4f} сек")
        performance_logger.info(f"  t_конфигурация (настройка): {t_configuration:.4f} сек")
        performance_logger.info(f"  Фактическое время (итого): {total_actual_time:.4f} сек")
        performance_logger.info("=" * 60)

        # Сохранение результатов
        self.results['init'] = {
            'actual_time': total_actual_time,
            't_model_load': t_model_load,
            't_allocation': t_allocation,
            't_configuration': t_configuration,
            'model_params': self.model_params_count,
            'bytes_per_param': bytes_per_param
        }

        return total_actual_time

    def run_inference(self, points):
        """
        ЭТАП 3: ОБРАБОТКА ДАННЫХ (ИНФЕРЕНС)
        Разделение на Семплирование (FPS) и Чистый Инференс (Forward Pass).
        """
        if self.model is None:
            raise ValueError("Модель не инициализирована. Вызовите initialize_model() сначала.")

        # 0. Старт замера общего времени этапа
        overall_start = time.time()
        N_points = len(points)

        # --- Подготовка тензора ---
        prep_start = time.time()
        points_batch = np.array([points])
        points_tensor = torch.Tensor(points_batch).to(self.device)
        t_prep_tensor = time.time() - prep_start

        # --- 1. t_fps: СЕМПЛИРОВАНИЕ (Подготовка входов) ---
        # Сложность O(N_points * sample_points)
        fps_start = time.time()
        centroids = self.farthest_point_sample(points_tensor, self.sample_points)
        pc_sampled = points_tensor[0][centroids[0]]
        t_fps = time.time() - fps_start

        # --- 2. НОРМАЛИЗАЦИЯ (Предобработка) ---
        norm_start = time.time()
        pc_sampled_np = pc_sampled.cpu().detach().numpy()
        X_test = np.array([pc_sampled_np])
        X_test = pcu.tree_normalize(X_test)
        data = torch.tensor(X_test, device=self.device).permute(0, 2, 1)
        t_normalization = time.time() - norm_start

        # --- 3. t_инференс: ЧИСТЫЙ ИНФЕРЕНС (Работа нейросети) ---
        # Сложность O(sample_points * FLOPs_per_point)
        inference_start = time.time()
        with torch.no_grad():
            logits, _ = self.model(data)
            # Получаем предсказание (0 - дерево, 1 - фон)
            preds = logits.max(dim=1)[1].detach().cpu().numpy()
        t_pure_inference = time.time() - inference_start

        # Итоговое фактическое время
        total_actual_time = time.time() - overall_start

        # Определение результата
        pred_value = int(preds.flat[0])
        prediction = 1 if pred_value == 0 else 0

        # --- Логирование в стиле ЭТАПА 2 ---
        performance_logger.info("=" * 60)
        performance_logger.info("ЭТАП 3: ОБРАБОТКА ДАННЫХ (ИНФЕРЕНС)")
        performance_logger.info(f"  Исходное количество точек (N_от): {N_points:,}")
        performance_logger.info(f"  Входов нейросети (N_sampled): {self.sample_points:,}")
        performance_logger.info(f"  Сложность дистанции (C_dist): 9 FLOPs")
        performance_logger.info(f"  FLOPs на точку инференса: {self.FLOPs_per_point:,}")
        performance_logger.info("-" * 60)
        performance_logger.info(f"  t_fps (семплирование):       {t_fps:.4f} сек")
        performance_logger.info(f"  t_инференс (нейросеть):      {t_pure_inference:.4f} сек")
        performance_logger.info(f"  Фактическое время (итого):   {total_actual_time:.4f} сек")
        performance_logger.info("-" * 60)
        performance_logger.info(f"  Результат распознавания: {'ДЕРЕВО' if prediction == 1 else 'НЕ ДЕРЕВО'}")
        performance_logger.info("=" * 60)

        # Сохранение для отчета
        self.results['inference'] = {
            'actual_time': total_actual_time,
            't_fps': t_fps,
            't_pure_inference': t_pure_inference,
            'n_points': N_points,
            'sample_points': self.sample_points
        }

        return prediction, total_actual_time
    
    def print_summary(self):
        """Выводит сводку по всем этапам."""
        performance_logger.info("\n" + "=" * 60)
        performance_logger.info("СВОДКА ПО ВСЕМ ЭТАПАМ")
        performance_logger.info("=" * 60)

        total_actual = sum(r['actual_time'] for r in self.results.values())
        
        for stage_name, stage_data in self.results.items():
            stage_ru = {
                'load': 'Загрузка данных',
                'init': 'Инициализация модели',
                'inference': 'Инференс'
            }.get(stage_name, stage_name)
            
            performance_logger.info(f"\n{stage_ru}:")

            performance_logger.info(f"  Фактическое время: {stage_data['actual_time']:.4f} сек")


        
        performance_logger.info("\n" + "-" * 60)
        performance_logger.info("ОБЩЕЕ ВРЕМЯ:")

        performance_logger.info(f"  Фактическое: {total_actual:.4f} сек")

        performance_logger.info("=" * 60 + "\n")
        
        return {

            'total_actual': total_actual,

        }


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

        # Чекбокс для измерения производительности
        self.checkbox_performance = QCheckBox("Измерить производительность")
        self.checkbox_performance.setChecked(False)
        params_layout.addWidget(self.checkbox_performance, 4, 0)

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


def run_performance_measurement(file_path=None, n_points=None, model_name='cpl1-1024-rp-s1024-pn2'):
    """
    Отдельная функция для запуска измерения производительности.
    Может использоваться независимо от GUI для тестирования и анализа.
    
    :param file_path: Путь к файлу облака точек (опционально)
    :param n_points: Количество точек для синтетической генерации (если file_path не указан)
    :param model_name: Имя модели из папки checkpoints
    :return: словарь с результатами измерения производительности
    """
    perf_measurement = PerformanceMeasurement(model_name=model_name)
    
    performance_logger.info("\n" + "=" * 60)
    performance_logger.info("НАЧАЛО ИЗМЕРЕНИЯ ПРОИЗВОДИТЕЛЬНОСТИ")
    performance_logger.info("=" * 60)
    
    # Этап 1: Загрузка данных
    points, _ = perf_measurement.load_data(file_path=file_path, n_points=n_points)
    
    # Этап 2: Инициализация модели
    perf_measurement.initialize_model()
    
    # Этап 3: Инференс
    inference_results, _ = perf_measurement.run_inference(points)
    
    # Вывод сводки
    summary = perf_measurement.print_summary()
    
    return {
        'measurement': perf_measurement,
        'summary': summary,
        'results': perf_measurement.results,
        'inference_results': inference_results
    }


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
    measure_performance = self.checkbox_performance.isChecked() if hasattr(self, 'checkbox_performance') else False

    # Измерение производительности (если включено)
    perf_measurement = None
    if measure_performance:
        perf_measurement = PerformanceMeasurement()
        performance_logger.info("\n" + "=" * 60)
        performance_logger.info("НАЧАЛО ИЗМЕРЕНИЯ ПРОИЗВОДИТЕЛЬНОСТИ")
        performance_logger.info("=" * 60)
        
        # Этап 1: Загрузка данных
        # Используем первый выбранный файл для измерения
        if selected_files:
            first_file = selected_files[0]
            points, _ = perf_measurement.load_data(file_path=first_file)
            
            # Этап 2: Инициализация модели
            perf_measurement.initialize_model()
            
            # Этап 3: Инференс
            inference_results, _ = perf_measurement.run_inference(points)
            
            # Вывод сводки
            perf_measurement.print_summary()

    # Обновляем логику для использования dbh_height
    # Создаем временный класс или обновляем существующий
    class TaxationLogicWithDBHHeight(TreeTaxationLogic):
        def calculate_tree_parameters(self, filename, calculate_dbh=True, calculate_height=True, dbh_height=1.3):
            if filename not in self.opengl_widget.point_clouds or not self.opengl_widget.point_clouds[filename]['full_data'] is not None:
                return None, "Облако точек не найдено или не имеет полных данных."
            
            points = self.opengl_widget.point_clouds[filename]['full_data']
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
    
    # Добавляем информацию о производительности, если измерение было включено
    if measure_performance and perf_measurement:
        perf_text = f"\n\n⏱️ **Производительность:**\n"
        perf_text += f"  Общее время (теор.): {perf_measurement.results.get('load', {}).get('theoretical_time', 0) + perf_measurement.results.get('init', {}).get('theoretical_time', 0) + perf_measurement.results.get('inference', {}).get('theoretical_time', 0):.4f} сек\n"
        perf_text += f"  Общее время (факт.): {perf_measurement.results.get('load', {}).get('actual_time', 0) + perf_measurement.results.get('init', {}).get('actual_time', 0) + perf_measurement.results.get('inference', {}).get('actual_time', 0):.4f} сек\n"
        total_theoretical = sum(r.get('theoretical_time', 0) for r in perf_measurement.results.values())
        total_actual = sum(r.get('actual_time', 0) for r in perf_measurement.results.values())
        total_error = abs(total_actual - total_theoretical) / total_theoretical if total_theoretical > 0 else 0
        perf_text += f"  Относительная ошибка: {total_error * 100:.2f}%\n"
        perf_text += f"  📄 Подробности в файле: taxation_performance.log"
        result_text += perf_text
    
    self.results_label.setText(result_text)