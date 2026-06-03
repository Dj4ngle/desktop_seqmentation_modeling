# Toolbar_Widgets/example_widget.py
from PyQt6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt

def example_dock_widget(self):
    """Возвращает (и кэширует) QDockWidget с нашим GUI."""
    if 'example' not in self.dock_widgets:
        dock = QDockWidget("Пример")
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)

        widget  = QWidget()
        layout  = QVBoxLayout(widget)
        layout.addWidget(QLabel("Привет из example_widget!"))
        btn = QPushButton("Вывести сообщение")
        btn.clicked.connect(lambda: print("example_widget: кнопка нажата"))
        layout.addWidget(btn)

        dock.setWidget(widget)
        self.dock_widgets['example'] = dock          # обязательно кэшируем!

    return self.dock_widgets['example']