import psutil
import pynvml
import csv
import time
from datetime import datetime
import os

def initialize_gpu():
    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)  # Первая видеокарта
        return handle
    except Exception as e:
        print("❌ Не удалось инициализировать NVML:", e)
        return None

def collect_metrics(gpu_handle):
    # CPU и RAM по всей системе
    cpu_percent = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()
    ram_used = (ram.total - ram.available) / (1024 ** 2)  # в MB

    # GPU
    gpu_percent = None
    vram_used = None

    if gpu_handle:
        try:
            util = pynvml.nvmlDeviceGetUtilizationRates(gpu_handle)
            mem = pynvml.nvmlDeviceGetMemoryInfo(gpu_handle)
            vram_used = mem.used / (1024 ** 2)
            gpu_percent = util.gpu
        except Exception as e:
            print("⚠️ Ошибка чтения данных GPU:", e)

    return {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "cpu_percent": round(cpu_percent, 2),
        "ram_used_mb": round(ram_used, 2),
        "gpu_percent": round(gpu_percent, 2) if gpu_percent is not None else "None",
        "vram_used_mb": round(vram_used, 2) if vram_used is not None else "None"
    }

def write_to_csv(filename, data, write_header):
    file_exists = os.path.exists(filename)
    with open(filename, "a", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=data.keys())
        if write_header and not file_exists:
            writer.writeheader()
        writer.writerow(data)

def main():
    output_file = "system_resource_log.csv"
    gpu_handle = initialize_gpu()

    print("📊 Мониторинг начат. Для остановки нажмите Ctrl+C.")
    try:
        while True:
            metrics = collect_metrics(gpu_handle)

            # Печать в консоль
            print(f"{metrics['timestamp']} | "
                  f"CPU: {metrics['cpu_percent']}% | "
                  f"RAM: {metrics['ram_used_mb']} MB | "
                  f"GPU: {metrics['gpu_percent']}% | "
                  f"VRAM: {metrics['vram_used_mb']} MB")

            # Запись в CSV
            write_to_csv(output_file, metrics, write_header=True)

            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Мониторинг завершён.")
    finally:
        if gpu_handle:
            pynvml.nvmlShutdown()

if __name__ == "__main__":
    main()
