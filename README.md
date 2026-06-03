# Desktop Segmentation and Modeling

A powerful desktop application for 3D point cloud and image segmentation using machine learning.

## Установка

```bash
pip install desktop-segmentation-modeling
```

## Быстрый старт

### Запуск приложения

```python
import desktop_segmentation_modeling

# Запуск PyQt приложения
desktop_segmentation_modeling.run_app()
```

### Использование API

```python
import desktop_segmentation_modeling

# 1. Обнаружение координат деревьев
csv_file = desktop_segmentation_modeling.run_coordinates(
    point_cloud_path='data/forest.las',
    intensity_values=[7000, 5000, 1000]
)

# 2. Сегментация облака точек
results = desktop_segmentation_modeling.run_segmentation(
    point_cloud_path='data/forest.las',
    eps=0.78,
    min_samples=132
)

# 3. Таксация дерева
taxation = desktop_segmentation_modeling.run_taxation(
    point_cloud_path='data/tree.las',
    calculate_dbh=True,
    calculate_height=True
)
```

## Публичный API

### `run_app()`

Запускает PyQt приложение для работы с облаками точек.

**Параметры:** Нет

**Пример:**
```python
import desktop_segmentation_modeling
desktop_segmentation_modeling.run_app()
```

---

### `run_segmentation()`

Выполняет сегментацию облака точек с помощью алгоритма DBSCAN.

**Параметры:**
- `point_cloud_path` (str): Путь к файлу облака точек (.las, .pcd)
- `eps` (float, default=0.78): Максимальное расстояние между точками в кластере
- `min_samples` (int, default=132): Минимальное количество точек для кластера
- `output_dir` (str, optional): Директория для сохранения результатов

**Возвращает:**
```python
{
    'segments': [список путей к файлам],
    'num_segments': количество сегментов,
    'labels': массив меток кластеров
}
```

**Пример:**
```python
results = desktop_segmentation_modeling.run_segmentation(
    point_cloud_path='data/pointcloud.las',
    eps=0.78,
    min_samples=132
)
```

---

### `run_taxation()`

Выполняет таксацию дерева (расчет параметров) из облака точек.

**Параметры:**
- `point_cloud_path` (str): Путь к файлу облака точек дерева (.las, .pcd)
- `calculate_dbh` (bool, default=True): Рассчитывать диаметр на высоте груди
- `calculate_height` (bool, default=True): Рассчитывать высоту дерева
- `dbh_height` (float, default=1.3): Высота для расчета DBH в метрах

**Возвращает:**
```python
{
    'DBH': диаметр на высоте груди (float или str),
    'Height': высота дерева (float),
    'points_count': количество точек (int)
}
```

**Пример:**
```python
results = desktop_segmentation_modeling.run_taxation(
    point_cloud_path='data/tree.las',
    calculate_dbh=True,
    calculate_height=True
)
```

---

### `run_coordinates()`

Выполняет обнаружение координат деревьев (пней) из облака точек.

**Параметры:**
- `point_cloud_path` (str): Путь к файлу облака точек (.las, .pcd)
- `intensity_values` (list, default=[7000, 5000, 1000]): Список значений интенсивности
- `output_dir` (str, optional): Директория для сохранения (по умолчанию `tmp/`)
- `shape_file` (str, optional): Путь к файлу границ участка (.shp)
- `trajectory_file` (str, optional): Путь к файлу траектории (.las) - для метода `flood_fill`
- `cut_data_method` (str, default="voronoi_tessellation"): Метод разбиения на ячейки
  - `"voronoi_tessellation"` - диаграмма Вороного
  - `"flood_fill"` - заливка по траектории
  - `"none"` - без разбиения
- `height_min` (float, default=0.0): Минимальная высота для фильтрации (метры)
- `height_max` (float, default=3.0): Максимальная высота для фильтрации (метры)
- `intensity_cut` (int, default=0): Минимальное значение интенсивности

**Возвращает:**
- `str`: Путь к CSV файлу с координатами деревьев

**Пример:**
```python
csv_file = desktop_segmentation_modeling.run_coordinates(
    point_cloud_path='data/forest.las',
    intensity_values=[7000, 5000, 1000],
    output_dir='output/coordinates'
)
```

---

## Подробная документация

Полная документация по использованию API доступна в файле [API_USAGE.md](API_USAGE.md) в репозитории проекта.

## Требования

- Python >= 3.11
- См. [requirements.txt](requirements.txt) для полного списка зависимостей

## Поддерживаемые форматы

- **LAS** - стандартный формат LiDAR данных
- **PCD** - формат облаков точек Point Cloud Data
- **CSV** - для координат (разделитель `;`)

---

## Как подключить собственный виджет
