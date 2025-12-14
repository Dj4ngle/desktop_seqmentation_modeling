"""
Публичный API для desktop_segmentation_modeling
"""

import os
import sys
import numpy as np
from sklearn.cluster import DBSCAN
import open3d as o3d
from PyQt6.QtWidgets import QApplication

from desktop_segmentation_modeling.config import base_path
from desktop_segmentation_modeling.main_window import MyMainWindow
from desktop_segmentation_modeling.Coordinates import (
    coord_settings,
    coordinates,
    merge_coordinates,
    clear_excess_stumps
)


def run_app():
    """
    Запускает PyQt приложение для работы с облаками точек.
    
    Приложение включает:
    - Загрузку и визуализацию облаков точек (.las, .pcd)
    - Сегментацию облаков точек
    - Таксацию деревьев
    - Моделирование 3D объектов
    
    Пример использования:
        import desktop_segmentation_modeling
        desktop_segmentation_modeling.run_app()
    
    Returns:
        None - функция блокирует выполнение до закрытия приложения
    """
    app = QApplication([])
    
    # Загружаем стили
    style_path = os.path.join(base_path, 'style.qss')
    if os.path.exists(style_path):
        with open(style_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())
    else:
        print(f"Предупреждение: файл стилей не найден: {style_path}")
    
    # Создаем и показываем главное окно
    main_window = MyMainWindow()
    main_window.show()
    
    # Запускаем цикл событий
    sys.exit(app.exec())


def run_segmentation(
    point_cloud_path: str,
    eps: float = 0.78,
    min_samples: int = 132,
    output_dir: str = None
):
    """
    Выполняет сегментацию облака точек с помощью алгоритма DBSCAN.
    
    Параметры:
        point_cloud_path (str): Путь к файлу облака точек (.las, .pcd, .csv)
        eps (float): Максимальное расстояние между точками в одном кластере (по умолчанию 0.78)
        min_samples (int): Минимальное количество точек для формирования кластера (по умолчанию 132)
        output_dir (str, optional): Директория для сохранения результатов. 
                                   Если не указана, результаты сохраняются рядом с исходным файлом.
    
    Returns:
        dict: Словарь с результатами сегментации:
            - 'segments': список путей к файлам сегментированных облаков точек
            - 'num_segments': количество найденных сегментов
            - 'labels': массив меток кластеров для каждой точки
    
    Пример использования:
        import desktop_segmentation_modeling
        
        results = desktop_segmentation_modeling.run_segmentation(
            point_cloud_path='data/pointcloud.las',
            eps=0.78,
            min_samples=132
        )
        
        print(f"Найдено сегментов: {results['num_segments']}")
        for segment_file in results['segments']:
            print(f"Сегмент: {segment_file}")
    
    Raises:
        FileNotFoundError: Если файл облака точек не найден
        ValueError: Если параметры некорректны
    """
    if not os.path.exists(point_cloud_path):
        raise FileNotFoundError(f"Файл не найден: {point_cloud_path}")
    
    if eps <= 0:
        raise ValueError("eps должен быть положительным числом")
    
    if min_samples < 1:
        raise ValueError("min_samples должен быть >= 1")
    
    # Определяем директорию для сохранения результатов
    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(point_cloud_path))
    else:
        os.makedirs(output_dir, exist_ok=True)
    
    # Загружаем облако точек
    file_ext = os.path.splitext(point_cloud_path)[1].lower()
    
    if file_ext == '.pcd':
        pcd = o3d.io.read_point_cloud(point_cloud_path)
        points = np.asarray(pcd.points)
    elif file_ext == '.las':
        try:
            import pylas
            las = pylas.read(point_cloud_path)
            points = np.column_stack([las.x, las.y, las.z])
        except ImportError:
            raise ImportError("Для работы с .las файлами требуется библиотека pylas")
    elif file_ext == '.csv':
        import pandas as pd
        df = pd.read_csv(point_cloud_path, sep=';')
        if 'x' in df.columns and 'y' in df.columns and 'z' in df.columns:
            points = df[['x', 'y', 'z']].values
        elif 'X' in df.columns and 'Y' in df.columns and 'Z' in df.columns:
            points = df[['X', 'Y', 'Z']].values
        else:
            raise ValueError("CSV файл должен содержать колонки x,y,z или X,Y,Z")
    else:
        raise ValueError(f"Неподдерживаемый формат файла: {file_ext}")
    
    if len(points) == 0:
        raise ValueError("Облако точек пустое")
    
    # Выполняем сегментацию DBSCAN
    print(f"Сегментация запускается с eps: {eps} и min_samples: {min_samples}")
    db = DBSCAN(eps=eps, min_samples=min_samples).fit(points)
    labels = db.labels_
    
    # Сохраняем сегментированные облака точек
    unique_labels = np.unique(labels)
    segments = []
    base_name = os.path.splitext(os.path.basename(point_cloud_path))[0]
    
    for label in unique_labels:
        if label == -1:
            continue  # Пропустить шум
        
        segment_points = points[labels == label]
        segment_file = os.path.join(output_dir, f"{base_name}_segment_{label}.pcd")
        
        # Создаем облако точек для сегмента
        segment_pcd = o3d.geometry.PointCloud()
        segment_pcd.points = o3d.utility.Vector3dVector(segment_points)
        
        # Сохраняем сегмент
        o3d.io.write_point_cloud(segment_file, segment_pcd)
        segments.append(segment_file)
        print(f"Сохранен сегмент {label}: {segment_file} ({len(segment_points)} точек)")
    
    num_segments = len(segments)
    print(f"Сегментация завершена, найдено {num_segments} сегментов")
    
    return {
        'segments': segments,
        'num_segments': num_segments,
        'labels': labels
    }


