import warnings

warnings.filterwarnings(
    "ignore",
    message=".*pynvml package is deprecated.*",
    category=FutureWarning,
)
warnings.filterwarnings(
    "ignore",
    message=".*nopython.*",
    category=Warning,
    module=r"pyntcloud\.utils\.numba",
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


def infer_sample_count(model_name):
    if "-512-" in model_name:
        return 512
    if "-1024-" in model_name or "s1024" in model_name:
        return 1024
    return 2048

def _deterministic_fps_start_indices(xyz, strategy=0):
    """Fixed FPS seeds for reproducible inference (strategy indexes rotate per vote)."""
    batchsize, _, _ = xyz.shape
    strategies = (
        lambda cloud: torch.argmin(cloud[:, :, 2], dim=1),
        lambda cloud: torch.argmax(cloud[:, :, 2], dim=1),
        lambda cloud: torch.argmax(torch.sum((cloud - cloud.mean(dim=1, keepdim=True)) ** 2, dim=-1), dim=1),
        lambda cloud: torch.argmin(cloud[:, :, 0], dim=1),
        lambda cloud: torch.argmax(cloud[:, :, 1], dim=1),
    )
    pick = strategies[strategy % len(strategies)]
    return pick(xyz)


def farthest_point_sample(xyz, npoint, start_indices=None):
    device = xyz.device
    batchsize, ndataset, _ = xyz.shape
    centroids = torch.zeros(batchsize, npoint, dtype=torch.long).to(device)
    distance = torch.ones(batchsize, ndataset).to(device) * 1e10
    if start_indices is None:
        farthest = _deterministic_fps_start_indices(xyz, strategy=0)
    else:
        farthest = start_indices.to(device)
    batch_indices = torch.arange(batchsize, dtype=torch.long).to(device)
    for i in range(npoint):
        centroids[:, i] = farthest
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
        self.sample_count = infer_sample_count(model_name)
        self.model = get_model(NUM_CLASSES, normal_channel=False).to(self.device)
        self.model.load_state_dict(torch.load(get_model_path(model_name), map_location=self.device))
        self.model.eval()

    def prepare_points(self, src):
        pc = PyntCloud.from_file(src)
        points = pc.points.loc[:, ["x", "y", "z"]].values
        return self.prepare_points_array(points)

    def prepare_points_array(self, points, fps_strategy=0):
        points = np.asarray(points, dtype=np.float32)
        if points.ndim != 2 or points.shape[1] < 3 or len(points) == 0:
            raise ValueError("Ожидался непустой массив точек формы (N, 3)")
        points = points[:, :3]
        points = torch.as_tensor(np.array([points]), dtype=torch.float32, device=self.device)
        start_indices = _deterministic_fps_start_indices(points, strategy=fps_strategy)
        centroids = farthest_point_sample(points, self.sample_count, start_indices=start_indices)
        pc_sampled = points[0][centroids[0]].cpu().numpy()
        return pcu.tree_normalize(np.array([pc_sampled]))[0]

    def predict_points(self, points, votes=5):
        return self.predict_points_detailed(points, votes=votes)["label"]

    def predict_points_detailed(self, points, votes=5):
        if votes <= 1:
            prepared_points = self.prepare_points_array(points, fps_strategy=0)
            labels = self._predict_prepared([prepared_points])
            label = labels[0] if labels else -1
            tree_votes = 1 if label == 1 else 0
            return {
                "label": label,
                "tree_votes": tree_votes,
                "total_votes": 1,
                "confidence": float(tree_votes),
            }

        labels = []
        for vote_idx in range(votes):
            prepared_points = self.prepare_points_array(points, fps_strategy=vote_idx)
            labels.extend(self._predict_prepared([prepared_points]))

        tree_votes = sum(label == 1 for label in labels)
        total_votes = len(labels)
        final_label = 1 if tree_votes > total_votes / 2 else 0
        return {
            "label": final_label,
            "tree_votes": tree_votes,
            "total_votes": total_votes,
            "confidence": tree_votes / total_votes if total_votes else 0.0,
        }

    def predict_batch(self, src_paths, batch_size=16):
        labels = [-1] * len(src_paths)
        batch = []
        batch_indices = []

        for index, src in enumerate(src_paths):
            try:
                batch.append(self.prepare_points(src))
                batch_indices.append(index)
            except Exception as error:
                print("Exception:", str(error))
                continue

            if len(batch) >= batch_size:
                for batch_index, label in zip(batch_indices, self._predict_prepared(batch)):
                    labels[batch_index] = label
                batch = []
                batch_indices = []

        if batch:
            for batch_index, label in zip(batch_indices, self._predict_prepared(batch)):
                labels[batch_index] = label

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
