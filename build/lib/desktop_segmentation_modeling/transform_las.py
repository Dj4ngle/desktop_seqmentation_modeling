import tkinter as tk
from tkinter import filedialog
import laspy
import numpy as np

def rotate_point_cloud_las(file_path, output_path, rotation_matrix):
    las = laspy.read(file_path)
    points = np.vstack((las.x, las.y, las.z)).transpose()
    rotated_points = np.dot(points, rotation_matrix.T)
    las.x = rotated_points[:, 0]
    las.y = rotated_points[:, 1]
    las.z = rotated_points[:, 2]
    las.write(output_path)

def select_files_and_rotate():
    # Создание корневого окна
    root = tk.Tk()
    root.withdraw()  # Скрываем корневое окно

    # Выбор файлов LAS
    file_paths = filedialog.askopenfilenames(
        title="Выберите файлы LAS",
        filetypes=(("LAS files", "*.las"), ("All files", "*.*"))
    )

    if not file_paths:
        return

    # Выбор директории для сохранения
    output_directory = filedialog.askdirectory(title="Выберите папку для сохранения файлов")

    if not output_directory:
        return

    # Создание матрицы поворота на 90 градусов вокруг оси X
    rotation_matrix = np.array([
        [1, 0, 0],
        [0, np.cos(np.pi / -2), -np.sin(np.pi / -2)],
        [0, np.sin(np.pi / -2), np.cos(np.pi / -2)]
    ])

    # Поворот и сохранение каждого файла
    for file_path in file_paths:
        output_path = f"{output_directory}/{file_path.split('/')[-1]}"
        rotate_point_cloud_las(file_path, output_path, rotation_matrix)
        print(f"Файл сохранен: {output_path}")

# Запуск GUI для выбора файлов и папки
select_files_and_rotate()