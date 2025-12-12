class CS():
    def __init__(self,
                 FLAG_cut_data=True, FLAG_make_cells=True, FLAG_make_stumps=True,
                 cut_data_method="voronoi_tessellation",
                 LOW=0.0, UP=3.0,
                 x_shift=0, y_shift=0, z_shift=0,
                 algo="birch", n_clusters=1,
                 intensity_cut_vor_tes=20000, intensity_cut=0,
                 cell_size=0.20,
                 height_limit_1=1.25, height_limit_2=1.35,
                 eps_XY=0.08, eps_Z=0.7,
                 path_base=None,  # Всегда нужно задавать самому
                 fname_points=None,  # Всегда нужно задавать самому
                 fname_traj="traj.las",
                 fname_shape="Polyline.shp"):
        self.FLAG_cut_data = FLAG_cut_data
        self.FLAG_make_cells = FLAG_make_cells
        self.FLAG_make_stumps = FLAG_make_stumps
        self.cut_data_method = cut_data_method
        self.LOW = LOW
        self.UP = UP
        self.x_shift = x_shift
        self.y_shift = y_shift
        self.z_shift = z_shift
        self.algo = algo
        self.n_clusters = n_clusters
        self.cell_size = cell_size
        self.intensity_cut_vor_tes = intensity_cut_vor_tes
        self.intensity_cut = intensity_cut
        self.height_limit_1 = height_limit_1
        self.height_limit_2 = height_limit_2
        self.eps_XY = eps_XY
        self.eps_Z = eps_Z
        self.path_base = path_base
        self.fname_points = fname_points
        self.fname_traj = fname_traj
        self.fname_shape = fname_shape
