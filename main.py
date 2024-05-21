import sys
from PyQt6.QtWidgets import QApplication
from main_window import MyMainWindow

if __name__ == "__main__":
    app = QApplication([])

    # Применяем стили
    app.setStyleSheet(open("style.qss").read())

    main_window = MyMainWindow()
    main_window.show()
    app.exec()
