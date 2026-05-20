import os

from PyQt6.QtWidgets import (
    QDockWidget,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QLabel,
    QComboBox,
    QLineEdit,
    QCheckBox,
    QProgressBar,
)
from PyQt6.QtCore import Qt, QRegularExpression, QThread, pyqtSignal
from PyQt6.QtGui import QRegularExpressionValidator


def coordinates_dock_widget(self):
    """Создает виджет для обнаружения координат пней."""
    if 'coordinates' not in self.dock_widgets:
        dock = QDockWidget("Обнаружение координат")
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        widget = QWidget()
        layout = QVBoxLayout()

        # Флажки для выбора метода сегментации
        self.checkbox_vot = QCheckBox("Segmentation Voronoi")
        self.checkbox_ram = QCheckBox("Segmentation RAM")
        self.checkbox_clear = QCheckBox("Segmentation Clear")

        layout.addWidget(self.checkbox_vot)
        layout.addWidget(self.checkbox_ram)
        layout.addWidget(self.checkbox_clear)

        # Выпадающий список
        self.intensity_selection = QComboBox()
        self.intensity_selection.addItems(["-1", "0", "1"])  # Добавляем элементы в выпадающий список
        layout.addWidget(QLabel("Порог:"))
        layout.addWidget(self.intensity_selection)

        # Поля ввода для intensity_cut_make
        self.intensity_inputs = []
        self.multiplier_input = QLineEdit()
        self.multiplier_input.setPlaceholderText("Введите множитель (например, 2)")
        self.multiplier_input.setText("1")  # Default value

        regex = QRegularExpression(r"^\d+$")
        validator = QRegularExpressionValidator(regex)
        self.multiplier_input.setValidator(validator)

        layout.addWidget(QLabel("Нужное количество:"))
        layout.addWidget(self.multiplier_input)

        default_values = ["7000", "5000", "1000"]

        for val in default_values:
            input_field = QLineEdit()
            input_field.setPlaceholderText("Введите интенсивность (например, 7000)")
            input_field.setText(val)

            regex = QRegularExpression(r"^\d+$")
            validator = QRegularExpressionValidator(regex)
            input_field.setValidator(validator)

            layout.addWidget(QLabel(f"Интенсивность:"))
            layout.addWidget(input_field)

            self.intensity_inputs.append(input_field)

        layout.addStretch(1)

        # Кнопка запуска/остановки расчётов
        self.coordinates_run_button = QPushButton("Обнаружить координаты")
        self.coordinates_run_button.setObjectName("coordinatesRunButton")
        self.coordinates_run_button.setProperty("role", "run")
        self.coordinates_run_button.clicked.connect(lambda: run_coordinates(self))
        layout.addWidget(self.coordinates_run_button)

        self.coordinates_progress_label = QLabel("Готово")
        self.coordinates_progress_label.setObjectName("coordinatesProgressLabel")
        self.coordinates_progress_label.setWordWrap(True)
        self.coordinates_progress_bar = QProgressBar()
        self.coordinates_progress_bar.setObjectName("coordinatesProgressBar")
        self.coordinates_progress_bar.setRange(0, 100)
        self.coordinates_progress_bar.setValue(0)
        self.coordinates_progress_bar.setTextVisible(True)
        self.coordinates_progress_bar.setFormat("%p%")
        layout.addWidget(self.coordinates_progress_label)
        layout.addWidget(self.coordinates_progress_bar)

        widget.setLayout(layout)
        dock.setWidget(widget)
        self.dock_widgets['coordinates'] = dock
    return self.dock_widgets['coordinates']


def set_coordinates_progress(self, value, message=None):
    value = max(0, min(100, int(value)))
    progress_bar = getattr(self, "coordinates_progress_bar", None)
    progress_label = getattr(self, "coordinates_progress_label", None)

    if progress_bar is not None:
        progress_bar.setValue(value)
    if progress_label is not None and message:
        progress_label.setText(message)


def reset_coordinates_progress(self, message="Готово"):
    set_coordinates_progress(self, 0, message)


