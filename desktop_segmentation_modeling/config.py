import sys
import os

def get_base_path():
    if getattr(sys, 'frozen', False):
        # Если приложение запущено из исполняемого файла
        return sys._MEIPASS
    else:
        # Если приложение запущено из исходного кода
        return os.path.dirname(os.path.abspath(__file__))

base_path = get_base_path()

# Настройка рендерера: "opengl" или "vulkan"
# Можно переопределить через переменную окружения RENDERER=opengl или RENDERER=vulkan
RENDERER_BACKEND = os.environ.get('RENDERER', 'opengl').lower()
