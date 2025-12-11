import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

# Пути к CSV файлам
csv_path_vbo = "system_resource_log_vbo.csv"
csv_path_no_vbo = "system_resource_log.csv"

def load_and_prepare(csv_path):
    df = pd.read_csv(csv_path)
    for col in ["cpu_percent", "ram_used_mb", "gpu_percent", "vram_used_mb"]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

df_vbo = load_and_prepare(csv_path_vbo)
df_no_vbo = load_and_prepare(csv_path_no_vbo)

min_len = min(len(df_vbo), len(df_no_vbo))
df_vbo = df_vbo.iloc[:min_len].copy()
df_no_vbo = df_no_vbo.iloc[:min_len].copy()
df_vbo["step"] = range(min_len)
df_no_vbo["step"] = range(min_len)

plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['font.weight'] = 'bold'
plt.rcParams['font.size'] = 20

font_prop = FontProperties(family='Times New Roman', weight='bold', size=20)
label_fontsize = 28
tick_fontsize = 24

names = [
    ("CPU (%)", "CPU с VBO", "CPU без VBO", "tab:red", "tab:pink", df_vbo["cpu_percent"], df_no_vbo["cpu_percent"]),
    ("RAM (MB)", "RAM с VBO", "RAM без VBO", "tab:blue", "tab:cyan", df_vbo["ram_used_mb"], df_no_vbo["ram_used_mb"]),
    ("GPU (%)", "GPU с VBO", "GPU без VBO", "tab:green", "lightgreen", df_vbo["gpu_percent"], df_no_vbo["gpu_percent"]),
    ("VRAM (MB)", "VRAM с VBO", "VRAM без VBO", "tab:purple", "violet", df_vbo["vram_used_mb"], df_no_vbo["vram_used_mb"])
]

for ylabel, label1, label2, color1, color2, data1, data2 in names:
    plt.figure(figsize=(14, 6))  # отдельное окно, ширина/высота по желанию
    plt.plot(df_vbo["step"], data1, label=label1, color=color1)
    plt.plot(df_no_vbo["step"], data2, label=label2, color=color2)
    plt.xlabel("Шаг (с)", fontsize=label_fontsize, fontname='Times New Roman', fontweight='bold')
    plt.ylabel(ylabel, fontsize=label_fontsize, fontname='Times New Roman', fontweight='bold')
    plt.legend(loc="upper right", prop=font_prop)
    plt.grid(True)
    plt.tick_params(axis='both', labelsize=tick_fontsize)
    plt.tight_layout()
    plt.show()
