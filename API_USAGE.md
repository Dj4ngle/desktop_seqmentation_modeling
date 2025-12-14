# Использование API desktop_segmentation_modeling

## Установка

```bash
pip install desktop-segmentation-modeling
```

## Публичные методы

### 1. `run_app()`

Запускает PyQt приложение для работы с облаками точек.

**Параметры:** Нет

**Возвращает:** None (блокирует выполнение до закрытия приложения)

**Пример:**
```python
import desktop_segmentation_modeling

# Запуск приложения
desktop_segmentation_modeling.run_app()
```

**Описание:**
- Загружает и применяет стили из `style.qss`
- Создает главное окно приложения
- Поддерживает загрузку облаков точек (.las, .pcd)
- Визуализация 3D облаков точек
- Интегрированные инструменты для сегментации и таксации

---

### 2. `run_segmentation()`

Выполняет сегментацию облака точек с помощью алгоритма DBSCAN.

**Параметры:**
- `point_cloud_path` (str, обязательный): Путь к файлу облака точек
  - Поддерживаемые форматы: `.las`, `.pcd`
- `eps` (float, опциональный): Максимальное расстояние между точками в одном кластере
  - По умолчанию: `0.78`
- `min_samples` (int, опциональный): Минимальное количество точек для формирования кластера
  - По умолчанию: `132`
- `output_dir` (str, опциональный): Директория для сохранения результатов
  - По умолчанию: директория исходного файла

**Возвращает:**
```python
{
    'segments': [список путей к файлам сегментированных облаков точек],
    'num_segments': количество найденных сегментов (int),
    'labels': массив меток кластеров для каждой точки (numpy.ndarray)
}
```

**Пример:**
```python
import desktop_segmentation_modeling

# Сегментация с параметрами по умолчанию
results = desktop_segmentation_modeling.run_segmentation(
    point_cloud_path='data/pointcloud.las'
)

print(f"Найдено сегментов: {results['num_segments']}")
for segment_file in results['segments']:
    print(f"Сегмент: {segment_file}")

# Сегментация с кастомными параметрами
results = desktop_segmentation_modeling.run_segmentation(
    point_cloud_path='data/pointcloud.pcd',
    eps=1.0,
    min_samples=100,
    output_dir='output/segments'
)
```

**Исключения:**
- `FileNotFoundError`: Если файл облака точек не найден
- `ValueError`: Если параметры некорректны (eps <= 0, min_samples < 1)
- `ImportError`: Если для .las файлов отсутствует библиотека pylas

---

### 3. `run_taxation()`

Выполняет таксацию дерева (расчет параметров) из облака точек.

**Параметры:**
- `point_cloud_path` (str, обязательный): Путь к файлу облака точек дерева
  - Поддерживаемые форматы: `.las`, `.pcd`
- `calculate_dbh` (bool, опциональный): Рассчитывать ли диаметр на высоте груди (DBH)
  - По умолчанию: `True`
- `calculate_height` (bool, опциональный): Рассчитывать ли высоту дерева
  - По умолчанию: `True`
- `dbh_height` (float, опциональный): Высота для расчета DBH в метрах
  - По умолчанию: `1.3` (стандартная высота груди)

**Возвращает:**
```python
{
    'DBH': диаметр на высоте груди в метрах (float или str с ошибкой),
    'Height': высота дерева в метрах (float),
    'points_count': количество точек в облаке (int)
}
```

**Пример:**
```python
import desktop_segmentation_modeling

# Таксация с параметрами по умолчанию
results = desktop_segmentation_modeling.run_taxation(
    point_cloud_path='data/tree.las'
)

print(f"Высота дерева: {results['Height']:.2f} м")
if isinstance(results['DBH'], float):
    print(f"DBH: {results['DBH']:.2f} м")
else:
    print(f"DBH: {results['DBH']}")

# Таксация только высоты
results = desktop_segmentation_modeling.run_taxation(
    point_cloud_path='data/tree.pcd',
    calculate_dbh=False,
    calculate_height=True
)

# Таксация с кастомной высотой DBH
results = desktop_segmentation_modeling.run_taxation(
    point_cloud_path='data/tree.csv',
    dbh_height=1.5  # 1.5 метра вместо стандартных 1.3
)
```

**Исключения:**
- `FileNotFoundError`: Если файл облака точек не найден
- `ValueError`: Если параметры некорректны (dbh_height <= 0) или файл пустой
- `ImportError`: Если для .las файлов отсутствует библиотека pylas

---

### 4. `run_coordinates()`

Выполняет обнаружение координат деревьев (пней) из облака точек.

**Параметры:**
- `point_cloud_path` (str, обязательный): Путь к файлу облака точек
  - Поддерживаемые форматы: `.las`, `.pcd`
