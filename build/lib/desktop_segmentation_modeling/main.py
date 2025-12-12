import os
from PyQt6.QtWidgets import QApplication

from desktop_segmentation_modeling.config import base_path
from desktop_segmentation_modeling.main_window import MyMainWindow

if __name__ == "__main__":
    app = QApplication([])

    style_path = os.path.join(base_path, 'style.qss')

    # Применяем стили
    app.setStyleSheet(open(style_path).read())

    main_window = MyMainWindow()
    main_window.show()
    app.exec()
