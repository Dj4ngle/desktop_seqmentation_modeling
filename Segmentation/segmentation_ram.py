import pandas as pd
import os
from classes.RAM import RAM
import numpy as np

def makedirs_if_not_exist(path):
    if not os.path.exists(path):
        os.makedirs(path)

def segmentation_ram(ss, tr_val, multiplier):

    path_file_save = os.path.join(ss.path_base, ss.step1_folder_name, ss.step2_folder_name)
    makedirs_if_not_exist(path_file_save)

    file_name_coord = os.path.join(ss.path_base, ss.csv_name_coord)
    path_file = os.path.join(ss.path_base, ss.step1_folder_name)

    label = pd.read_csv(file_name_coord, sep = ';')

    threshold = tr_val
    print(f"Threshold value: {threshold}")

    # Пока захардкожены названия полей
    def meets_criteria(row, threshold, count_required):
        count = sum(row[["Labels_int7000", "Labels_int5000", "Labels_int1000"]] >= threshold)
        return count >= count_required

    count_required = multiplier
    label = label[label.apply(meets_criteria, axis=1, threshold=threshold, count_required=count_required)]

    print(f"Number of points after filtering: {len(label)}")
    if len(label) == 0:
        print("No points meet the filtering criteria.")
        return []

    coords = np.asarray(label[["X", "Y"]], dtype=np.float64)

    fname_root = os.path.splitext(os.path.basename(ss.fname_points))[0]
    path_csv = os.path.join(ss.path_base, f"{fname_root}_binding.csv")
    df1 = pd.read_csv(path_csv, sep = ';')

    file_name_coord = os.path.join(ss.path_base, ss.csv_name_coord)
    df2 = pd.read_csv(file_name_coord, sep = ';')

    fname_root = os.path.splitext(os.path.basename(ss.fname_points))[0]
    res_csv = os.path.join(ss.path_base, f"{fname_root}_res.csv")

    combined_dataframe = df2.merge(df1, on= ('X', 'Y'))
    combined_dataframe.to_csv(res_csv, index=False, sep=';')

    print("First step clustering (accumulating RAM)...")

    obj_ram = RAM(path_file = path_file, coordinates = coords, combined_dataframe = combined_dataframe)
    obj_ram.accumulating()

    print("Second step clustering (using RAM)...")
    obj_ram.exploitation(path_file_save)
    return []
