"""
Виджет для бенчмарка визуализации облаков точек.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QProgressBar, QTextEdit, QGroupBox, QFileDialog, QDockWidget
)
from PyQt6.QtCore import Qt
from ..benchmark import BenchmarkController
import os


def benchmark_dock_widget(self):
    """Создает виджет для бенчмарка визуализации облаков точек."""
    dock = QDockWidget("Бенчмарк")
    dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
    widget = BenchmarkWidget(self.openGLWidget, self)
    dock.setWidget(widget)
    return dock


class BenchmarkWidget(QWidget):
    """Виджет для управления и отображения результатов бенчмарка."""
    
    def __init__(self, opengl_widget, parent=None):
        super().__init__(parent)
        self.opengl_widget = opengl_widget
        self.benchmark_controller = BenchmarkController(opengl_widget, duration=20.0)
        
        # Устанавливаем ссылку на монитор производительности в OpenGL виджете
        self.opengl_widget.performance_monitor = self.benchmark_controller.monitor
        
        # Подключаем сигналы
        self.benchmark_controller.benchmark_finished.connect(self.on_benchmark_finished)
        self.benchmark_controller.progress_updated.connect(self.update_progress)
        
        self.init_ui()
    
    def init_ui(self):
        """Инициализирует пользовательский интерфейс."""
        layout = QVBoxLayout()
        
        # Группа управления
        control_group = QGroupBox("Управление бенчмарком")
        control_layout = QVBoxLayout()
        
        # Кнопка запуска
        self.start_button = QPushButton("Запустить бенчмарк")
        self.start_button.clicked.connect(self.start_benchmark)
        control_layout.addWidget(self.start_button)
        
        # Кнопка остановки
        self.stop_button = QPushButton("Остановить бенчмарк")
        self.stop_button.clicked.connect(self.stop_benchmark)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button)
        
        # Прогресс бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        control_layout.addWidget(QLabel("Прогресс:"))
        control_layout.addWidget(self.progress_bar)
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # Группа результатов
        results_group = QGroupBox("Результаты")
        results_layout = QVBoxLayout()
        
        # Текстовое поле для результатов
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(300)
        results_layout.addWidget(self.results_text)
        
        # Кнопка сохранения результатов
        self.save_button = QPushButton("Сохранить результаты")
        self.save_button.clicked.connect(self.save_results)
        self.save_button.setEnabled(False)
        results_layout.addWidget(self.save_button)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        # Группа информации
        info_group = QGroupBox("Информация")
        info_layout = QVBoxLayout()
        
        info_text = QLabel(
            "Бенчмарк выполняет следующие действия:\n"
            "• 0-5 сек: Вращение по оси Y\n"
            "• 5-10 сек: Вращение по оси Y + приближение\n"
            "• 10-15 сек: Вращение по оси X + отдаление + перемещение\n"
            "• 15-20 сек: Комбинированное вращение + перемещение\n\n"
            "Длительность: 20 секунд"
        )
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def start_benchmark(self):
        """Запускает бенчмарк."""
        if not self.opengl_widget.point_clouds and not self.opengl_widget.models:
            self.results_text.setText("Ошибка: Нет загруженных облаков точек или моделей для бенчмарка.")
            return
        
        # Проверяем, есть ли активные облака точек или модели
        has_active = False
        for cloud_info in self.opengl_widget.point_clouds.values():
            if cloud_info.get('active', False):
                has_active = True
                break
        if not has_active:
            for model_info in self.opengl_widget.models.values():
                if model_info.get('active', False):
                    has_active = True
                    break
        
        if not has_active:
            self.results_text.setText("Ошибка: Нет активных облаков точек или моделей для бенчмарка.")
            return
        
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.results_text.clear()
        self.results_text.append("Бенчмарк запущен...")
        
        self.benchmark_controller.start()
    
    def stop_benchmark(self):
        """Останавливает бенчмарк."""
        self.benchmark_controller.stop()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
    
    def update_progress(self, value):
        """Обновляет прогресс бар."""
        self.progress_bar.setValue(int(value))
    
    def on_benchmark_finished(self, results):
        """Обрабатывает завершение бенчмарка."""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setValue(100)
        
        # Форматируем результаты
        text = "═══════════════════════════════════════════════════\n"
        text += "           БЕНЧМАРК ЗАВЕРШЕН\n"
        text += "═══════════════════════════════════════════════════\n\n"
        
        overall = results.get('overall', {})
        stages = results.get('stages', {})
        
        text += f"Длительность: {results.get('duration', 0):.2f} сек\n"
        text += f"Всего кадров: {overall.get('total_frames', 0)}\n\n"
        
        # Общая статистика
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "ОБЩАЯ СТАТИСТИКА\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        fps = overall.get('fps', {})
        cpu = overall.get('cpu', {})
        gpu = overall.get('gpu', {})
        ram = overall.get('ram', {})
        
        text += "FPS:\n"
        text += f"  Среднее: {fps.get('mean', 0):.2f}\n"
        text += f"  Минимум: {fps.get('min', 0):.2f}\n"
        text += f"  Максимум: {fps.get('max', 0):.2f}\n"
        text += f"  Текущее: {fps.get('current', 0):.2f}\n\n"
        
        text += "CPU Usage (%):\n"
        text += f"  Среднее: {cpu.get('mean', 0):.2f}\n"
        text += f"  Минимум: {cpu.get('min', 0):.2f}\n"
        text += f"  Максимум: {cpu.get('max', 0):.2f}\n"
        text += f"  Текущее: {cpu.get('current', 0):.2f}\n\n"
        
        text += "GPU Usage (%):\n"
        text += f"  Среднее: {gpu.get('mean', 0):.2f}\n"
        text += f"  Минимум: {gpu.get('min', 0):.2f}\n"
        text += f"  Максимум: {gpu.get('max', 0):.2f}\n"
        text += f"  Текущее: {gpu.get('current', 0):.2f}\n\n"
        
        text += "RAM Usage (MB):\n"
        text += f"  Среднее: {ram.get('mean', 0):.2f}\n"
        text += f"  Минимум: {ram.get('min', 0):.2f}\n"
        text += f"  Максимум: {ram.get('max', 0):.2f}\n"
        text += f"  Текущее: {ram.get('current', 0):.2f}\n\n"
        
        # Статистика по этапам
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "СТАТИСТИКА ПО ЭТАПАМ\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for stage_id in range(4):
            if stage_id in stages:
                stage = stages[stage_id]
                text += f"{stage.get('name', f'Этап {stage_id + 1}')}\n"
                text += f"  Кадров: {stage.get('frames', 0)}\n"
                
                stage_fps = stage.get('fps', {})
                stage_cpu = stage.get('cpu', {})
                stage_gpu = stage.get('gpu', {})
                stage_ram = stage.get('ram', {})
                
                text += f"  FPS: среднее={stage_fps.get('mean', 0):.2f}, "
                text += f"мин={stage_fps.get('min', 0):.2f}, "
                text += f"макс={stage_fps.get('max', 0):.2f}\n"
                
                text += f"  CPU: среднее={stage_cpu.get('mean', 0):.2f}%, "
                text += f"макс={stage_cpu.get('max', 0):.2f}%\n"
                
                text += f"  GPU: среднее={stage_gpu.get('mean', 0):.2f}%, "
                text += f"макс={stage_gpu.get('max', 0):.2f}%\n"
                
                text += f"  RAM: среднее={stage_ram.get('mean', 0):.2f} MB, "
                text += f"макс={stage_ram.get('max', 0):.2f} MB\n\n"
        
        text += f"Время выполнения: {results.get('timestamp', 'N/A')}\n"
        
        self.results_text.setText(text)
        self.save_button.setEnabled(True)
        
        # Сохраняем результаты в атрибут для последующего сохранения
        self.last_results = results
    
    def save_results(self):
        """Сохраняет результаты бенчмарка в файл."""
        if not hasattr(self, 'last_results'):
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить результаты бенчмарка",
            f"benchmark_results_{self.last_results['timestamp'].replace(':', '-').split('.')[0]}.json",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if filename:
            saved_file = self.benchmark_controller.save_results(filename)
            self.results_text.append(f"\nРезультаты сохранены в: {saved_file}")

