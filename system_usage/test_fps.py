import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

# Пути к двум CSV файлам
csv_path_vbo = "metrics_log_vbo.csv"
csv_path_no_vbo = "metrics_log.csv"

def load_and_prepare(csv_path):
    df = pd.read_csv(csv_path)
    df["FPS"] = pd.to_numeric(df["FPS"], errors="coerce")
    df["RenderTime_ms"] = pd.to_numeric(df["RenderTime_ms"], errors="coerce")
    df.dropna(subset=["FPS", "RenderTime_ms"], inplace=True)
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
    ("FPS", "FPS с VBO", "FPS без VBO", "tab:blue", "tab:cyan", df_vbo["FPS"], df_no_vbo["FPS"]),
    ("Время отрисовки (мс)", "Render Time с VBO", "Render Time без VBO", "tab:orange", "gold", df_vbo["RenderTime_ms"], df_no_vbo["RenderTime_ms"])
]

for ylabel, label1, label2, color1, color2, data1, data2 in names:
    plt.figure(figsize=(14, 6))  # отдельное окно для каждого графика
    plt.plot(df_vbo["step"], data1, label=label1, color=color1)
    plt.plot(df_no_vbo["step"], data2, label=label2, color=color2)
    plt.xlabel("Шаг (с)", fontsize=label_fontsize, fontname='Times New Roman', fontweight='bold')
    plt.ylabel(ylabel, fontsize=label_fontsize, fontname='Times New Roman', fontweight='bold')
    plt.legend(loc="upper right", prop=font_prop)
    plt.grid(True)
    plt.tick_params(axis='both', labelsize=tick_fontsize)
    plt.tight_layout()
    plt.show()
