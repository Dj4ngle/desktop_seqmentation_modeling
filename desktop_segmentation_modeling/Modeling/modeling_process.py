import os
import sys
import json
import warnings

import numpy as np
import pywavefront

from desktop_segmentation_modeling.Modeling.modeler import modeler
from desktop_segmentation_modeling.Modeling.modeler2 import modeler2


RESULT_PREFIX = "DSM_MODELING_RESULT="


def build_model_cache(obj_path):
    scene = pywavefront.Wavefront(obj_path, collect_faces=True)
    vertices = []
    for _, mesh in scene.meshes.items():
        for face in mesh.faces:
            vertices.extend([scene.vertices[index] for index in face])

    points = np.asarray(vertices, dtype=np.float32)
    if len(points) > 0:
        points = points - np.mean(points, axis=0)

    cache_path = obj_path + ".display.npz"
    np.savez(cache_path, points=points)
    return cache_path


def main():
    warnings.filterwarnings("ignore", category=FutureWarning, module=r"torch\.cuda")

    if len(sys.argv) < 6:
        print("Ошибка: недостаточно аргументов для моделирования.", file=sys.stderr)
        return 1

    method = sys.argv[1]
    slider1 = int(sys.argv[2])
    slider2 = int(sys.argv[3])
    slider3 = int(sys.argv[4])
    selected_files = sys.argv[5:]
    modeling_func = modeler if method == "BPA" else modeler2

    for file_path in selected_files:
        base_name, _ = os.path.splitext(file_path)
        obj_path = base_name + ".obj"
        result_path = modeling_func(file_path, obj_path, slider1, slider2, slider3)
        if result_path:
            cache_path = build_model_cache(result_path)
            payload = {"obj_path": result_path, "cache_path": cache_path}
            print(f"{RESULT_PREFIX}{json.dumps(payload, ensure_ascii=False)}", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
