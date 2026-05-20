import numpy as np
from sklearn import cluster
import os
# from pycobra.visualisation import voronoi_finite_polygons_2d
from scipy.spatial import Voronoi
from shapely.geometry import Polygon
from .PCD import PCD
from .PCD_AREA import PCD_AREA
from .PCD_UTILS import PCD_UTILS
from tqdm import tqdm
from shapely.ops import unary_union
import matplotlib.pyplot as plt
import random
# from matplotlib.collections import PatchCollection

class VOR_TES(PCD):
    """ Clustering with Voronoi Tesselations """
    def __init__(self, points, intensity, algo = 'birch', n_clusters = 8, intensity_cut = 20000,
                 verbose=False, show_progress=False, should_stop=None):
        super().__init__(points, intensity)
        self.n_clusters = n_clusters
        self.verbose = verbose
        self.show_progress = show_progress
        self.should_stop = should_stop

        pc = PCD(points = self.points, intensity = self.intensity)
        idx_labels = np.where(pc.intensity>=intensity_cut)
        pc.index_cut(idx_labels)
        self.pts = pc.points[:,0:2]

        if algo == 'birch':
            self.algo = cluster.Birch(n_clusters=n_clusters)
        elif algo == 'spectral':
            self.algo = cluster.SpectralClustering(n_clusters=n_clusters, eigen_solver='arpack', affinity="nearest_neighbors")
        elif algo == 'kmeans':
            self.algo = cluster.KMeans(n_clusters=n_clusters)
        else:
            raise Exception("There is no such algorithm. Choose from existing: 'birch', 'spectral', 'kmeans'")

        if self.verbose:
            print(f'Starting clustering via {algo} algorithm ...')
        if not self._should_stop():
            self.algo.fit(self.pts)

    def _should_stop(self):
        return bool(self.should_stop and self.should_stop())

    def plot_cluster_voronoi(self):
        vor = Voronoi(self.pts)
        regions, vertices = PCD_UTILS.voronoi_finite_polygons_2d(vor)
        fig, ax = plt.subplots()
        plot = ax.scatter([], [])
        indice = 0
        for region in regions:
            # ax.plot(self.pts[:,0][indice], self.pts[:,1][indice], 'ko')
            polygon = vertices[region]
            color = self.algo.labels_[indice]
            random.seed(color)
            clr = [random.random(), random.random(), random.random()]
            ax.fill(*zip(*polygon), alpha=0.4, color=clr, label="")
            indice += 1
        ax.axis('equal')
        plt.xlim(vor.min_bound[0] - 0.1, vor.max_bound[0] + 0.1)
        plt.ylim(vor.min_bound[1] - 0.1, vor.max_bound[1] + 0.1)
        plt.show()


    def select_clusters(self, path_folder):
        i = 0
        pc = PCD_AREA(points = self.points, intensity = self.intensity)
        saved_count = 0
        for filename in tqdm(sorted(os.listdir(path_folder)), disable=not self.show_progress):
            if self._should_stop():
                return saved_count
            if filename.endswith('.csv'):
                fname_brd = os.path.join(path_folder, filename) 
                border = np.loadtxt(fname_brd, delimiter=',', dtype=np.float32)
                pc_part = pc.poly_cut(border, returned = 'area')
                if self._should_stop():
                    return saved_count

                # dt_pc = np.array(np.c_[pc.points, pc.intensity], dtype=np.float32)
                # dt_part = np.array(np.c_[pc_part.points, pc_part.intensity], dtype=np.float32)
                # points_cell_set = set(tuple(p) for p in dt_part)
                # pc_filtered = np.array([p for p in dt_pc if tuple(p) not in points_cell_set])
                # try:
                #     pc.points = pc_filtered[:,:3]
                #     pc.intensity = pc_filtered[:,3]
                # except:
                #     pass

                fname_part = os.path.join(path_folder, filename.partition('.csv')[0] + '.pcd') 
                if pc_part.points.shape[0]>1:
                    pc_part.save(fname_part)
                    saved_count += 1
                i += 1
        return saved_count


    def select_borders(self, path_folder, shp_poly, verbose = False):
        if self.verbose:
            print(f'Starting create Voronoi partitions ...')
        if self._should_stop():
            return 0
        vor = Voronoi(self.pts)
        regions, vertices = PCD_UTILS.voronoi_finite_polygons_2d(vor)
        indice = 0
        mp = [[]]
        for i in range(self.n_clusters):
            mp.append([])
        if verbose:
            self.plot_cluster_voronoi()
        with tqdm(total=self.pts.shape[0], disable=not self.show_progress) as pbar:
            for region in regions:
                if self._should_stop():
                    return 0
                polygon = vertices[region]
                label = self.algo.labels_[indice]
                poly = Polygon(polygon)
                for i in range(self.n_clusters):
                    if label == i:
                        mp[i].append(poly)
                        break
                indice += 1
                pbar.update(1)
        
        if self.verbose:
            print(f'Starting saving borders in .csv files ...')

        border_count = 0
        for i in tqdm(range(self.n_clusters), disable=not self.show_progress):
            if self._should_stop():
                return border_count
            multi_poly = unary_union(mp[i])

            shp_ply = Polygon(shp_poly)
            cut_poly = multi_poly.intersection(shp_ply)

            if verbose:
                fig, axs = plt.subplots()
                axs.set_aspect('equal', 'datalim')
                for geom in cut_poly.geoms:    
                    xs, ys = geom.exterior.xy    
                    axs.fill(xs, ys, alpha=0.5, fc='r', ec='none')
                plt.show()

                fig, axs = plt.subplots()
                axs.set_aspect('equal', 'datalim')   
                xs, ys = multi_poly.exterior.xy    
                axs.fill(xs, ys, alpha=0.5, fc='b', ec='none')
                xs, ys = shp_ply.exterior.xy    
                axs.fill(xs, ys, alpha=0.5, fc='g', ec='none')
                plt.show()
            
            if str(type(cut_poly)) == "<class 'shapely.geometry.polygon.Polygon'>":
                polygon_xy = np.asarray(cut_poly.exterior.coords.xy)       
                polygon = np.vstack((polygon_xy[0], polygon_xy[1])).T.reshape(-1, 2)
                z = np.zeros(polygon.shape[0])
                dt1 = np.c_[polygon, z]
                dt1 = np.array(dt1, dtype=np.float32)
                filename_border = str(i).rjust(4, '0') + '.csv'
                fname_brd = os.path.join(path_folder, filename_border) 
                np.savetxt(fname_brd, dt1, delimiter=',', header='x,y,z')
                border_count += 1

            elif str(type(cut_poly)) == "<class 'shapely.geometry.multipolygon.MultiPolygon'>":
                j = 0
                for poly_item in cut_poly.geoms:
                    if self._should_stop():
                        return border_count
                    polygon_xy = np.asarray(poly_item.exterior.coords.xy)       
                    polygon = np.vstack((polygon_xy[0], polygon_xy[1])).T.reshape(-1, 2)
                    z = np.zeros(polygon.shape[0])
                    dt1 = np.c_[polygon, z]
                    dt1 = np.array(dt1, dtype=np.float32)
                    filename_border = str(i).rjust(4, '0')
                    filename_border = filename_border + f"_{j}.csv"
                    fname_brd = os.path.join(path_folder, filename_border) 
                    np.savetxt(fname_brd, dt1, delimiter=',', header='x,y,z')
                    border_count += 1
                    j += 1
        return border_count