def run_taxation(
    point_cloud_path: str,
    calculate_dbh: bool = True,
    calculate_height: bool = True,
    dbh_height: float = 1.3
):
    """
    Выполняет таксацию дерева (расчет параметров) из облака точек.
    
    Параметры:
        point_cloud_path (str): Путь к файлу облака точек дерева (.las, .pcd, .csv)
        calculate_dbh (bool): Рассчитывать ли диаметр на высоте груди (DBH) (по умолчанию True)
        calculate_height (bool): Рассчитывать ли высоту дерева (по умолчанию True)
        dbh_height (float): Высота для расчета DBH в метрах (по умолчанию 1.3 м)
    
    Returns:
        dict: Словарь с результатами таксации:
            - 'DBH': диаметр на высоте груди в метрах (или строка с ошибкой)
            - 'Height': высота дерева в метрах
            - 'points_count': количество точек в облаке
    
    Пример использования:
        import desktop_segmentation_modeling
        
        results = desktop_segmentation_modeling.run_taxation(
            point_cloud_path='data/tree.las',
            calculate_dbh=True,
            calculate_height=True,
            dbh_height=1.3
        )
        
        print(f"Высота дерева: {results['Height']:.2f} м")
        print(f"DBH: {results['DBH']:.2f} м")
    
    Raises:
        FileNotFoundError: Если файл облака точек не найден
        ValueError: Если параметры некорректны
    """
    if not os.path.exists(point_cloud_path):
        raise FileNotFoundError(f"Файл не найден: {point_cloud_path}")
    
    if dbh_height <= 0:
        raise ValueError("dbh_height должен быть положительным числом")
    
    # Загружаем облако точек
    file_ext = os.path.splitext(point_cloud_path)[1].lower()
    
    if file_ext == '.pcd':
        pcd = o3d.io.read_point_cloud(point_cloud_path)
        points = np.asarray(pcd.points)
    elif file_ext == '.las':
        try:
            import pylas
            las = pylas.read(point_cloud_path)
            points = np.column_stack([las.x, las.y, las.z])
        except ImportError:
            raise ImportError("Для работы с .las файлами требуется библиотека pylas")
    elif file_ext == '.csv':
        import pandas as pd
        df = pd.read_csv(point_cloud_path, sep=';')
        if 'x' in df.columns and 'y' in df.columns and 'z' in df.columns:
            points = df[['x', 'y', 'z']].values
        elif 'X' in df.columns and 'Y' in df.columns and 'Z' in df.columns:
            points = df[['X', 'Y', 'Z']].values
        else:
            raise ValueError("CSV файл должен содержать колонки x,y,z или X,Y,Z")
    else:
        raise ValueError(f"Неподдерживаемый формат файла: {file_ext}")
    
    if len(points) == 0:
        raise ValueError("Облако точек пустое")
    
    results = {}
    results['points_count'] = len(points)
    
    # Расчет высоты
    if calculate_height:
        z_min = np.min(points[:, 2])
        z_max = np.max(points[:, 2])
        height = z_max - z_min
        results['Height'] = height
    
    # Расчет DBH (Диаметр на Высоте Груди)
    if calculate_dbh:
        z_min = np.min(points[:, 2])
        dbh_section_height = z_min + dbh_height
        dbh_section_thickness = 0.1  # Толщина "среза" в метрах (10 см)
        
        # Выделение точек в области DBH
        z_filter = (points[:, 2] >= dbh_section_height - dbh_section_thickness / 2) & \
                   (points[:, 2] <= dbh_section_height + dbh_section_thickness / 2)
        dbh_points = points[z_filter, :]
        
        if len(dbh_points) < 10:
            results['DBH'] = "Недостаточно точек для DBH"
        else:
            # Проекция на плоскость XY
            xy_points = dbh_points[:, :2]
            
            # Расчет центра масс
            center_x, center_y = np.mean(xy_points, axis=0)
            
            # Расчет радиусов до центра
            radii = np.sqrt((xy_points[:, 0] - center_x) ** 2 + (xy_points[:, 1] - center_y) ** 2)
            
            # DBH - медианный диаметр
            median_radius = np.median(radii)
            dbh = median_radius * 2
            
            results['DBH'] = dbh
    
    return results


