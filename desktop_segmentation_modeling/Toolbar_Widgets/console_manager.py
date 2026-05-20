import sys
from datetime import datetime, timedelta
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QDockWidget, QPlainTextEdit, QVBoxLayout, QWidget


class ConsoleWriter(QObject):
    """Вспомогательный класс для потокобезопасной записи в консоль"""
    message_signal = pyqtSignal(str)
    
    def __init__(self, console_widget):
        super().__init__()
        self.console_widget = console_widget
        self.message_signal.connect(self._write_message)
    
    def _write_message(self, message):
        """Слот для записи сообщения в консоль (выполняется в главном потоке)"""
        if message == '\n':
            return

        if not isinstance(message, str):
            self.console_widget.appendPlainText(str(message))
            return

        normalized_message = message.replace('\r', '\n')
        for line in normalized_message.splitlines():
            line = line.strip()
            if not line:
                continue
            time_now = datetime.utcnow() + timedelta(hours=3)
            time_str = time_now.strftime("%H:%M:%S")
            self.console_widget.appendPlainText(f"[{time_str}] {line}")


class ConsoleWidget(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(2000)
        self.writer = ConsoleWriter(self)
        self._pending_messages = []
        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(75)
        self._flush_timer.timeout.connect(self._flush_pending_messages)

    def write(self, message):
        self._pending_messages.append(message)
        if not self._flush_timer.isActive():
            self._flush_timer.start()

    def flush(self):
        self._flush_pending_messages()

    def _flush_pending_messages(self):
        if not self._pending_messages:
            self._flush_timer.stop()
            return

        message = ''.join(self._pending_messages)
        self._pending_messages = []
        self.writer.message_signal.emit(message)


class ConsolePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.console_widget = ConsoleWidget(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        layout.addWidget(self.console_widget)

    def set_progress(self, value, message=None):
        pass

    def reset_progress(self, message="Готово"):
        pass


class ConsoleManager:
    def __init__(self, parent=None):
        self.parent = parent
        self.consolePanel = None
        self.consoleWidget = None

    def create_console_dock_widget(self):
        dock = QDockWidget('Консоль', self.parent)
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.consolePanel = ConsolePanel()
        self.consoleWidget = self.consolePanel.console_widget
        dock.setWidget(self.consolePanel)
        return dock

    def redirect_console_output(self):
        if self.consoleWidget:
            sys.stdout = ConsoleOutput(self.consoleWidget)
            sys.stderr = ConsoleOutput(self.consoleWidget)

    def set_progress(self, value, message=None):
        if self.consolePanel:
            self.consolePanel.set_progress(value, message)

    def reset_progress(self, message="Готово"):
        if self.consolePanel:
            self.consolePanel.reset_progress(message)


class ConsoleOutput:
    def __init__(self, console_widget):
        self.console_widget = console_widget
        self.stdout = sys.stdout
        self.stderr = sys.stderr

    def write(self, message):
        self.stdout.write(message)
        self.stdout.flush()
        # Используем потокобезопасный метод write консоли
        self.console_widget.write(message)

    def flush(self):
        self.stdout.flush()
        self.console_widget.flush()
