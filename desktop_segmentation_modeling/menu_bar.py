import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMenuBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from desktop_segmentation_modeling.config import base_path

class MenuBar:
    def __init__(self, parent=None):
        self.parent = parent
        
    def create_menu_bar(self):
        menuBar = QMenuBar(self.parent)
        self.parent.setMenuBar(menuBar)
        # Создание меню "Файл" с помощью объекта QMenu
        fileMenu = QMenu("Файл", self.parent)
        menuBar.addMenu(fileMenu)
        # fileMenu.addAction(self.newAction)
        fileMenu.addAction(self.openAction)
        fileMenu.addAction(self.saveAction)
        fileMenu.addAction(self.exitAction)

        # Меню "Помощь"
        helpMenu = menuBar.addMenu("Помощь")
        helpMenu.addAction(self.helpContentAction)
        helpMenu.addAction(self.aboutAction)
        
    def create_actions(self):
        self.openAction = QAction("Открыть", self.parent)
        self.saveAction = QAction("Сохранить", self.parent)
        self.exitAction = QAction("Выйти", self.parent)

        # Действия в меню "Помощь"
        self.helpContentAction = QAction("Справочный материал", self.parent)
        self.aboutAction = QAction("О приложении", self.parent)

        self.helpContentAction.triggered.connect(self.show_help_content)
        self.aboutAction.triggered.connect(self.show_about)

    def show_help_content(self):
        self.show_info_dialog(
            "Справочный материал",
            "Desktop Segmentation and Modeling\n\n"
            "Основные действия:\n"
            "- Файл -> Открыть: загрузить облака точек .las, .pcd или модель .obj.\n"
            "- Файл -> Сохранить: сохранить выбранные файлы.\n"
            "- Панель инструментов: открыть удаление земли, сегментацию, таксацию, "
            "моделирование или координаты.\n"
            "- Список 'Файлы': отметьте чекбокс, чтобы отобразить файл и использовать его "
            "в инструментах.\n\n"
            "Поддерживаемые форматы: LAS, PCD, OBJ."
        )

    def show_about(self):
        self.show_info_dialog(
            "О приложении",
            "Desktop Segmentation and Modeling\n\n"
            "Приложение для визуализации и обработки 3D облаков точек.\n\n"
            "Возможности:\n"
            "- визуализация LAS/PCD;\n"
            "- удаление земли;\n"
            "- сегментация деревьев;\n"
            "- таксация;\n"
            "- построение 3D моделей;\n"
            "- обнаружение координат деревьев."
        )

    def show_info_dialog(self, title, text):
        dialog = QDialog(self.parent)
        dialog.setWindowTitle(title)
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowType.FramelessWindowHint)
        dialog.setMinimumWidth(480)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #3F3F46;
                color: #CCCEDB;
                border: 1px solid #66666d;
            }
            QLabel {
                background-color: transparent;
                color: #CCCEDB;
            }
            QTextEdit {
                background-color: #494950;
                color: #CCCEDB;
                border: 1px solid #66666d;
                border-radius: 6px;
                padding: 10px;
                selection-background-color: #1E88E5;
            }
            QPushButton {
                background-color: #494950;
                color: #CCCEDB;
                border: 1px solid #66666d;
                border-radius: 4px;
                padding: 6px 18px;
            }
            QPushButton:hover {
                background-color: #52525a;
            }
            QPushButton:pressed {
                background-color: #66666d;
            }
            QPushButton#closeButton {
                min-width: 24px;
                max-width: 24px;
                min-height: 24px;
                max-height: 24px;
                padding: 0;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        close_button = QPushButton("x")
        close_button.setObjectName("closeButton")
        close_button.clicked.connect(dialog.reject)
        header_layout.addWidget(close_button)
        layout.addLayout(header_layout)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(text)
        text_edit.setMinimumHeight(220)
        layout.addWidget(text_edit)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(dialog.accept)
        buttons_layout.addWidget(ok_button)
        layout.addLayout(buttons_layout)

        icon_path = os.path.join(base_path, "images", "Icon.png")
        if os.path.exists(icon_path):
            dialog.setWindowIcon(QIcon(icon_path))

        dialog.exec()
