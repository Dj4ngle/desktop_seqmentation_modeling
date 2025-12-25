"""
Модуль для бенчмарка визуализации облаков точек.
Обеспечивает автоматическое выполнение действий и мониторинг производительности.
"""
import time
import psutil
import json
import csv
from datetime import datetime
from collections import deque
from PyQt6.QtCore import QTimer, QObject, pyqtSignal
from PyQt6.QtCore import QPointF
import numpy as np

try:
    import pynvml
    GPU_AVAILABLE = True
    try:
        pynvml.nvmlInit()
    except:
        GPU_AVAILABLE = False
except ImportError:
    GPU_AVAILABLE = False


class PerformanceMonitor(QObject):
    """Класс для мониторинга производительности системы."""
    
    def __init__(self):
        super().__init__()
        # Общие метрики
        self.fps_history = deque(maxlen=1000)
        self.cpu_history = deque(maxlen=1000)
        self.gpu_history = deque(maxlen=1000)
        self.ram_history = deque(maxlen=1000)
        
        # Метрики по этапам (4 этапа по 5 секунд каждый)
        self.stage_metrics = {
            0: {'fps': deque(maxlen=500), 'cpu': deque(maxlen=500), 
                'gpu': deque(maxlen=500), 'ram': deque(maxlen=500)},
            1: {'fps': deque(maxlen=500), 'cpu': deque(maxlen=500), 
                'gpu': deque(maxlen=500), 'ram': deque(maxlen=500)},
            2: {'fps': deque(maxlen=500), 'cpu': deque(maxlen=500), 
                'gpu': deque(maxlen=500), 'ram': deque(maxlen=500)},
            3: {'fps': deque(maxlen=500), 'cpu': deque(maxlen=500), 
                'gpu': deque(maxlen=500), 'ram': deque(maxlen=500)}
        }
        
        self.last_frame_time = time.time()
        self.frame_count = 0
        self.current_stage = 0
        
        # Данные для временной зависимости FPS (запись каждые 0.1 секунды)
        self.fps_timeline = []  # Список кортежей (elapsed_time, fps)
        self.fps_samples_in_interval = []  # FPS значения в текущем интервале 0.1 сек
        self.last_csv_record_time = 0.0  # Время последней записи в CSV
        self.csv_interval = 0.1  # Интервал записи в секундах (0.1 = 100мс)
        self.benchmark_start_time = None  # Время начала бенчмарка
        
        self.process = psutil.Process()
        
        if GPU_AVAILABLE:
            try:
                self.gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            except:
                self.gpu_handle = None
        else:
            self.gpu_handle = None
    
    def record_frame(self, elapsed_time=0.0):
        """Записывает метрики для текущего кадра."""
        current_time = time.time()
        delta_time = current_time - self.last_frame_time
        
        # Определяем текущий этап (0-3) на основе elapsed_time
        # Если elapsed_time == 0, используем последний известный этап
        if elapsed_time > 0:
            stage = int(elapsed_time / 5.0)
            if stage > 3:
                stage = 3
            self.current_stage = stage
        else:
            # Если elapsed_time не передан, используем текущий этап
            stage = self.current_stage
        
        # Записываем FPS только если прошло достаточно времени
        if delta_time > 0:
            fps = 1.0 / delta_time
            self.fps_history.append(fps)
            self.stage_metrics[stage]['fps'].append(fps)
            
            # Запись FPS для временной зависимости (каждые 0.1 секунды)
            if elapsed_time > 0:
                # Добавляем текущий FPS в список для текущего интервала
                self.fps_samples_in_interval.append(fps)
                
                # Проверяем, прошло ли 0.1 секунды с последней записи
                if elapsed_time - self.last_csv_record_time >= self.csv_interval:
                    # Вычисляем средний FPS за интервал
                    if len(self.fps_samples_in_interval) > 0:
                        avg_fps = np.mean(self.fps_samples_in_interval)
                        self.fps_timeline.append((elapsed_time, avg_fps))
                        self.fps_samples_in_interval.clear()
                    
                    # Обновляем время последней записи
                    self.last_csv_record_time = elapsed_time
        
        self.last_frame_time = current_time
        self.frame_count += 1
        
        # CPU usage
        cpu_percent = self.process.cpu_percent(interval=None)
        self.cpu_history.append(cpu_percent)
        self.stage_metrics[stage]['cpu'].append(cpu_percent)
        
        # RAM usage
        ram_info = self.process.memory_info()
        ram_mb = ram_info.rss / (1024 * 1024)  # Convert to MB
        self.ram_history.append(ram_mb)
        self.stage_metrics[stage]['ram'].append(ram_mb)
        
        # GPU usage
        if self.gpu_handle:
            try:
                util = pynvml.nvmlDeviceGetUtilizationRates(self.gpu_handle)
                gpu_usage = util.gpu
                self.gpu_history.append(gpu_usage)
                self.stage_metrics[stage]['gpu'].append(gpu_usage)
            except:
                self.gpu_history.append(0)
                self.stage_metrics[stage]['gpu'].append(0)
        else:
            self.gpu_history.append(0)
            self.stage_metrics[stage]['gpu'].append(0)
    
    def get_statistics(self):
        """Возвращает статистику по всем метрикам, включая статистику по этапам."""
        def calc_stats(history):
            if not history:
                return {'mean': 0, 'min': 0, 'max': 0, 'current': 0}
            return {
                'mean': float(np.mean(history)),
                'min': float(np.min(history)),
                'max': float(np.max(history)),
                'current': float(history[-1]) if history else 0
            }
        
        # Общая статистика
        overall_stats = {
            'fps': calc_stats(self.fps_history),
            'cpu': calc_stats(self.cpu_history),
            'gpu': calc_stats(self.gpu_history),
            'ram': calc_stats(self.ram_history),
            'total_frames': self.frame_count
        }
        
        # Статистика по этапам
        stage_stats = {}
        stage_names = {
            0: 'Этап 1 (0-5 сек): Вращение по Y',
            1: 'Этап 2 (5-10 сек): Вращение + Приближение',
            2: 'Этап 3 (10-15 сек): Вращение + Отдаление + Перемещение',
            3: 'Этап 4 (15-20 сек): Комбинированное вращение + Перемещение'
        }
        
        for stage_id in range(4):
            stage_data = self.stage_metrics[stage_id]
            stage_stats[stage_id] = {
                'name': stage_names[stage_id],
                'fps': calc_stats(stage_data['fps']),
                'cpu': calc_stats(stage_data['cpu']),
                'gpu': calc_stats(stage_data['gpu']),
                'ram': calc_stats(stage_data['ram']),
                'frames': len(stage_data['fps'])
            }
        
        return {
            'overall': overall_stats,
            'stages': stage_stats
        }
    
    def reset(self):
        """Сбрасывает все метрики."""
        self.fps_history.clear()
        self.cpu_history.clear()
        self.gpu_history.clear()
        self.ram_history.clear()
        self.frame_count = 0
        self.current_stage = 0
        self.last_frame_time = time.time()
        
        # Сбрасываем данные временной зависимости FPS
        self.fps_timeline.clear()
        self.fps_samples_in_interval.clear()
        self.last_csv_record_time = 0.0
        self.benchmark_start_time = None
        
        # Сбрасываем метрики по этапам
        for stage_id in range(4):
            self.stage_metrics[stage_id]['fps'].clear()
            self.stage_metrics[stage_id]['cpu'].clear()
            self.stage_metrics[stage_id]['gpu'].clear()
            self.stage_metrics[stage_id]['ram'].clear()
    
    def save_fps_timeline_to_csv(self, filename=None):
        """
        Сохраняет временную зависимость FPS в CSV файл.
        
        Args:
            filename: Путь к файлу. Если None, создается автоматически.
        
        Returns:
            str: Путь к сохраненному файлу
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fps_timeline_{timestamp}.csv"
        
        # Сортируем по времени на случай, если данные не в порядке
        sorted_timeline = sorted(self.fps_timeline, key=lambda x: x[0])
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                # Записываем заголовок
                writer.writerow(['Time (seconds)', 'FPS'])
                
                # Записываем данные
                for elapsed_time, fps in sorted_timeline:
                    writer.writerow([f'{elapsed_time:.3f}', f'{fps:.2f}'])
            
            return filename
        except Exception as e:
            print(f"Ошибка при сохранении CSV файла: {e}")
            return None


class BenchmarkController(QObject):
    """Контроллер для управления бенчмарком."""
    
    benchmark_finished = pyqtSignal(dict)  # Сигнал завершения бенчмарка с результатами
    progress_updated = pyqtSignal(float)  # Сигнал обновления прогресса (0-100)
    
    def __init__(self, opengl_widget, duration=20.0):
        super().__init__()
        self.opengl_widget = opengl_widget
        self.duration = duration  # Длительность бенчмарка в секундах
        self.monitor = PerformanceMonitor()
        # Добавляем ссылку на контроллер в монитор для доступа к elapsed_time
        self.monitor.benchmark_controller = self
        
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_benchmark)
        
        self.start_time = None
        self.elapsed_time = 0.0
        
        # Параметры для действий
        self.rotation_speed = 60.0  # градусов в секунду
        self.zoom_speed = 0.2  # изменение масштаба в секунду
        self.pan_speed = 0.02  # скорость перемещения
        
        # Начальные значения
        self.initial_rotation_x = opengl_widget.rotation_x
        self.initial_rotation_y = opengl_widget.rotation_y
        self.initial_rotation_z = opengl_widget.rotation_z
        self.initial_scale = opengl_widget.scale_factor
        self.initial_position = QPointF(opengl_widget.point_cloud_position)
        
        self.is_running = False
    
    def start(self):
        """Запускает бенчмарк."""
        if self.is_running:
            return
        
        # Сохраняем начальные значения
        self.initial_rotation_x = self.opengl_widget.rotation_x
        self.initial_rotation_y = self.opengl_widget.rotation_y
        self.initial_rotation_z = self.opengl_widget.rotation_z
        self.initial_scale = self.opengl_widget.scale_factor
        self.initial_position = QPointF(self.opengl_widget.point_cloud_position)
        
        # Сбрасываем монитор
        self.monitor.reset()
        
        # Запускаем таймер
        self.start_time = time.time()
        self.elapsed_time = 0.0
        self.is_running = True
        
        # Запускаем таймер с частотой ~60 FPS
        self.timer.start(16)  # ~60 FPS
    
    def stop(self):
        """Останавливает бенчмарк."""
        if not self.is_running:
            return
        
        self.timer.stop()
        self.is_running = False
        
        # Сохраняем оставшиеся данные FPS (если есть)
        if len(self.monitor.fps_samples_in_interval) > 0 and self.elapsed_time > 0:
            avg_fps = np.mean(self.monitor.fps_samples_in_interval)
            self.monitor.fps_timeline.append((self.elapsed_time, avg_fps))
            self.monitor.fps_samples_in_interval.clear()
        
        # Получаем статистику
        stats = self.monitor.get_statistics()
        
        # Добавляем дополнительную информацию
        stats['duration'] = self.elapsed_time
        stats['timestamp'] = datetime.now().isoformat()
        
        # Автоматически сохраняем временную зависимость FPS в CSV
        csv_filename = self.monitor.save_fps_timeline_to_csv()
        if csv_filename:
            stats['fps_timeline_csv'] = csv_filename
        
        # Эмитируем сигнал с результатами
        self.benchmark_finished.emit(stats)
    
    def _update_benchmark(self):
        """Обновляет состояние бенчмарка (вызывается таймером)."""
        if not self.is_running:
            return
        
        current_time = time.time()
        self.elapsed_time = current_time - self.start_time
        
        # НЕ записываем метрики здесь - они записываются в paintGL/paintEvent при реальной отрисовке
        # Здесь только обновляем elapsed_time для определения этапа
        
        # Выполняем действия
        self._perform_actions(self.elapsed_time)
        
        # Обновляем виджет - это вызовет paintGL/paintEvent, где записываются метрики
        self.opengl_widget.update()
        
        # Обновляем прогресс
        progress = (self.elapsed_time / self.duration) * 100.0
        self.progress_updated.emit(min(progress, 100.0))
        
        # Проверяем, не закончилось ли время
        if self.elapsed_time >= self.duration:
            self.stop()
    
    def _perform_actions(self, elapsed_time):
        """Выполняет предопределенные действия на основе прошедшего времени."""
        # Действия выполняются в следующем порядке:
        # 0-5 сек: Вращение по оси Y
        # 5-10 сек: Вращение по оси Y + приближение
        # 10-15 сек: Вращение по оси X + отдаление + перемещение
        # 15-20 сек: Комбинированное вращение + перемещение
        
        t = elapsed_time
        
        # Вращение по оси Y (0-20 сек)
        rotation_y = self.initial_rotation_y + (t * self.rotation_speed) % 360
        
        if t < 5:
            # Только вращение по Y
            self.opengl_widget.rotation_x = self.initial_rotation_x
            self.opengl_widget.rotation_y = rotation_y
            self.opengl_widget.rotation_z = self.initial_rotation_z
            self.opengl_widget.scale_factor = self.initial_scale
            self.opengl_widget.point_cloud_position = QPointF(self.initial_position)
        
        elif t < 10:
            # Вращение по Y + приближение
            zoom_factor = 1.0 + (t - 5) * self.zoom_speed
            self.opengl_widget.rotation_x = self.initial_rotation_x
            self.opengl_widget.rotation_y = rotation_y
            self.opengl_widget.rotation_z = self.initial_rotation_z
            self.opengl_widget.scale_factor = self.initial_scale * zoom_factor
            self.opengl_widget.point_cloud_position = QPointF(self.initial_position)
        
        elif t < 15:
            # Вращение по X + отдаление + перемещение
            rotation_x = self.initial_rotation_x + (t - 10) * self.rotation_speed * 0.5
            zoom_factor = 1.0 + 5 * self.zoom_speed - (t - 10) * self.zoom_speed
            pan_x = (t - 10) * self.pan_speed
            pan_y = (t - 10) * self.pan_speed * 0.5
            
            self.opengl_widget.rotation_x = rotation_x % 360
            self.opengl_widget.rotation_y = rotation_y
            self.opengl_widget.rotation_z = self.initial_rotation_z
            self.opengl_widget.scale_factor = self.initial_scale * zoom_factor
            self.opengl_widget.point_cloud_position = QPointF(
                self.initial_position.x() + pan_x,
                self.initial_position.y() + pan_y
            )
        
        else:
            # Комбинированное вращение + перемещение
            rotation_x = self.initial_rotation_x + (t - 10) * self.rotation_speed * 0.5
            rotation_z = self.initial_rotation_z + (t - 15) * self.rotation_speed * 0.3
            pan_x = 5 * self.pan_speed + (t - 15) * self.pan_speed * 0.5
            pan_y = 5 * self.pan_speed * 0.5 - (t - 15) * self.pan_speed * 0.3
            
            self.opengl_widget.rotation_x = rotation_x % 360
            self.opengl_widget.rotation_y = rotation_y
            self.opengl_widget.rotation_z = rotation_z % 360
            self.opengl_widget.scale_factor = self.initial_scale * (1.0 + 5 * self.zoom_speed - 5 * self.zoom_speed)
            self.opengl_widget.point_cloud_position = QPointF(
                self.initial_position.x() + pan_x,
                self.initial_position.y() + pan_y
            )
        
        # НЕ вызываем update() здесь - он вызывается в _update_benchmark()
        # чтобы избежать двойного вызова paintGL/paintEvent
    
    def save_results(self, filename=None):
        """Сохраняет результаты бенчмарка в JSON файл."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark_results_{timestamp}.json"
        
        stats = self.monitor.get_statistics()
        stats['duration'] = self.elapsed_time
        stats['timestamp'] = datetime.now().isoformat()
        
        # Добавляем информацию о конфигурации бенчмарка
        stats['benchmark_config'] = {
            'duration': self.duration,
            'rotation_speed': self.rotation_speed,
            'zoom_speed': self.zoom_speed,
            'pan_speed': self.pan_speed
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        
        return filename