def run_coordinates(
    point_cloud_path: str,
    intensity_values: list = [7000, 5000, 1000],
    output_dir: str = None,
    shape_file: str = None,
    trajectory_file: str = None,
    cut_data_method: str = "voronoi_tessellation",
    height_min: float = 0.0,
    height_max: float = 3.0,
    intensity_cut: int = 0
):
    """
    Выполняет обнаружение координат деревьев (пней) из облака точек.
    
    Параметры:
        point_cloud_path (str): Путь к файлу облака точек (.las, .pcd)
        intensity_values (list): Список значений интенсивности для фильтрации точек
            (по умолчанию [7000, 5000, 1000])
        output_dir (str, optional): Директория для сохранения результатов.
                                   Если не указана, создается папка 'tmp' в текущей директории.
        shape_file (str, optional): Путь к файлу границ участка (.shp).
                                   Если не указан, границы определяются автоматически.
        trajectory_file (str, optional): Путь к файлу траектории (.las).
                                        Требуется только для метода 'flood_fill'.
        cut_data_method (str): Метод разбиения на ячейки:
            - "voronoi_tessellation" (по умолчанию) - диаграмма Вороного
            - "flood_fill" - заливка по траектории
            - "none" - без разбиения
        height_min (float): Минимальная высота для фильтрации точек в метрах (по умолчанию 0.0)
        height_max (float): Максимальная высота для фильтрации точек в метрах (по умолчанию 3.0)
        intensity_cut (int): Минимальное значение интенсивности для фильтрации (по умолчанию 0)
    
    Returns:
        str: Путь к CSV файлу с координатами деревьев
        
    Пример использования:
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
            cut_data_method='voronoi_tessellation'
        )
    
    Raises:
        FileNotFoundError: Если файл облака точек не найден
        ValueError: Если параметры некорректны
    """
    if not os.path.exists(point_cloud_path):
        raise FileNotFoundError(f"Файл не найден: {point_cloud_path}")
    
    if not intensity_values or not isinstance(intensity_values, list):
        raise ValueError("intensity_values должен быть непустым списком")
    
    if height_min >= height_max:
        raise ValueError("height_min должен быть меньше height_max")
    
    if cut_data_method not in ["voronoi_tessellation", "flood_fill", "none"]:
        raise ValueError("cut_data_method должен быть одним из: 'voronoi_tessellation', 'flood_fill', 'none'")
    
    # Определяем директорию для сохранения результатов
    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), "tmp")
    os.makedirs(output_dir, exist_ok=True)
    
    # Проверяем наличие shape файла
    if shape_file and not os.path.exists(shape_file):
        print(f"Предупреждение: файл границ не найден: {shape_file}. Будут использованы границы всего участка.")
        shape_file = None
    
    # Проверяем наличие trajectory файла для метода flood_fill
    if cut_data_method == "flood_fill":
        if trajectory_file and not os.path.exists(trajectory_file):
            raise FileNotFoundError(f"Для метода 'flood_fill' требуется файл траектории: {trajectory_file}")
        elif not trajectory_file:
            raise ValueError("Для метода 'flood_fill' требуется указать trajectory_file")
    
    # Создаем настройки CS
    cs = coord_settings.CS()
    cs.fname_points = point_cloud_path
    cs.path_base = output_dir
    cs.cut_data_method = cut_data_method
    cs.LOW = height_min
    cs.UP = height_max
    cs.intensity_cut = intensity_cut
    
    if shape_file:
        cs.fname_shape = shape_file
    else:
        cs.fname_shape = "Polyline.shp"  # Будет создан автоматически
    
    if trajectory_file:
        cs.fname_traj = trajectory_file
    else:
        cs.fname_traj = "traj.las"
    
    # Выполняем обнаружение координат для каждого значения интенсивности
    print(f"Запуск обнаружения координат для файла: {point_cloud_path}")
    print(f"Значения интенсивности: {intensity_values}")
    
    for intensity_cut_make in intensity_values:
        print(f"Обработка с интенсивностью {intensity_cut_make}...")
        coordinates.coordinates(intensity_cut_make, cs)
    
    # Объединяем координаты
    print("Объединение координат...")
    merge_coordinates.merge_coordinates(cs)
    
    # Очищаем лишние пни (используя модель классификации)
    print("Очистка лишних пней...")
    csv_output_file = clear_excess_stumps.clear_excess_stumps(cs)
    
    print(f"Обнаружение координат завершено. Результаты сохранены в: {csv_output_file}")
    
    return csv_output_file
