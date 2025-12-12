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