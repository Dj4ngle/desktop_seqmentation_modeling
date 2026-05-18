import sys
from datetime import datetime, timedelta
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QDockWidget, QPlainTextEdit


class ConsoleWriter(QObject):
    """Вспомогательный класс для потокобезопасной записи в консоль"""
    message_signal = pyqtSignal(str)
    
    def __init__(self, console_widget):
        super().__init__()
        self.console_widget = console_widget
        self.message_signal.connect(self._write_message)
    
    def _write_message(self, message):
        """Слот для записи сообщения в консоль (выполняется в главном потоке)"""
        if (isinstance(message, str) and message != '\n'):
            time_now = datetime.utcnow() + timedelta(hours=3)
            time_str = time_now.strftime("%H:%M:%S")
            message_with_time = f"[{time_str}] {message}"
            self.console_widget.appendPlainText(message_with_time.strip())
        elif message != '\n':
            self.console_widget.appendPlainText(str(message))


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
        # Используем потокобезопасный метод write консоли
        self.console_widget.write(message)

    def flush(self):
        self.stdout.flush()
        self.console_widget.flush()
