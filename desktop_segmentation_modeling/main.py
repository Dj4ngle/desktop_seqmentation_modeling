import os
import sys
from PyQt6.QtWidgets import QApplication

from desktop_segmentation_modeling.config import base_path
from desktop_segmentation_modeling.main_window import MyMainWindow

if __name__ == "__main__":
    app = QApplication([])

    # Загружаем стили
    style_path = os.path.join(base_path, 'style.qss')
    if os.path.exists(style_path):
        try:
            with open(style_path, 'r', encoding='utf-8') as f:
                app.setStyleSheet(f.read())
        except Exception as e:
            print(f"Предупреждение: не удалось загрузить стили: {e}")
    else:
        print(f"Предупреждение: файл стилей не найден: {style_path}")

    main_window = MyMainWindow()
    main_window.show()
    sys.exit(app.exec())
