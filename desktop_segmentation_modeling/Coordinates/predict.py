import warnings

warnings.filterwarnings(
    "ignore",
    message=".*pynvml package is deprecated.*",
    category=FutureWarning,
)

import torch
import numpy as np
from desktop_segmentation_modeling.Coordinates.predictmdl.models.pointnet2_cls_ssg import get_model
import desktop_segmentation_modeling.Coordinates.predictmdl.utils.pointcloud_utils as pcu
from pyntcloud import PyntCloud
import os
import pandas as pd
from tqdm import tqdm
from pathlib import Path


SPECIES_NAMES = ['Tree', 'Not_Tree']
NUM_CLASSES = len(SPECIES_NAMES)

def farthest_point_sample(xyz, npoint):
    device = xyz.device
    batchsize, ndataset, dimension = xyz.shape
    centroids = torch.zeros(batchsize, npoint, dtype=torch.long).to(device)
    distance = torch.ones(batchsize, ndataset).to(device) * 1e10
    farthest =  torch.randint(0, ndataset, (batchsize,), dtype=torch.long).to(device)
    batch_indices = torch.arange(batchsize, dtype=torch.long).to(device)
    for i in range(npoint):
        centroids[:,i] = farthest
        centroid = xyz[batch_indices, farthest, :].view(batchsize, 1, 3)
        dist = torch.sum((xyz - centroid) ** 2, -1)
        mask = dist < distance
        distance[mask] = dist[mask]
        farthest = torch.max(distance, -1)[1]
    return centroids


def get_model_path(model_name):
    # Получаем путь к файлам пакета для корректной работы при установке как библиотека
    package_dir = Path(__file__).resolve().parents[1]  # desktop_segmentation_modeling
    return str(package_dir / 'Coordinates' / 'predictmdl' / 'checkpoints' / model_name / 'models' / 'model.t7')


class StumpPredictor:
    def __init__(self, model_name):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = get_model(NUM_CLASSES, normal_channel=False).to(self.device)
        self.model.load_state_dict(torch.load(get_model_path(model_name), map_location=self.device))
        self.model.eval()

    def prepare_points(self, src):
        pc = PyntCloud.from_file(src)
        points = pc.points.loc[:, ["x", "y", "z"]].values
        points = torch.as_tensor(np.array([points]), dtype=torch.float32, device=self.device)
        centroids = farthest_point_sample(points, 2048)
        pc_sampled = points[0][centroids[0]].cpu().numpy()
        return pcu.tree_normalize(np.array([pc_sampled]))[0]

    def predict_batch(self, src_paths, batch_size=16):
        labels = []
        batch = []

        for src in src_paths:
            try:
                batch.append(self.prepare_points(src))
            except Exception as error:
                print("Exception:", str(error))
                labels.append(-1)
                continue

            if len(batch) >= batch_size:
                labels.extend(self._predict_prepared(batch))
                batch = []

        if batch:
            labels.extend(self._predict_prepared(batch))

        return labels

    def _predict_prepared(self, prepared_points):
        with torch.no_grad():
            data = torch.as_tensor(np.asarray(prepared_points), dtype=torch.float32, device=self.device)
            data = data.permute(0, 2, 1)
            logits, _ = self.model(data)
            preds = logits.max(dim=1)[1].detach().cpu().numpy()

        # Model class 1 means Not_Tree in the existing convention.
        return [0 if pred == 1 else 1 for pred in preds]


def test(src, model_name, predictor=None):
    if predictor is None:
        predictor = StumpPredictor(model_name)

    labels = predictor.predict_batch([src], batch_size=1)
    return labels[0] if labels else -1


def predict_paths(src_paths, model_name, batch_size=16):
    predictor = StumpPredictor(model_name)
    return predictor.predict_batch(src_paths, batch_size=batch_size)

def predict(path_file, model_name):
    names = []
    src_paths = []
    for filename in tqdm(os.listdir(path_file)):
        if filename.endswith('.pcd'):
            names.append(filename)
            src_paths.append(os.path.join(path_file, filename))

    labels = predict_paths(src_paths, model_name)
    bd = pd.DataFrame({"Name_tree": names, "Label": labels})
    bd.to_csv(os.path.join(path_file,'predict_' + model_name + '.csv'), index = False, sep=';')
