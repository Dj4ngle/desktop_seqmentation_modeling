"""
Desktop Segmentation and Modeling - A powerful desktop application 
for 3D point cloud and image segmentation using machine learning.

Публичный API:
- run_app() - запуск PyQt приложения
- run_segmentation() - запуск сегментации облака точек
- run_taxation() - запуск таксации деревьев
- run_coordinates() - обнаружение координат деревьев (пней)
"""

__version__ = '1.0.12'
__author__ = 'Dj4ngle'
__url__ = 'https://github.com/Dj4ngle/desktop_seqmentation_modeling'

def run_app(*args, **kwargs):
    from desktop_segmentation_modeling.api import run_app as _run_app
    return _run_app(*args, **kwargs)


def run_segmentation(*args, **kwargs):
    from desktop_segmentation_modeling.api import run_segmentation as _run_segmentation
    return _run_segmentation(*args, **kwargs)


def run_taxation(*args, **kwargs):
    from desktop_segmentation_modeling.api import run_taxation as _run_taxation
    return _run_taxation(*args, **kwargs)


def run_coordinates(*args, **kwargs):
    from desktop_segmentation_modeling.api import run_coordinates as _run_coordinates
    return _run_coordinates(*args, **kwargs)

__all__ = ['run_app', 'run_segmentation', 'run_taxation', 'run_coordinates', '__version__']
