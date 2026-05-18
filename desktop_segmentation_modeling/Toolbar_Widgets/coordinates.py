import os

from PyQt6.QtWidgets import (QDockWidget, QVBoxLayout, QWidget, QPushButton, QLabel, QComboBox, QLineEdit, QCheckBox)
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

        # Кнопка запуска
        run_button = QPushButton("Обнаружить координаты")
        run_button.clicked.connect(lambda: run_coordinates(self))
        layout.addWidget(run_button)

        widget.setLayout(layout)
        dock.setWidget(widget)
        self.dock_widgets['coordinates'] = dock
    return self.dock_widgets['coordinates']


class CoordinatesWorker(QThread):
    """Класс для выполнения расчётов координат в фоновом потоке"""
    finished = pyqtSignal()
    error = pyqtSignal(str)
    file_loaded = pyqtSignal(str)  # Сигнал для загрузки файла в UI
    
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
            
            for file_path in self.selected_files:
                if not self.intensity_values:
                    print("Ошибка: Не указана интенсивность обрезки точек.")
                    return
                
                # Загружаем настройки CS
                cs = coord_settings.CS()
                cs.fname_points = file_path
                cs.path_base = tmp_dir
                
                for intensity_cut_make in self.intensity_values:
                    print(f"Запуск обнаружения координат с интенсивностью {intensity_cut_make} для {file_path}")
                    coordinates.coordinates(intensity_cut_make, cs)
                
                # мерджим координаты
                merge_coordinates.merge_coordinates(cs)
                csv_output_file = clear_excess_stumps.clear_excess_stumps(cs)
                
                # Отправляем сигнал для загрузки файла в UI (выполнится в главном потоке)
                self.file_loaded.emit(csv_output_file)
                
                # Загружаем настройки SS
                ss = seg_settings.SS()
                ss.fname_points = file_path
                ss.path_base = tmp_dir
                ss.csv_name_coord = csv_output_file
                
                segmented_files = []
                
                # Вызываем только выбранные методы
                if self.use_clear:
                    segmented_files_vot = segmentation_vor.segmentation_vor(ss, self.tr_val, self.multiplier, make_binding=True)
                    segmented_files.extend(segmented_files_vot)
                    segmented_files_ram = segmentation_ram.segmentation_ram(ss, self.tr_val, self.multiplier)
                    segmented_files.extend(segmented_files_ram)
                    segmented_files_clear = segmentation_clear.segmentation_clear(ss, self.tr_val, self.multiplier)
                    segmented_files.extend(segmented_files_clear)
                elif self.use_ram:
                    segmented_files_vot = segmentation_vor.segmentation_vor(ss, self.tr_val, self.multiplier, make_binding=True)
                    segmented_files.extend(segmented_files_vot)
                    segmented_files_ram = segmentation_ram.segmentation_ram(ss, self.tr_val, self.multiplier)
                    segmented_files.extend(segmented_files_ram)
                elif self.use_vot:
                    segmented_files_vot = segmentation_vor.segmentation_vor(ss, self.tr_val, self.multiplier, make_binding=True)
                    segmented_files.extend(segmented_files_vot)
                
                # Отправляем сигналы для загрузки всех сегментированных файлов
                for file in segmented_files:
                    self.file_loaded.emit(file)
            
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
        print("Расчёты уже выполняются. Пожалуйста, дождитесь завершения.")
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
    multiplier = int(self.multiplier_input.text())
    tr_val = int(self.intensity_selection.currentText())
    intensity_values = []
    for input_field in self.intensity_inputs:
        if not input_field.text():
            print("Ошибка: одно из полей интенсивности не заполнено.")
            return
        intensity_values.append(int(input_field.text()))
    
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
    
    # Подключаем сигналы для обновления UI
    # file_loaded - загружает файл в UI (выполняется в главном потоке через сигнал)
    def on_file_loaded(file_path):
        self.openGLWidget.load_point_cloud(file_path)
        self.add_file_to_list_widget(file_path)
    
    # finished - обработчик завершения расчётов
    def on_finished():
        print("Расчёты координат завершены.")
        if hasattr(self, '_coordinates_worker'):
            worker = self._coordinates_worker
            self._coordinates_worker = None
            worker.deleteLater()
    
    # error - обработчик ошибок
    def on_error(error_msg):
        print(f"Ошибка: {error_msg}")
    
    self._coordinates_worker.file_loaded.connect(on_file_loaded)
    self._coordinates_worker.finished.connect(on_finished)
    self._coordinates_worker.error.connect(on_error)
    
    # Запускаем поток
    print("Запуск расчётов координат...")
    self._coordinates_worker.start()
