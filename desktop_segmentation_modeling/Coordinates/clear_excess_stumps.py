import os
import pandas as pd
import numpy as np
from tqdm import tqdm

from desktop_segmentation_modeling.Coordinates import predict


def count_num_files(cs):
    txt_path = os.path.join(cs.path_base, "coordinates_paths.txt") 
    file = open(txt_path, "r")
    i = 0
    while True:
        line = file.readline()
        if not line:
            break
        if line.strip() == '':
            continue
        i += 1
    file.close()
    return i

def makedirs_if_not_exist(path):
    if not os.path.exists(path):
        os.makedirs(path)


def _show_progress(cs):
    return bool(getattr(cs, "show_progress", False))


def _should_stop(should_stop):
    return bool(should_stop and should_stop())


def clear_excess_stumps(cs, should_stop=None):
    # Этот харкод тут был...
    model_name = 'int0000_7000-512-rlish-s4762'

    # Извлекаем только имя файла
    file_name = os.path.basename(cs.fname_points)
    pth = os.path.join(cs.path_base, file_name.partition('.')[0] + "_Coordinates_Merged.csv")
    df = pd.read_csv(pth, delimiter=";")

    names_col = []
    n = count_num_files(cs)
    first_n_columns = df.iloc[:, :n]
    column_names = first_n_columns.columns
    labels_matrix = np.full((df.shape[0], n), -1, dtype=np.int16)
    predictor = predict.StumpPredictor(model_name)
    predicted_count = 0
    missing_count = 0

    for i in tqdm(range(n), disable=not _show_progress(cs)):
        if _should_stop(should_stop):
            return None
        parts = column_names[i].split("_")
        parts_int = parts[-1]
        if "." in parts_int:
            parts_int = parts_int.split(".")[0]
        names_col.append("Labels_"+str(parts_int))
        path_int = os.path.join(cs.path_base, parts_int, cs.cut_data_method + '_cells', 'stumps')

        rows_to_predict = []
        paths_to_predict = []
        for j in range(df.shape[0]):
            if _should_stop(should_stop):
                return None
            value = first_n_columns.at[j, column_names[i]]
            if value != "File__Not__Found":
                path_file = os.path.join(path_int, value)
                if os.path.exists(path_file):
                    rows_to_predict.append(j)
                    paths_to_predict.append(path_file)
                else:
                    missing_count += 1
                    labels_matrix[j, i] = -3
            elif value == "File__Not__Found":
                labels_matrix[j, i] = -2
            else:
                print("Ошибка: некорректное имя файла кандидата")
                break

        if paths_to_predict:
            predicted_labels = predictor.predict_batch(paths_to_predict)
            if _should_stop(should_stop):
                return None
            for row_idx, label in zip(rows_to_predict, predicted_labels):
                labels_matrix[row_idx, i] = label
            predicted_count += len(paths_to_predict)

    df_labels = pd.DataFrame(data=labels_matrix, columns=names_col)
    df_result = pd.concat([df, df_labels], axis=1)

    # Извлекаем только имя файла
    file_name = os.path.basename(cs.fname_points)
    save_pth = os.path.join(cs.path_base, file_name.partition('.')[0] + "_Clear_Excess.csv")
    save_pth = os.path.join(cs.path_base, save_pth)
    if _should_stop(should_stop):
        return None
    df_result.to_csv(save_pth, index = False, sep=';')
    print(f"Классификация кандидатов: обработано {predicted_count}, пропущено {missing_count}.")

    return save_pth
