import sys
from datetime import datetime, timedelta
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDockWidget, QPlainTextEdit


class ConsoleWidget(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)

    def write(self, message):
        if (isinstance(message, str) and message != '\n'):
            time_now = datetime.utcnow() + timedelta(hours=3)
            time_str = time_now.strftime("%H:%M:%S")
            message_with_time = f"[{time_str}] {message}"
            self.appendPlainText(message_with_time.strip())
        elif message != '\n':
            self.appendPlainText(str(message))

    def flush(self):
        pass


class ConsoleManager:
    def __init__(self, parent=None):
        self.parent = parent
        self.consoleWidget = None

    def create_console_dock_widget(self):
        dock = QDockWidget('Консоль', self.parent)
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.consoleWidget = ConsoleWidget()
        dock.setWidget(self.consoleWidget)
        return dock

    def redirect_console_output(self):
        if self.consoleWidget:
            sys.stdout = ConsoleOutput(self.consoleWidget)
            sys.stderr = ConsoleOutput(self.consoleWidget)


class ConsoleOutput:
    def __init__(self, console_widget):
        self.console_widget = console_widget
        self.stdout = sys.stdout
        self.stderr = sys.stderr

    def write(self, message):
        self.stdout.write(message)
        self.stdout.flush()
        self.console_widget.write(message)

    def flush(self):
        self.stdout.flush()
        self.console_widget.flush()
