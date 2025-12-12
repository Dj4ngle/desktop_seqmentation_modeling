import tkinter as tk
from tkinter import filedialog
import open3d as o3d
import numpy as np

def rotate_point_cloud_pcd(file_path, output_path, rotation_matrix):
    pcd = o3d.io.read_point_cloud(file_path)
    pcd.rotate(rotation_matrix, center=(0, 0, 0))  # Поворот вокруг центра координат
    o3d.io.write_point_cloud(output_path, pcd)

def select_files_and_rotate():
    # Создание корневого окна
    root = tk.Tk()
    root.withdraw()  # Скрываем корневое окно

    # Выбор файлов PCD
    file_paths = filedialog.askopenfilenames(
        title="Выберите файлы PCD",
        filetypes=(("PCD files", "*.pcd"), ("All files", "*.*"))
    )

    if not file_paths:
        return

    # Выбор директории для сохранения
    output_directory = filedialog.askdirectory(title="Выберите папку для сохранения файлов")

    if not output_directory:
        return

    # Создание матрицы поворота на 90 градусов вокруг оси X
    rotation_matrix = o3d.geometry.get_rotation_matrix_from_xyz((-np.pi / 2, 0, 0))

    # Поворот и сохранение каждого файла
    for file_path in file_paths:
        output_path = f"{output_directory}/{file_path.split('/')[-1]}"
        rotate_point_cloud_pcd(file_path, output_path, rotation_matrix)
        print(f"Файл сохранен: {output_path}")

# Запуск GUI для выбора файлов и папки
select_files_and_rotate()