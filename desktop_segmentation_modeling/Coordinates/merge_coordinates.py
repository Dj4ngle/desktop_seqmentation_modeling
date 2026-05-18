import os
import pandas as pd
import numpy as np
from scipy.spatial import cKDTree

def makedirs_if_not_exist(path):
    if not os.path.exists(path):
        os.makedirs(path)

def merge(file1, file2, iter, names_col, array):
    n_col_name = 0 + iter
    n_col_diam = (iter+1)*2

    eps = 0.25
    array = file1.to_numpy(dtype=object)
    XY = array[:, iter:iter + 2].astype(np.float64)

    added_column_name = np.full(array.shape[0], "File__Not__Found", dtype=object)
    added_column_diameter = np.full(array.shape[0], 0.0, dtype=np.float32)

    file2_values = file2.to_numpy(dtype=object)
    file2_xy = file2_values[:, 1:3].astype(np.float64)
    matched_file2 = np.zeros(file2_values.shape[0], dtype=bool)

    if XY.shape[0] > 0 and file2_xy.shape[0] > 0:
        tree = cKDTree(XY)
        distances, indices = tree.query(file2_xy, distance_upper_bound=eps)
        valid_matches = np.isfinite(distances) & (indices < XY.shape[0])

        for file2_idx, array_idx in enumerate(indices[valid_matches]):
            row = file2_values[np.flatnonzero(valid_matches)[file2_idx]]
            added_column_name[array_idx] = row[0]
            added_column_diameter[array_idx] = row[3]

        matched_file2[valid_matches] = True

    array = np.insert(array, n_col_diam, added_column_diameter, axis=1)
    array = np.insert(array, n_col_name, added_column_name, axis=1)
   
    rows_to_add = []
    for row, is_matched in zip(file2_values, matched_file2):
        if not is_matched:
            added_row = ["File__Not__Found",row[0],row[1],row[2],0.0,row[3]]
            if iter > 1:
                added_row.insert((iter)*2, 0.0)
                added_row.insert(iter-1, "File__Not__Found")
            rows_to_add.append(added_row)

    if rows_to_add:
        array = np.vstack([array, np.asarray(rows_to_add, dtype=object)])

    df = pd.DataFrame(data = array, columns=names_col)
    df = df.dropna()
    df = df[(df.X != 'nan')]
    df = df[(df.Y != 'nan')]
    return df

def init_merge_file(cs):
    txt_path = os.path.join(cs.path_base, "coordinates_paths.txt") 
    file = open(txt_path, "r")
    i = 0
    iter = 0
    df = None  #Инициализируем df заранее

    while True:
        line = file.readline()
        if not line:
            break
        file_name = line.strip()
        if file_name == '':
            continue
        file1_path = file_name
        splt_fn = file_name.split(sep="_")[-1]
        splt_fn = splt_fn.split(sep=".")[0]

        if i == 0:
            names_col = ["Name_stump_" + splt_fn, "X", "Y", "Diameter_" + splt_fn]
        if i > 0:
            names_col.insert((iter+2)*2, "Diameter_" + splt_fn)
            names_col.insert(iter+1, "Name_stump_" + splt_fn)
            if i == 1:
                array = ['n',0,0,0]
            else:
                array.insert(i,'n')
                array.insert(i*2+1,0)
       
        i+=1
        if i >= 2 :
            iter += 1
            if iter == 1:
                file1 = pd.read_csv(file2_path, delimiter=";")
                file2 = pd.read_csv(file1_path, delimiter=";")
            else:
                file1 = df
                file2 = pd.read_csv(file1_path, delimiter=";")
            df = merge(file1, file2, iter, names_col, [array])
        
        file2_path = file1_path

    file.close()

    if df is None:  # Если df так и не был создан, создаём пустой DataFrame
        df = pd.DataFrame(columns=["Name_stump", "X", "Y", "Diameter"])

    return df

def merge_coordinates(cs):
    df = init_merge_file(cs)

    # Извлекаем только имя файла
    file_name = os.path.basename(cs.fname_points)
    save_pth = os.path.join(cs.path_base, file_name.partition('.')[0] + "_Coordinates_Merged.csv")
    save_pth = os.path.join(cs.path_base, save_pth)
    df.to_csv(save_pth, index = False, sep=';')
