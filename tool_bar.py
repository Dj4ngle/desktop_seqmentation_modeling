from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QToolBar, QApplication
from PyQt6.QtGui import QIcon, QAction

class ToolBar:
    def __init__(self, parent=None):
        self.parent = parent

    def _createToolBars(self):
        # Создание панели инструментов "Панель управленя взаимодействием"
        editToolBar = QToolBar("Панель управления взаимодействием", self.parent)
        editToolBar.addAction(self.earthExtractionAction)
        editToolBar.addAction(self.segmentationAction)
        editToolBar.addAction(self.taxationAction)
        editToolBar.addAction(self.modelingAction)
        self.parent.addToolBar(editToolBar)
        # Использование объекта QToolBar и области панели инструментов
        interactionToolBar = QToolBar("Панел управления вращения", self.parent)
        interactionToolBar.addAction(self.frontViewAction)
        interactionToolBar.addAction(self.backViewAction)
        interactionToolBar.addAction(self.leftSideViewAction)
        interactionToolBar.addAction(self.rightSideViewAction)
        interactionToolBar.addAction(self.topViewAction)
        interactionToolBar.addAction(self.bottomViewAction)
        self.parent.addToolBar(Qt.ToolBarArea.LeftToolBarArea, interactionToolBar)
        
    def create_actions(self):
        # Действия для панели инструментов
        self.earthExtractionAction = QAction(QIcon("images/ground_extraction.png"), "Удаление земли", self.parent)
        self.segmentationAction = QAction(QIcon("images/segmentation.png"), "Сегментация", self.parent)
        self.taxationAction = QAction(QIcon("images/taxation.png"), "Таксация", self.parent)
        self.modelingAction = QAction(QIcon("images/modeling.png"), "Моделирование", self.parent)
        self.frontViewAction = QAction(QIcon("images/FrontView.png"), "Вид спереди", self.parent)
        self.backViewAction = QAction(QIcon("images/BackView.png"), "Вид сзади", self.parent)
        self.leftSideViewAction = QAction(QIcon("images/SideViewLeft.png"), "Вид сбоку", self.parent)
        self.rightSideViewAction = QAction(QIcon("images/SideViewRight.png"), "Вид сбоку", self.parent)
        self.topViewAction = QAction(QIcon("images/TopView.png"), "Вид сверху", self.parent)
        self.bottomViewAction = QAction(QIcon("images/BottomView.png"), "Вид снизу", self.parent)
