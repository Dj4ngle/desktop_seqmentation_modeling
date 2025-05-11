## Как подключить собственный виджет

Ниже — **краткая инструкция** по добавлению нового док-виджета и кнопки на панель инструментов.

В примерах используется тестовый виджет `example_widget`. Полный код лежит в `Toolbar_Widgets/example_widget.py`.

---

### 1. Создаём файл виджета

```python
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
```

---

### 2. Изменения в **`Toolbar_Widgets/design.py`**

Функция `init_dock_widgets()` уже лежит именно здесь (а не в `main_window.py`).

1. Импортируйте новый модуль над функцией:

```python
from Toolbar_Widgets import example_widget
```

2. В самой функции добавьте строку в словарь:

```python
def init_dock_widgets(self):
    self.dock_widgets = {
        'ground_extraction': ground_extraction.ground_extraction_dock_widget(self),
        'segmentation'     : segmentation.segmentation_dock_widget(self),
        'taxation'         : taxation.taxation_dock_widget(self),
        'modeling'         : modeling.modeling_dock_widget(self),
        'coordinates'      : coordinates.coordinates_dock_widget(self),
        'example'          : example_widget.example_dock_widget(self)   # ← наш виджет
    }
```

---

### 3. Добавляем кнопку на панель инструментов

1. Положите PNG-иконку (64 × 64) в папку `images/` (например `example.png`).

2. В **`Toolbar/tool_bar.py`**

```python
class ToolBar:
    def create_actions(self):
        # …другие действия…
        self.exampleAction = QAction(
            QIcon(os.path.join(base_path, "images/example.png")),
            "Пример", self.parent
        )

    def _createToolBars(self):
        editToolBar = QToolBar("Панель управления взаимодействием", self.parent)
        # …существующие addAction…
        editToolBar.addAction(self.exampleAction)       # ← добавили
        self.parent.addToolBar(editToolBar)
```

---

### 4. Связываем кнопку с показом виджета

В **`main_window.py`** (конструктор `MyMainWindow.__init__`):

```python
self.toolbarsCreator.exampleAction.triggered.connect(
    lambda: self.toggle_dock_widget(
        'example',                         # ключ из init_dock_widgets
        Qt.DockWidgetArea.LeftDockWidgetArea
    )
)
```

---

### 5. (Необязательно) работа со списками файлов

Если ваш виджет создаёт новые облака/модели, вызывайте:

```python
self.openGLWidget.load_point_cloud(path)
self.add_file_to_list_widget(path)
```

---

### 6. Проверка

1. Запустите приложение.
2. Нажмите кнопку **«Пример»** в панели инструментов.
3. Откроется док-панель с надписью «Привет из example\_widget!»; при нажатии кнопки в панели появится вывод в консоль.

---

### 7. Шпаргалка имён

| Что                            | Где правим / кладём                     | Именование                        |
| ------------------------------ | --------------------------------------- | --------------------------------- |
| Файл виджета                   | `Toolbar_Widgets/<name>.py`             | любое (`example_widget.py`)       |
| Функция создания дока          | внутри файла                            | `<name>_dock_widget(self)`        |
| Кэш-ключ в `self.dock_widgets` | `design.py → init_dock_widgets()`       | `'example'` (совпадает с кнопкой) |
| QAction                        | `Toolbar/tool_bar.py`                   | `<name>Action`                    |
| Показ/скрытие                  | `main_window.py` (`toggle_dock_widget`) | ключ `'example'`                  |

### 8. Часто задаваемые вопросы

**Q:** Почему в `example_dock_widget` мы кладём док в `self.dock_widgets`?  
**A:** Чтобы метод `toggle_dock_widget` в `MyMainWindow` мог находить и показывать/скрывать панель, не создавая её каждый раз заново.

**Q:** Как отключить / скрыть все остальные панели, когда открывается моя?  
**A:** Ничего делать не нужно — это уже реализовано в методе `toggle_dock_widget`.

**Q:** Можно ли подключить тяжёлую бизнес-логику в отдельном модуле?  
**A:** Да. Рекомендуется создать директорию `logic/<name>/` и импортировать её из виджета.

---