import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QActionGroup, QIcon
from PyQt6.QtWidgets import (
    QApplication,
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


LIGHT_THEME_QSS = """
QMenuBar {
    background-color: #F3F4F6;
    color: #1F2937;
}
QMenuBar::item {
    background-color: #F3F4F6;
    color: #1F2937;
    padding: 4px 7px;
    border: 1px solid #F3F4F6;
    border-radius: 7px;
}
QMenuBar::item:selected {
    background-color: #E5E7EB;
    color: #111827;
}
QMenu {
    background-color: #FFFFFF;
    color: #1F2937;
    border: 1px solid #D1D5DB;
}
QMenu::item {
    background-color: #FFFFFF;
    color: #1F2937;
    padding: 4px 15px 4px 7px;
    border-radius: 7px;
}
QMenu::item:selected {
    background-color: #E5E7EB;
    color: #111827;
}
QMenu::item:pressed {
    background-color: #D1D5DB;
}
QMainWindow, QWidget {
    background-color: #F3F4F6;
    color: #1F2937;
}
QToolBar {
    background-color: #F3F4F6;
    color: #1F2937;
    border: none;
}
QToolButton:hover {
    background-color: #E5E7EB;
}
QToolButton:pressed {
    background-color: #D1D5DB;
}
QPushButton {
    background-color: #FFFFFF;
    color: #1F2937;
    border: 1px solid #D1D5DB;
    border-radius: 3px;
    padding: 3px 6px;
}
QPushButton:hover {
    background-color: #E5E7EB;
}
QPushButton:pressed {
    background-color: #D1D5DB;
}
QListWidget, QPlainTextEdit, QTextEdit {
    background-color: #FFFFFF;
    color: #1F2937;
    border: 1px solid #D1D5DB;
    padding: 5px;
}
QLabel, QCheckBox, QRadioButton {
    background-color: transparent;
    color: #1F2937;
}
QCheckBox::indicator:unchecked {
    background-color: #FFFFFF;
    border: 1px solid #9CA3AF;
    border-radius: 3px;
}
QCheckBox::indicator:checked {
    background-color: #2563EB;
    border: 1px solid #2563EB;
    border-radius: 3px;
    width: 11px;
    height: 11px;
}
QDockWidget {
    background-color: #F3F4F6;
    color: #1F2937;
}
QDockWidget::title {
    text-align: left;
    background-color: #E5E7EB;
    color: #1F2937;
    padding: 1px;
}
QDockWidget::close-button, QDockWidget::float-button {
    background-color: #E5E7EB;
    border-color: #6B7280;
}
QDockWidget::close-button:hover, QDockWidget::float-button:hover {
    background-color: #D1D5DB;
}
QLineEdit, QComboBox, QDoubleSpinBox {
    background-color: #FFFFFF;
    color: #1F2937;
    border: 1px solid #D1D5DB;
}
QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    color: #1F2937;
}
QComboBox QAbstractItemView::item:selected {
    background-color: #E5E7EB;
    color: #111827;
}
QScrollArea {
    background-color: #F3F4F6;
    border: 1px solid #D1D5DB;
}
QScrollArea > QWidget > QWidget {
    background-color: #F3F4F6;
}
QScrollBar:horizontal, QScrollBar:vertical {
    background: #F3F4F6;
}
QToolTip {
    background-color: #FFFFFF;
    color: #1F2937;
    border: 1px solid #D1D5DB;
}
"""

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

        # Меню "Настройки"
        settingsMenu = menuBar.addMenu("Настройки")
        themeMenu = settingsMenu.addMenu("Тема")
        themeMenu.addAction(self.darkThemeAction)
        themeMenu.addAction(self.lightThemeAction)

        # Меню "Помощь"
        helpMenu = menuBar.addMenu("Помощь")
        helpMenu.addAction(self.helpContentAction)
        helpMenu.addAction(self.aboutAction)
        
    def create_actions(self):
        self.openAction = QAction("Открыть", self.parent)
        self.saveAction = QAction("Сохранить", self.parent)
        self.exitAction = QAction("Выйти", self.parent)

        # Действия в меню "Настройки"
        self.darkThemeAction = QAction("Тёмная", self.parent)
        self.lightThemeAction = QAction("Светлая", self.parent)
        self.darkThemeAction.setCheckable(True)
        self.lightThemeAction.setCheckable(True)
        self.darkThemeAction.setChecked(True)

        self.themeActionGroup = QActionGroup(self.parent)
        self.themeActionGroup.setExclusive(True)
        self.themeActionGroup.addAction(self.darkThemeAction)
        self.themeActionGroup.addAction(self.lightThemeAction)

        # Действия в меню "Помощь"
        self.helpContentAction = QAction("Справочный материал", self.parent)
        self.aboutAction = QAction("О приложении", self.parent)

        self.darkThemeAction.triggered.connect(lambda: self.apply_theme("dark"))
        self.lightThemeAction.triggered.connect(lambda: self.apply_theme("light"))
        self.helpContentAction.triggered.connect(self.show_help_content)
        self.aboutAction.triggered.connect(self.show_about)

    def apply_theme(self, theme_name):
        app = QApplication.instance()
        if app is None:
            return

        if theme_name == "light":
            app.setStyleSheet(LIGHT_THEME_QSS)
            self.lightThemeAction.setChecked(True)
        else:
            style_path = os.path.join(base_path, 'style.qss')
            if os.path.exists(style_path):
                with open(style_path, 'r', encoding='utf-8') as style_file:
                    app.setStyleSheet(style_file.read())
            else:
                app.setStyleSheet("")
            self.darkThemeAction.setChecked(True)

        if self.parent is not None:
            self.parent.current_theme = theme_name
            if hasattr(self.parent, "openGLWidget"):
                if theme_name == "light":
                    self.parent.openGLWidget.set_background_color(1.0, 1.0, 1.0, 1.0)
                else:
                    self.parent.openGLWidget.set_background_color(0.0, 0.0, 0.0, 1.0)

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
        dialog.setStyleSheet(self.get_dialog_stylesheet())

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

    def get_dialog_stylesheet(self):
        if getattr(self.parent, "current_theme", "dark") == "light":
            return """
            QDialog {
                background-color: #F3F4F6;
                color: #1F2937;
                border: 1px solid #D1D5DB;
            }
            QLabel {
                background-color: transparent;
                color: #1F2937;
            }
            QTextEdit {
                background-color: #FFFFFF;
                color: #1F2937;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 10px;
                selection-background-color: #2563EB;
            }
            QPushButton {
                background-color: #FFFFFF;
                color: #1F2937;
                border: 1px solid #D1D5DB;
                border-radius: 4px;
                padding: 6px 18px;
            }
            QPushButton:hover {
                background-color: #E5E7EB;
            }
            QPushButton:pressed {
                background-color: #D1D5DB;
            }
            QPushButton#closeButton {
                min-width: 24px;
                max-width: 24px;
                min-height: 24px;
                max-height: 24px;
                padding: 0;
                border-radius: 12px;
            }
            """

        return """
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
        """
