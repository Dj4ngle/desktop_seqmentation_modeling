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
from desktop_segmentation_modeling.point_cloud_widget import POINT_CLOUD_PALETTE_LABELS


def load_theme_stylesheet(file_name):
    style_path = os.path.join(base_path, file_name)
    if not os.path.exists(style_path):
        return ""

    with open(style_path, 'r', encoding='utf-8') as style_file:
        return style_file.read()


POINT_CLOUD_PALETTE_ORDER = ("blue", "cyan", "green", "orange", "violet", "gray")


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
        paintMenu = settingsMenu.addMenu("Покраска")
        for action in self.paintPaletteActions:
            paintMenu.addAction(action)
        paintMenu.addSeparator()
        paintMenu.addAction(self.resetPaintAction)

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
        self.paintPaletteActions = []
        for palette_name in POINT_CLOUD_PALETTE_ORDER:
            action = QAction(POINT_CLOUD_PALETTE_LABELS[palette_name], self.parent)
            action.triggered.connect(
                lambda checked=False, name=palette_name: self.apply_point_cloud_palette(name)
            )
            self.paintPaletteActions.append(action)
        self.resetPaintAction = QAction("Сбросить покраску", self.parent)

        self.darkThemeAction.triggered.connect(lambda: self.apply_theme("dark"))
        self.lightThemeAction.triggered.connect(lambda: self.apply_theme("light"))
        self.helpContentAction.triggered.connect(self.show_help_content)
        self.aboutAction.triggered.connect(self.show_about)
        self.resetPaintAction.triggered.connect(self.reset_point_cloud_palette)

    def apply_point_cloud_palette(self, palette_name):
        if self.parent is not None and hasattr(self.parent, "apply_selected_point_cloud_palette"):
            self.parent.apply_selected_point_cloud_palette(palette_name)

    def reset_point_cloud_palette(self):
        if self.parent is not None and hasattr(self.parent, "reset_selected_point_cloud_palette"):
            self.parent.reset_selected_point_cloud_palette()

    def apply_theme(self, theme_name):
        app = QApplication.instance()
        if app is None:
            return

        if theme_name == "light":
            app.setStyleSheet(load_theme_stylesheet('style_light.qss'))
            self.lightThemeAction.setChecked(True)
        else:
            app.setStyleSheet(load_theme_stylesheet('style.qss'))
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