- `intensity_values` (list, опциональный): Список значений интенсивности для фильтрации точек
  - По умолчанию: `[7000, 5000, 1000]`
  - Каждое значение используется для отдельного прохода обработки
- `output_dir` (str, опциональный): Директория для сохранения результатов
  - По умолчанию: `tmp/` в текущей рабочей директории
- `shape_file` (str, опциональный): Путь к файлу границ участка (.shp)
  - Если не указан, границы определяются автоматически по всему облаку точек
- `trajectory_file` (str, опциональный): Путь к файлу траектории (.las)
  - Требуется только для метода `cut_data_method='flood_fill'`
- `cut_data_method` (str, опциональный): Метод разбиения на ячейки
  - `"voronoi_tessellation"` (по умолчанию) - диаграмма Вороного
  - `"flood_fill"` - заливка по траектории (требует trajectory_file)
  - `"none"` - без разбиения на ячейки
- `height_min` (float, опциональный): Минимальная высота для фильтрации точек в метрах
  - По умолчанию: `0.0`
- `height_max` (float, опциональный): Максимальная высота для фильтрации точек в метрах
  - По умолчанию: `3.0`
- `intensity_cut` (int, опциональный): Минимальное значение интенсивности для фильтрации
  - По умолчанию: `0`

**Возвращает:**
- `str`: Путь к CSV файлу с координатами деревьев

**Пример:**
```python
import desktop_segmentation_modeling

# Обнаружение координат с параметрами по умолчанию
csv_file = desktop_segmentation_modeling.run_coordinates(
    point_cloud_path='data/forest.las'
)
print(f"Координаты сохранены в: {csv_file}")

# Обнаружение координат с кастомными параметрами
csv_file = desktop_segmentation_modeling.run_coordinates(
    point_cloud_path='data/forest.las',
    intensity_values=[8000, 6000, 2000],
    output_dir='output/coordinates',
    shape_file='data/borders.shp',
    cut_data_method='voronoi_tessellation',
    height_min=0.0,
    height_max=5.0
)

# Обнаружение координат с методом flood_fill
csv_file = desktop_segmentation_modeling.run_coordinates(
    point_cloud_path='data/forest.las',
    intensity_values=[7000, 5000],
    trajectory_file='data/trajectory.las',
    cut_data_method='flood_fill'
)
```

**Исключения:**
- `FileNotFoundError`: Если файл облака точек не найден
- `ValueError`: Если параметры некорректны (неверный метод, height_min >= height_max и т.д.)

**Описание процесса:**
1. Фильтрация облака точек по высоте и интенсивности
2. Разбиение на ячейки выбранным методом
3. Извлечение пней из каждой ячейки
4. Классификация пней с помощью модели машинного обучения
5. Объединение координат из всех проходов
6. Очистка лишних пней (не деревьев)
7. Сохранение результата в CSV файл

**Формат выходного CSV файла:**
- Колонки: `Name_stump_int<значение>`, `X`, `Y`, `Diameter_int<значение>`, `Labels_int<значение>`
- Разделитель: `;` (точка с запятой)
- Координаты в метрах

---

## Полный пример использования

```python
import desktop_segmentation_modeling

# 1. Запуск приложения
# desktop_segmentation_modeling.run_app()

# 2. Обнаружение координат деревьев
coordinates_file = desktop_segmentation_modeling.run_coordinates(
    point_cloud_path='data/forest.las',
    intensity_values=[7000, 5000, 1000],
    output_dir='output/coordinates'
)
print(f"Координаты сохранены в: {coordinates_file}")

# 3. Сегментация облака точек
segmentation_results = desktop_segmentation_modeling.run_segmentation(
    point_cloud_path='data/forest.las',
    eps=0.78,
    min_samples=132
)

print(f"Сегментация завершена. Найдено {segmentation_results['num_segments']} сегментов")

# 4. Таксация каждого сегмента
for segment_file in segmentation_results['segments']:
    print(f"\nТаксация для {segment_file}:")
    taxation_results = desktop_segmentation_modeling.run_taxation(
        point_cloud_path=segment_file,
        calculate_dbh=True,
        calculate_height=True
    )
    print(f"  Высота: {taxation_results['Height']:.2f} м")
    if isinstance(taxation_results['DBH'], float):
        print(f"  DBH: {taxation_results['DBH']:.2f} м")
```

---

## Требования к форматам файлов

### CSV файлы
Должны содержать колонки с координатами:
- `x`, `y`, `z` (строчные) или
- `X`, `Y`, `Z` (заглавные)
- Разделитель: `;` (точка с запятой)

### LAS файлы
Стандартный формат LiDAR данных. Требуется библиотека `pylas`.

### PCD файлы
Стандартный формат облаков точек Point Cloud Data.
