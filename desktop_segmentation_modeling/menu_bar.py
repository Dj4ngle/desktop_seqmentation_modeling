from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenuBar, QMenu

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
        # Меню "Правка"
        editMenu = menuBar.addMenu("Правка")
        # Подменю "Цвет" в меню "Правка"
        findMenu = editMenu.addMenu("Цвет")
        findMenu.addAction(self.selectFromListAction)
        findMenu.addAction(self.createNewColorAction)
        # Подменю "Рендерер" в меню "Правка"
        rendererMenu = editMenu.addMenu("Рендерер")
        rendererMenu.addAction(self.useOpenGLAction)
        rendererMenu.addAction(self.useVulkanAction)
        # Меню "Помощь"
        helpMenu = menuBar.addMenu("Помощь")
        helpMenu.addAction(self.helpContentAction)
        helpMenu.addAction(self.aboutAction)
        
    def create_actions(self):
        self.openAction = QAction("Открыть", self.parent)
        self.saveAction = QAction("Сохранить", self.parent)
        self.exitAction = QAction("Выйти", self.parent)
        # Действия в меню "Правка"
        self.colorAction = QAction("Цвет", self.parent)
        # Действия в подменю "Цвет"
        self.selectFromListAction = QAction("Выбрать из списка", self.parent)
        self.createNewColorAction = QAction("Создать новый цвет", self.parent)
        # Действия в подменю "Рендерер"
        self.useOpenGLAction = QAction("Использовать OpenGL", self.parent)
        self.useOpenGLAction.setCheckable(True)
        self.useVulkanAction = QAction("Использовать Vulkan", self.parent)
        self.useVulkanAction.setCheckable(True)
        # Действия в меню "Помощь"
        self.helpContentAction = QAction("Справочный материал", self.parent)
        self.aboutAction = QAction("О приложении", self.parent)