def _refresh_widget_style(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def set_coordinates_running_state(self, running, stopping=False):
    run_button = getattr(self, "coordinates_run_button", None)
    if run_button is None:
        return

    if stopping:
        run_button.setText("Останавливаем...")
        run_button.setEnabled(False)
        run_button.setProperty("role", "stop")
    elif running:
        run_button.setText("Остановить расчёты")
        run_button.setEnabled(True)
        run_button.setProperty("role", "stop")
    else:
        run_button.setText("Обнаружить координаты")
        run_button.setEnabled(True)
        run_button.setProperty("role", "run")

    _refresh_widget_style(run_button)


class CoordinatesWorker(QThread):
    """Класс для выполнения расчётов координат в фоновом потоке"""
    finished = pyqtSignal()
    error = pyqtSignal(str)
    file_loaded = pyqtSignal(str)  # Сигнал для загрузки файла в UI
    progress = pyqtSignal(int, str)
    cancelled = pyqtSignal()
    
    def __init__(self, selected_files, intensity_values, multiplier, tr_val, 
                 use_vot, use_ram, use_clear):
        super().__init__()
        self.selected_files = selected_files
        self.intensity_values = intensity_values
        self.multiplier = multiplier
        self.tr_val = tr_val
        self.use_vot = use_vot
        self.use_ram = use_ram
        self.use_clear = use_clear
        self._stop_requested = False

    def request_stop(self):
        self._stop_requested = True
        self.requestInterruption()

    def stop_requested(self):
        return self._stop_requested or self.isInterruptionRequested()

    def _build_stage_plan(self):
        stages_per_file = ["Подготовка"]
        stages_per_file.extend([f"Порог {value}" for value in self.intensity_values])
        stages_per_file.extend(["Объединение координат", "Классификация кандидатов"])
        stages_per_file.extend(
            self._segmentation_stage_label(stage)
            for stage in self._selected_segmentation_stages()
        )
        stages_per_file.append("Загрузка результатов")
        return stages_per_file

    def _selected_segmentation_stages(self):
        stages = []
        if self.use_vot or self.use_ram or self.use_clear:
            stages.append("voronoi")
        if self.use_ram or self.use_clear:
            stages.append("ram")
        if self.use_clear:
            stages.append("clear")
        return stages

    def _segmentation_stage_label(self, stage):
        return {
            "voronoi": "Сегментация Voronoi",
            "ram": "Сегментация RAM",
            "clear": "Финальная очистка",
        }[stage]

    def _set_progress(self, completed_steps, total_steps, message):
        percent = 0 if total_steps == 0 else int(round(completed_steps / total_steps * 100))
        self.progress.emit(percent, message)

    def _finish_stage(self, completed_steps, total_steps, message):
        completed_steps += 1
        self._set_progress(completed_steps, total_steps, message)
        return completed_steps

    def _stop_if_requested(self, completed_steps, total_steps):
        if not self.stop_requested():
            return False

        self._set_progress(
            completed_steps,
            total_steps,
            "Расчёты координат остановлены пользователем"
        )
        print("Расчёты координат остановлены пользователем.")
        self.cancelled.emit()
        self.finished.emit()
        return True
    
    def run(self):
        """Выполнение расчётов в фоновом потоке"""
        try:
            from desktop_segmentation_modeling.Coordinates import (
                clear_excess_stumps,
                coord_settings,
                merge_coordinates,
                coordinates,
            )
            from desktop_segmentation_modeling.Segmentation import (
                segmentation_clear,
                segmentation_ram,
                segmentation_vor,
                seg_settings,
            )

            # Определяем путь к tmp директории один раз для всех файлов
            # Используем текущую рабочую директорию для совместимости с библиотекой
            # Это гарантирует работу как при разработке, так и при использовании как библиотеки
            # tmp будет создаваться в текущей рабочей директории пользователя
            tmp_dir = os.path.join(os.getcwd(), "tmp")
            os.makedirs(tmp_dir, exist_ok=True)

            stage_plan = self._build_stage_plan()
            total_steps = len(stage_plan) * len(self.selected_files)
            completed_steps = 0
            self._set_progress(0, total_steps, "Расчёты координат запущены")
            
            for file_path in self.selected_files:
                if self._stop_if_requested(completed_steps, total_steps):
                    return

                if not self.intensity_values:
                    print("Ошибка: Не указана интенсивность обрезки точек.")
                    self.finished.emit()
                    return

                file_name = os.path.basename(file_path)
                self._set_progress(completed_steps, total_steps, f"Подготовка файла {file_name}")
                
                # Загружаем настройки CS
                cs = coord_settings.CS()
                cs.fname_points = file_path
                cs.path_base = tmp_dir
                open(os.path.join(tmp_dir, "coordinates_paths.txt"), "w", encoding="utf-8").close()
                completed_steps = self._finish_stage(
                    completed_steps,
                    total_steps,
                    f"Подготовка файла {file_name} завершена"
                )
                
                print(f"Обнаружение координат: {file_name}")
                for intensity_cut_make in self.intensity_values:
                    if self._stop_if_requested(completed_steps, total_steps):
                        return

                    self._set_progress(
                        completed_steps,
                        total_steps,
                        f"Поиск кандидатов: intensity >= {intensity_cut_make}"
                    )
                    print(f"Порог intensity >= {intensity_cut_make}")
                    coordinates.coordinates(intensity_cut_make, cs, should_stop=self.stop_requested)
                    if self._stop_if_requested(completed_steps, total_steps):
                        return

                    completed_steps = self._finish_stage(
                        completed_steps,
                        total_steps,
                        f"Порог intensity >= {intensity_cut_make} обработан"
                    )
                
                # мерджим координаты
                if self._stop_if_requested(completed_steps, total_steps):
                    return

                self._set_progress(completed_steps, total_steps, "Объединение координат по порогам")
                print("Объединение координат по разным порогам...")
                merge_coordinates.merge_coordinates(cs)
                if self._stop_if_requested(completed_steps, total_steps):
                    return

                completed_steps = self._finish_stage(
                    completed_steps,
                    total_steps,
                    "Объединение координат завершено"
                )

                if self._stop_if_requested(completed_steps, total_steps):
                    return

                self._set_progress(completed_steps, total_steps, "Классификация кандидатов PointNet")
                print("Классификация кандидатов через PointNet...")
                csv_output_file = clear_excess_stumps.clear_excess_stumps(cs, should_stop=self.stop_requested)
                if self._stop_if_requested(completed_steps, total_steps):
                    return

                completed_steps = self._finish_stage(
                    completed_steps,
                    total_steps,
                    "Классификация кандидатов завершена"
                )
                
                # Загружаем настройки SS
                ss = seg_settings.SS()
                ss.fname_points = file_path
                ss.path_base = tmp_dir
                ss.csv_name_coord = csv_output_file
                
                segmented_files = []
                
                # Вызываем только выбранные методы. RAM и очистка зависят от Voronoi.
                for stage in self._selected_segmentation_stages():
                    if self._stop_if_requested(completed_steps, total_steps):
                        return

                    if stage == "voronoi":
                        self._set_progress(completed_steps, total_steps, "Сегментация Voronoi")
                        segmented_files_vot = segmentation_vor.segmentation_vor(
                            ss,
                            self.tr_val,
                            self.multiplier,
                            make_binding=True,
                            should_stop=self.stop_requested,
                        )
                        if self._stop_if_requested(completed_steps, total_steps):
                            return

                        segmented_files.extend(segmented_files_vot)
                        completed_steps = self._finish_stage(
                            completed_steps,
                            total_steps,
                            "Сегментация Voronoi завершена",
                        )
                    elif stage == "ram":
                        self._set_progress(completed_steps, total_steps, "Сегментация RAM")
                        segmented_files_ram = segmentation_ram.segmentation_ram(
                            ss,
                            self.tr_val,
                            self.multiplier,
                            should_stop=self.stop_requested,
                        )
                        if self._stop_if_requested(completed_steps, total_steps):
                            return

                        segmented_files.extend(segmented_files_ram)
                        completed_steps = self._finish_stage(
                            completed_steps,
                            total_steps,
                            "Сегментация RAM завершена",
                        )
                    elif stage == "clear":
                        self._set_progress(completed_steps, total_steps, "Финальная очистка сегментов")
                        segmented_files_clear = segmentation_clear.segmentation_clear(
                            ss,
                            self.tr_val,
                            self.multiplier,
                            should_stop=self.stop_requested,
                        )
                        if self._stop_if_requested(completed_steps, total_steps):
                            return

                        segmented_files.extend(segmented_files_clear)
                        completed_steps = self._finish_stage(
                            completed_steps,
                            total_steps,
                            "Финальная очистка завершена",
                        )
                
                # Отправляем сигналы для загрузки всех сегментированных файлов
                self._set_progress(completed_steps, total_steps, "Передача результатов в интерфейс")
                for file in segmented_files:
                    if self._stop_if_requested(completed_steps, total_steps):
                        return

                    self.file_loaded.emit(file)
                completed_steps = self._finish_stage(
                    completed_steps,
                    total_steps,
                    f"Результаты файла {file_name} переданы в интерфейс"
                )
            
            self.progress.emit(100, "Расчёты координат завершены")
            print("Обнаружение координат завершено.")
            self.finished.emit()
            
        except Exception as e:
            error_msg = f"Ошибка при выполнении расчётов: {str(e)}"
            print(error_msg)
            self.error.emit(error_msg)
            self.finished.emit()


def run_coordinates(self):
    """Запускает процесс обнаружения координат деревьев в фоновом потоке."""
    # Проверяем, не запущен ли уже процесс
    if getattr(self, '_coordinates_worker', None) and self._coordinates_worker.isRunning():
        if self._coordinates_worker.stop_requested():
            print("Остановка расчётов координат уже выполняется.")
            return

        self._coordinates_worker.request_stop()
        set_coordinates_running_state(self, True, stopping=True)
        progress_bar = getattr(self, "coordinates_progress_bar", None)
        progress_value = progress_bar.value() if progress_bar is not None else 0
        set_coordinates_progress(
            self,
            progress_value,
            "Остановка будет выполнена в ближайшем безопасном месте расчёта"
        )
        print("Остановка расчётов координат запрошена...")
        return
    
    selected_files = []
    for index in range(self.listWidget.count()):
        item = self.listWidget.item(index)
        checkbox = self.listWidget.itemWidget(item)
        if checkbox.isChecked():
            selected_files.append(checkbox.property("filePath"))
    if not selected_files:
        print("Ошибка: Не выбрано облако точек для обнаружения координат.")
        return

    # Получаем значения из виджетов в главном потоке (до запуска worker)
    if not self.multiplier_input.text():
        print("Ошибка: поле нужного количества не заполнено.")
        return

    multiplier = int(self.multiplier_input.text())
    tr_val = int(self.intensity_selection.currentText())
    intensity_values = []
    for input_field in self.intensity_inputs:
        if not input_field.text():
            print("Ошибка: одно из полей интенсивности не заполнено.")
            return
        intensity_values.append(int(input_field.text()))

    if multiplier < 1 or multiplier > len(intensity_values):
        print("Ошибка: нужное количество должно быть от 1 до числа заданных интенсивностей.")
        return
    
    use_vot = self.checkbox_vot.isChecked()
    use_ram = self.checkbox_ram.isChecked()
    use_clear = self.checkbox_clear.isChecked()

    # Создаём и запускаем worker в отдельном потоке
    self._coordinates_worker = CoordinatesWorker(
        selected_files,
        intensity_values,
        multiplier,
        tr_val,
        use_vot,
        use_ram,
        use_clear
    )
    self._coordinates_failed = False
    self._coordinates_cancelled = False
    
    # Подключаем сигналы для обновления UI
    # file_loaded - загружает файл в UI (выполняется в главном потоке через сигнал)
    def on_file_loaded(file_path):
        self.add_file_to_list_widget(file_path)
        if file_path.lower().endswith(('.las', '.pcd')):
            self.load_point_cloud_async(file_path)
    
    # finished - обработчик завершения расчётов
    def on_finished():
        worker = getattr(self, '_coordinates_worker', None)
        if worker is None:
            return

        if not getattr(self, "_coordinates_failed", False) and not getattr(self, "_coordinates_cancelled", False):
            print("Расчёты координат завершены.")
        set_coordinates_running_state(self, False)
        self._coordinates_worker = None
        worker.deleteLater()
    
    # error - обработчик ошибок
    def on_error(error_msg):
        self._coordinates_failed = True
        print(f"Ошибка: {error_msg}")
        progress_bar = getattr(self, "coordinates_progress_bar", None)
        progress_value = progress_bar.value() if progress_bar is not None else 0
        set_coordinates_progress(self, progress_value, error_msg)

    def on_cancelled():
        self._coordinates_cancelled = True
        progress_bar = getattr(self, "coordinates_progress_bar", None)
        progress_value = progress_bar.value() if progress_bar is not None else 0
        set_coordinates_progress(self, progress_value, "Расчёты остановлены пользователем")

    def on_progress(value, message):
        set_coordinates_progress(self, value, message)

    self._coordinates_worker.file_loaded.connect(on_file_loaded)
    self._coordinates_worker.finished.connect(on_finished)
    self._coordinates_worker.error.connect(on_error)
    self._coordinates_worker.cancelled.connect(on_cancelled)
    self._coordinates_worker.progress.connect(on_progress)

    # Запускаем поток
    reset_coordinates_progress(self, "Расчёты координат запущены")
    set_coordinates_running_state(self, True)
    print("Запуск расчётов координат...")
    self._coordinates_worker.start()
