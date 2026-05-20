import pandas as pd
import os
from desktop_segmentation_modeling.classes.RAM import RAM
import numpy as np

def makedirs_if_not_exist(path):
    if not os.path.exists(path):
        os.makedirs(path)


def _show_progress(ss):
    return bool(getattr(ss, "show_progress", False))


def _should_stop(should_stop):
    return bool(should_stop and should_stop())


def segmentation_ram(ss, tr_val, multiplier, should_stop=None):

    path_file_save = os.path.join(ss.path_base, ss.step1_folder_name, ss.step2_folder_name)
    makedirs_if_not_exist(path_file_save)

    file_name_coord = os.path.join(ss.path_base, ss.csv_name_coord)
    path_file = os.path.join(ss.path_base, ss.step1_folder_name)

    label = pd.read_csv(file_name_coord, sep = ';')
    if _should_stop(should_stop):
        return []

    threshold = tr_val

    # Пока захардкожены названия полей
    def meets_criteria(row, threshold, count_required):
        count = sum(row[["Labels_int7000", "Labels_int5000", "Labels_int1000"]] >= threshold)
        return count >= count_required

    count_required = multiplier
    label = label[label.apply(meets_criteria, axis=1, threshold=threshold, count_required=count_required)]

    print(f"Сегментация RAM: кандидатов после фильтра {len(label)}.")
    if len(label) == 0:
        print("Сегментация RAM пропущена: нет подходящих кандидатов.")
        return []

    if _should_stop(should_stop):
        return []

    coords = np.asarray(label[["X", "Y"]], dtype=np.float64)

    fname_root = os.path.splitext(os.path.basename(ss.fname_points))[0]
    path_csv = os.path.join(ss.path_base, f"{fname_root}_binding.csv")
    df1 = pd.read_csv(path_csv, sep = ';')
    if _should_stop(should_stop):
        return []

    file_name_coord = os.path.join(ss.path_base, ss.csv_name_coord)
    df2 = pd.read_csv(file_name_coord, sep = ';')

    fname_root = os.path.splitext(os.path.basename(ss.fname_points))[0]
    res_csv = os.path.join(ss.path_base, f"{fname_root}_res.csv")

    combined_dataframe = df2.merge(df1, on= ('X', 'Y'))
    combined_dataframe.to_csv(res_csv, index=False, sep=';')
    if _should_stop(should_stop):
        return []

    print("Сегментация RAM: накопление дополнительных точек...")

    obj_ram = RAM(
        path_file=path_file,
        coordinates=coords,
        combined_dataframe=combined_dataframe,
        show_progress=_show_progress(ss),
        should_stop=should_stop,
    )
    if not obj_ram.accumulating():
        return []
    if _should_stop(should_stop):
        return []

    print("Сегментация RAM: сохранение уточненных деревьев...")
    out_files = obj_ram.exploitation(path_file_save)
    if _should_stop(should_stop):
        return out_files
    print(f"Сегментация RAM: сохранено {len(out_files)} файлов.")
    return out_files
