class SS():
    def __init__(
        self,
        path_base=None,  # Всегда нужно задавать самому
        fname_points=None,  # Всегда нужно задавать самому
        fname_shape="borders.shp",
        csv_name_coord="Loc1.csv",
        first_num=0,
        STEP=2.5,
        z_thresholds=[0.5, 0.625, 0.695, 0.75, 0.875, 1],
        eps_steps=[0.01, 0.15, 0.35, 0.5, 0.6, 0.7],
        min_pts=[50, 50, 50, 50, 45, 40]
    ):
        self.path_base = path_base
        self.fname_points = fname_points
        self.fname_shape = fname_shape
        self.csv_name_coord = csv_name_coord
        self.first_num = first_num
        self.STEP = STEP
        self.z_thresholds = z_thresholds
        self.eps_steps = eps_steps
        self.min_pts = min_pts

        self.step1_folder_name = 'vor'
        self.step2_folder_name = 'ram'
        self.step3_folder_name = 'clear'
