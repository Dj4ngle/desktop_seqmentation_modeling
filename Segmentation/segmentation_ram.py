import pandas as pd
import os
from scipy.spatial.distance import cdist
from settings.seg_settings import SS
from classes.RAM import RAM
import numpy as np

def makedirs_if_not_exist(path):
    if not os.path.exists(path):
        os.makedirs(path)

def segmentation_ram(ss):

    path_file_save = os.path.join(ss.path_base, ss.step1_folder_name, ss.step2_folder_name)
    makedirs_if_not_exist(path_file_save)

    file_name_coord = os.path.join(ss.path_base, ss.csv_name_coord)
    path_file = os.path.join(ss.path_base, ss.step1_folder_name)

    label = pd.read_csv(file_name_coord, sep = ';')
    coords = np.asarray(label[["X", "Y"]], dtype=np.float64)

    path_csv = os.path.join(ss.path_base, ss.fname_points.split(".")[0] + "_binding.csv")
    df1 = pd.read_csv(path_csv, sep = ';')

    file_name_coord = os.path.join(ss.path_base, ss.csv_name_coord)
    df2 = pd.read_csv(file_name_coord, sep = ';')

    combined_dataframe = df2.merge(df1, on= ('X', 'Y'))
    combined_dataframe.to_csv(os.path.join(ss.path_base, ss.fname_points.split(".")[0] + "_res.csv"), index = False, sep=';') 

    print("First step clustering (accumulating RAM)...")

    obj_ram = RAM(path_file = path_file, coordinates = coords, combined_dataframe = combined_dataframe)
    obj_ram.accumulating()

    print("Second step clustering (using RAM)...")
    obj_ram.exploitation(path_file_save)
