import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from tqdm import tqdm
import os
from scipy.spatial.distance import cdist
from classes.PCD_TREE import PCD_TREE
from classes.PCD_UTILS import PCD_UTILS
from classes.PCD import PCD

def makedirs_if_not_exist(path):
    if not os.path.exists(path):
        os.makedirs(path)

def clustering(pc_tree):
    P = pd.DataFrame(pc_tree.points, columns = ['X','Y','Z'])
    X = np.asarray(P)
    if pc_tree.points.shape[0]<100000:
        clustering = DBSCAN(eps=1.25, min_samples=25).fit(X)
        labels=clustering.labels_
    else:
        labels = np.zeros(pc_tree.points.shape[0])
    return labels

def segmentation_clear(ss, tr_val, multiplier):
    path_file_save = os.path.join(ss.path_base, ss.step1_folder_name, ss.step2_folder_name, ss.step3_folder_name)
    makedirs_if_not_exist(path_file_save)

    fname_root = os.path.splitext(os.path.basename(ss.fname_points))[0]
    path_csv = os.path.join(ss.path_base, f"{fname_root}_res.csv")
    print(path_csv)

    path_file = os.path.join(ss.path_base, ss.step1_folder_name, ss.step2_folder_name)
    df = pd.read_csv(path_csv, sep=';')

    def meets_criteria(row, threshold, count_required):
        count = sum(row[["Labels_int7000", "Labels_int5000", "Labels_int1000"]] >= threshold)
        return count >= count_required

    count_required = multiplier
    df = df[df.apply(meets_criteria, axis=1, threshold=tr_val, count_required=count_required)]

    print(f"Number of points after filtering: {len(df)}")
    if len(df) == 0:
        print("No points meet the filtering criteria.")
        return []

    inum=0

    # Создаём список созданных файлов
    out_files = []

    # Assuming this is part of your segmentation_clear function
    for fname in tqdm(os.listdir(path_file)):
        if fname.endswith('.pcd'):
            inum += 1
            if inum < ss.first_num:
                continue

            try:
                pc_tree = PCD_TREE()
                pc_tree.open(os.path.join(path_file, fname))

                labels = clustering(pc_tree)

                min_z_values = []
                for i in np.unique(labels):
                    if i > -1:
                        idx_layer = np.where(labels == i)
                        i_data = pc_tree.points[idx_layer]
                        index = i_data[:, 2].argmin()
                        min_z_value = i_data[index]
                        min_z_values.append(min_z_value)
                min_z_values = np.asarray(min_z_values)

                idx_labels = np.where(min_z_values[:, 2] < pc_tree.points.min(axis=0)[2] + 1)
                min_z_values = min_z_values[idx_labels]

                centers_labels = []
                for i in range(min_z_values.shape[0]):
                    idx_layer = np.where(labels == i)
                    i_data = pc_tree.points[idx_layer]
                    center = PCD_UTILS.center_m(i_data[:, 0:2])
                    centers_labels.append(center)
                centers_labels = np.asarray(centers_labels)

                # Check if we have enough centers for clustering
                if centers_labels.shape[0] < 2:
                    print(
                        f"Not enough centers for clustering for file {fname}. Found {centers_labels.shape[0]} centers.")
                    continue  # Skip this file or handle it as needed

                x_value = df.loc[df['Name_tree'] == fname, 'X'].values[0]
                y_value = df.loc[df['Name_tree'] == fname, 'Y'].values[0]
                main_center = [x_value, y_value]

                distances = cdist(centers_labels, [main_center])
                min_distance_index = np.argmin(distances)

                pc_result = PCD(pc_tree.points, pc_tree.intensity)
                idx_l = np.where(labels == min_distance_index)
                pc_result.index_cut(idx_l)

                filename = f"{fname}"
                if pc_result.points.shape[0] > 1:
                    file_name_data_out = os.path.join(path_file_save, filename)
                    pc_result.save(file_name_data_out)

                    out_files.append(file_name_data_out)
            except Exception as e:
                print(f"Error processing file {fname}: {e}")

    return out_files
