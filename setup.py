# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

# --- Метаданные ---
PACKAGE_NAME = 'desktop_segmentation_modeling'
VERSION = '1.0.12'  # Начальная версия, которую вы можете обновить
DESCRIPTION = 'A powerful desktop application for 3D point cloud and image segmentation using machine learning.'
URL = 'https://github.com/Dj4ngle/desktop_seqmentation_modeling'
AUTHOR = 'Dj4ngle'
AUTHOR_EMAIL = ''  # Укажите ваш email, если хотите
PYTHON_VERSION = '>=3.11'  # Целевая версия Python

# --- Список Зависимостей ---
# Обновлено на основе requirements.txt
INSTALL_REQUIRES = [
    'asttokens==3.0.1',
    'attrs==25.4.0',
    'blinker==1.9.0',
    'certifi==2025.11.12',
    'charset-normalizer==3.4.4',
    'circle-fit==0.2.1',
    'click==8.3.1',
    'colorama==0.4.6',
    'comm==0.2.3',
    'ConfigArgParse==1.7.1',
    'contourpy==1.3.2',
    'cycler==0.12.1',
    'dash==3.3.0',
    'decorator==5.2.1',
    'exceptiongroup==1.3.1',
    'executing==2.2.1',
    'fastjsonschema==2.21.2',
    'filelock==3.20.0',
    'Flask==3.1.2',
    'fonttools==4.61.1',
    'fsspec==2025.12.0',
    'hdbscan==0.8.41',
    'idna==3.11',
    'importlib_metadata==8.7.0',
    'ipython==8.37.0',
    'ipywidgets==8.1.8',
    'itsdangerous==2.2.0',
    'jedi==0.19.2',
    'Jinja2==3.1.6',
    'joblib==1.5.2',
    'jsonschema==4.25.1',
    'jsonschema-specifications==2025.9.1',
    'jupyter_core==5.9.1',
    'jupyterlab_widgets==3.0.16',
    'kiwisolver==1.4.9',
    'laspy==2.6.1',
    'llvmlite==0.46.0',
    'MarkupSafe==3.0.3',
    'matplotlib==3.10.8',
    'matplotlib-inline==0.2.1',
    'mpmath==1.3.0',
    'narwhals==2.13.0',
    'nbformat==5.10.4',
    'nest-asyncio==1.6.0',
    'networkx==3.4.2',
    'numba==0.63.1',
    'numpy==2.2.6',
    'open3d==0.19.0',
    'packaging==25.0',
    'pandas==2.3.3',
    'parso==0.8.5',
    'pillow==12.0.0',
    'platformdirs==4.5.1',
    'plotly==6.5.0',
    'pooch==1.8.2',
    'prompt_toolkit==3.0.52',
    'pure_eval==0.2.3',
    'Pygments==2.19.2',
    'pylas==0.4.3',
    'pyntcloud==0.3.1',
    'PyOpenGL==3.1.10',
    'PyOpenGL-accelerate==3.1.10',
    'pyparsing==3.2.5',
    'PyQt6==6.10.1',
    'PyQt6-Qt6==6.10.1',
    'PyQt6_sip==13.10.3',
    'pyshp==3.0.3',
    'python-dateutil==2.9.0.post0',
    'python-lzf==0.2.6',
    'pytz==2025.2',
    'pyvista==0.46.4',
    'PyWavefront==1.3.3',
    'referencing==0.37.0',
    'requests==2.32.5',
    'retrying==1.4.2',
    'rpds-py==0.30.0',
    'scikit-learn==1.7.2',
    'scipy==1.15.3',
    'scooby==0.11.0',
    'seaborn==0.13.2',
    'shapely==2.1.2',
    'six==1.17.0',
    'stack-data==0.6.3',
    'sympy==1.14.0',
    'threadpoolctl==3.6.0',
    'torch==2.9.1',
    'tqdm==4.67.1',
    'traitlets==5.14.3',
    'trimesh==4.10.1',
    'typing_extensions==4.15.0',
    'tzdata==2025.2',
    'urllib3==2.6.2',
    'vtk==9.5.2',
    'wcwidth==0.2.14',
    'Werkzeug==3.1.4',
    'widgetsnbextension==4.0.15',
    'zipp==3.23.0',
]

# --- Исполнение setup ---
setup(
    name=PACKAGE_NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=open('README.md', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    url=URL,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    license='MIT',  # Часто используемая открытая лицензия, рекомендуется добавить LICENSE файл
    packages=find_packages(),
    install_requires=INSTALL_REQUIRES,

    package_data={
        'desktop_segmentation_modeling': [
            'style.qss',
            'style_light.qss',
            'images/*',
            'design.ui',
        ],
    },
    include_package_data=True,  # MANIFEST.in будет использован для включения остальных файлов

    # Классификаторы помогают людям найти ваш пакет на PyPI
    classifiers=[
        'Development Status :: 4 - Beta',  # Укажите актуальный статус
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.11',
        'Topic :: Scientific/Engineering :: GIS',
        'Topic :: Scientific/Engineering :: Image Processing',
        'Operating System :: OS Independent',
    ],
    python_requires=PYTHON_VERSION,
)
