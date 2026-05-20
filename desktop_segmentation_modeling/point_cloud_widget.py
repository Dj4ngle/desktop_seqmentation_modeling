from OpenGL.arrays import vbo
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QPointF
from OpenGL.GL import *
import numpy as np
import os


POINT_CLOUD_PALETTES = {
    "blue": ((0.78, 0.90, 1.0), (0.05, 0.32, 0.72)),
    "cyan": ((0.74, 0.95, 0.96), (0.02, 0.45, 0.58)),
    "green": ((0.78, 0.93, 0.78), (0.10, 0.48, 0.22)),
    "orange": ((1.0, 0.78, 0.38), (0.82, 0.27, 0.06)),
    "violet": ((0.88, 0.82, 1.0), (0.36, 0.21, 0.72)),
    "gray": ((0.86, 0.88, 0.91), (0.25, 0.29, 0.34)),
}

POINT_CLOUD_PALETTE_LABELS = {
    "blue": "Синий градиент",
    "cyan": "Голубой градиент",
    "green": "Зелёный градиент",
    "orange": "Оранжевый градиент",
    "violet": "Фиолетовый градиент",
    "gray": "Серый градиент",
}


class OpenGLWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super(OpenGLWidget, self).__init__(parent)
        self.point_clouds = {}
        self.models = {}
        self.scale_factor = 2
        self.last_mouse_position = None
        self.rotation_x = 1
        self.rotation_y = 1
        self.rotation_z = 1
        self.rotation_mode = "Z"
        self.point_cloud_position = QPointF(0, 0)  # Текущее положение облака точек
        self.background_color = (0.0, 0.0, 0.0, 1.0)
        self.use_light_background = False

        self.vbo = None
        self.num_points = 0
        self.color = (1.0, 1.0, 1.0)  # Белый цвет по умолчанию

        self.vbo_data = {}
        self.vbo_data_models = {}
        self.render_metadata = {}
        self.point_cloud_palette_overrides = {}

    def _create_point_vbos(self, points_centered, colors):
        self.makeCurrent()
        try:
            point_vbo = vbo.VBO(np.asarray(points_centered, dtype=np.float32))
            color_vbo = vbo.VBO(np.asarray(colors, dtype=np.float32))
        finally:
            self.doneCurrent()
        return point_vbo, color_vbo

    def _create_color_vbo(self, colors):
        self.makeCurrent()
        try:
            return vbo.VBO(np.asarray(colors, dtype=np.float32))
        finally:
            self.doneCurrent()

    def _release_vbo_entry(self, storage, filename):
        if filename not in storage:
            return
        point_vbo, color_vbo, _ = storage.pop(filename)
        if not self.isValid():
            return
        self.makeCurrent()
        try:
            for buffer in (point_vbo, color_vbo):
                if buffer is not None:
                    buffer.delete()
        finally:
            self.doneCurrent()

    def release_point_cloud(self, filename):
        self._release_vbo_entry(self.vbo_data, filename)
        self.point_clouds.pop(filename, None)
        self.render_metadata.pop(filename, None)
        self.point_cloud_palette_overrides.pop(filename, None)

    def release_model(self, filename):
        self._release_vbo_entry(self.vbo_data_models, filename)
        self.models.pop(filename, None)
        self.render_metadata.pop(filename, None)

    def reset_camera_view(self):
        self.point_cloud_position = QPointF(0, 0)
        self.rotation_x = 1
        self.rotation_y = 1
        self.rotation_z = 1
        self.scale_factor = self.calculate_scale_factor_for_all()

    def load_point_cloud(self, filename):
        if filename not in self.point_clouds:
            # Инициализация записи, если она еще не существует
            self.point_clouds[filename] = {'active': False, 'data': None}

        if filename in self.vbo_data:
            # Если данные уже загружены в VBO, просто активируем их для отображения
            self.point_clouds[filename]['active'] = True
            self.update()
            return
        # Загрузка и кэширование данных
        file_extension = os.path.splitext(filename)[1].lower()
        if file_extension == '.las':
            import laspy

            las = laspy.read(filename)
            points = np.column_stack((las.x, las.y, las.z))
            colors = np.column_stack((las.red, las.green, las.blue)) / 255.0
        elif file_extension == '.pcd':
            from desktop_segmentation_modeling.point_cloud_io import read_pcd_points_and_colors

            points, colors, _ = read_pcd_points_and_colors(filename)
        elif file_extension == '.csv':
            return
        else:
            print("Unsupported file format")
            return

        raw_points = np.asarray(points)
        points_centered = self.center_points_for_display(raw_points)
        source_colors = np.asarray(colors, dtype=np.float32)
        colors = self.resolve_point_cloud_colors(filename, points_centered, source_colors, raw_points, None)

        self._release_vbo_entry(self.vbo_data, filename)
        point_vbo, color_vbo = self._create_point_vbos(points_centered, colors)
        self.vbo_data[filename] = (point_vbo, color_vbo, len(points_centered))
        self.point_clouds[filename] = {
            'active': True,
            'data': points_centered,
            'full_data': raw_points,
            'source_colors': source_colors,
            'color_scalar': None,
            'metadata': self.build_render_metadata(raw_points),
        }
        self.render_metadata[filename] = self.point_clouds[filename]['metadata']

        self.scale_factor = self.calculate_scale_factor_for_all()
        self.update()

    def load_model(self, filename):
        if filename not in self.models:
            self.models[filename] = {'active': False, 'data': None}

        if filename in self.vbo_data_models:
            self.models[filename]['active'] = True
            self.update()
            return

        file_extension = os.path.splitext(filename)[1].lower()
        if file_extension == '.obj':
            import pywavefront

            scene = pywavefront.Wavefront(filename, collect_faces=True)
            vertices = []
            total_faces = 0
            for _, mesh in scene.meshes.items():
                total_faces += len(mesh.faces)
                for face in mesh.faces:
                    vertices.extend([scene.vertices[index] for index in face])
            points = np.array(vertices, dtype=np.float32)
            colors = np.ones((len(points), 3))  # Белый цвет для всех вершин
        else:
            print("Unsupported file format")
            return

        points_centered = self.center_points_for_display(points)
        self._release_vbo_entry(self.vbo_data_models, filename)
        point_vbo, color_vbo = self._create_point_vbos(points_centered, colors)
        self.vbo_data_models[filename] = (point_vbo, color_vbo, len(points_centered))
        self.models[filename] = {
            'active': True,
            'data': points_centered,
            'num_polygons': total_faces,
            'metadata': self.build_render_metadata(points_centered),
        }
        self.render_metadata[filename] = self.models[filename]['metadata']
        self.scale_factor = self.calculate_scale_factor_for_all()
        self.update()

    def load_model_from_arrays(self, filename, points):
        if filename in self.vbo_data_models:
            self.models[filename]['active'] = True
            self.update()
            return

        points = np.asarray(points, dtype=np.float32)
        if len(points) == 0:
            print(f"Модель {filename} не содержит вершин")
            return

        colors = np.ones((len(points), 3), dtype=np.float32)
        self._release_vbo_entry(self.vbo_data_models, filename)
        point_vbo, color_vbo = self._create_point_vbos(points, colors)
        self.vbo_data_models[filename] = (point_vbo, color_vbo, len(points))
        self.models[filename] = {
            'active': True,
            'data': points,
            'num_polygons': len(points) // 3,
            'metadata': self.build_render_metadata(points),
        }
        self.render_metadata[filename] = self.models[filename]['metadata']
        self.scale_factor = self.calculate_scale_factor_for_all()
        self.update()

    def load_point_cloud_from_arrays(self, filename, points, colors=None, full_data=None, metadata=None):
        points = np.asarray(points, dtype=np.float32)
        if len(points) == 0:
            print(f"Облако точек {filename} пустое")
            return

        if full_data is None:
            full_data = points
        full_data = np.asarray(full_data)

        points_centered = self.center_points_for_display(points)
        if colors is None:
            source_colors = np.ones((len(points_centered), 3), dtype=np.float32)
        else:
            source_colors = np.asarray(colors, dtype=np.float32)
            if len(source_colors) != len(points_centered):
                source_colors = np.ones((len(points_centered), 3), dtype=np.float32)

        if metadata is None:
            metadata = self.build_render_metadata(points_centered)

        color_scalar = metadata.get('color_scalar') if isinstance(metadata, dict) else None
        colors = self.resolve_point_cloud_colors(
            filename,
            points_centered,
            source_colors,
            full_data,
            metadata,
        )

        self._release_vbo_entry(self.vbo_data, filename)
        point_vbo, color_vbo = self._create_point_vbos(points_centered, colors)
        self.vbo_data[filename] = (point_vbo, color_vbo, len(points_centered))
        self.point_clouds[filename] = {
            'active': True,
            'data': points_centered,
            'full_data': full_data,
            'source_colors': source_colors,
            'color_scalar': color_scalar,
            'metadata': metadata,
        }
        self.render_metadata[filename] = metadata
        self.scale_factor = self.calculate_scale_factor_for_all()
        self.update()

    def resolve_point_cloud_colors(self, filename, points, source_colors, full_data=None, metadata=None):
        palette_name = self.point_cloud_palette_overrides.get(filename)
        if palette_name is None:
            palette_name = "blue" if self.use_light_background else "orange"

        return self.create_gradient_colors(
            filename,
            palette_name,
            points=points,
            full_data=full_data,
            metadata=metadata,
        )

    def create_gradient_colors(self, filename, palette_name, points=None, full_data=None, metadata=None):
        start_color, end_color = POINT_CLOUD_PALETTES.get(
            palette_name,
            POINT_CLOUD_PALETTES["blue"],
        )
        start_color = np.asarray(start_color, dtype=np.float32)
        end_color = np.asarray(end_color, dtype=np.float32)

        scalar = None
        if isinstance(metadata, dict):
            scalar = metadata.get('color_scalar')

        if scalar is None:
            cloud = self.point_clouds.get(filename, {})
            scalar = cloud.get('color_scalar')

        if scalar is None and full_data is not None:
            full_data = np.asarray(full_data)
            if full_data.ndim == 2 and full_data.shape[1] >= 3:
                scalar = full_data[:, 2]

        if scalar is None and points is not None:
            points = np.asarray(points)
            if points.ndim == 2 and points.shape[1] >= 3:
                scalar = points[:, 2]

        num_points = 0
        if points is not None:
            num_points = len(points)
        elif filename in self.vbo_data:
            num_points = self.vbo_data[filename][2]

        if scalar is None or len(scalar) != num_points:
            scalar = np.linspace(0.0, 1.0, num_points, dtype=np.float32)
        else:
            scalar = np.asarray(scalar, dtype=np.float32)

        if len(scalar) == 0:
            return np.empty((0, 3), dtype=np.float32)

        finite_mask = np.isfinite(scalar)
        if not np.any(finite_mask):
            normalized = np.zeros_like(scalar, dtype=np.float32)
        else:
            finite_values = scalar[finite_mask]
            min_value = float(np.min(finite_values))
            max_value = float(np.max(finite_values))
            if max_value == min_value:
                normalized = np.zeros_like(scalar, dtype=np.float32)
            else:
                normalized = (scalar - min_value) / (max_value - min_value)
                normalized = np.clip(normalized, 0.0, 1.0).astype(np.float32)

        return start_color + normalized[:, None] * (end_color - start_color)

    def refresh_point_cloud_colors(self):
        for filename in list(self.point_clouds.keys()):
            self.update_point_cloud_colors(filename)
        self.update()

    def update_point_cloud_colors(self, filename):
        if filename not in self.point_clouds or filename not in self.vbo_data:
            return

        cloud = self.point_clouds[filename]
        source_colors = cloud.get('source_colors')
        points = cloud.get('data')
        full_data = cloud.get('full_data')
        metadata = cloud.get('metadata')
        if source_colors is None or points is None:
            return

        colors = self.resolve_point_cloud_colors(
            filename,
            points,
            source_colors,
            full_data,
            metadata,
        )

        point_vbo, old_color_vbo, num_points = self.vbo_data[filename]
        if len(colors) != num_points:
            return

        if not self.isValid():
            return

        self.makeCurrent()
        try:
            if old_color_vbo is not None:
                old_color_vbo.delete()
            color_vbo = vbo.VBO(np.asarray(colors, dtype=np.float32))
        finally:
            self.doneCurrent()

        self.vbo_data[filename] = (point_vbo, color_vbo, num_points)

    def set_point_cloud_palette(self, filename, palette_name):
        if palette_name not in POINT_CLOUD_PALETTES:
            return

        self.point_cloud_palette_overrides[filename] = palette_name
        self.update_point_cloud_colors(filename)
        self.update()

    def clear_point_cloud_palette(self, filename):
        self.point_cloud_palette_overrides.pop(filename, None)
        self.update_point_cloud_colors(filename)
        self.update()

    def center_points_for_display(self, points):
        points = np.asarray(points, dtype=np.float32)
        return points - np.mean(points, axis=0, dtype=np.float64).astype(np.float32)

    def build_render_metadata(self, points):
        points = np.asarray(points)
        if points.size == 0:
            return {'min': None, 'max': None, 'center': None, 'max_size': 0.0}

        min_bounds = np.min(points[:, :3], axis=0)
        max_bounds = np.max(points[:, :3], axis=0)
        size = max_bounds - min_bounds
        return {
            'min': min_bounds,
            'max': max_bounds,
            'center': (min_bounds + max_bounds) / 2,
            'max_size': float(np.max(size)),
        }

    def calculate_scale_factor_for_all(self):
        max_size = 0.0

        for key, cloud in self.point_clouds.items():
            if cloud.get('active'):
                metadata = cloud.get('metadata') or self.render_metadata.get(key)
                max_size = max(max_size, metadata.get('max_size', 0.0) if metadata else 0.0)

        for key, model in self.models.items():
            if model.get('active'):
                metadata = model.get('metadata') or self.render_metadata.get(key)
                max_size = max(max_size, metadata.get('max_size', 0.0) if metadata else 0.0)

        scale_factor = 1.5 / max_size if max_size != 0 else 1
        return scale_factor
        
    def resizeGL(self, width, height):
        # Определяем размеры окна
        if height == 0:
            height = 1

        # Устанавливаем область отображения OpenGL
        glViewport(0, 0, width, height)

        # Модифицируем проекционную матрицу так, чтобы сохранить пропорции контента
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect_ratio = width / height
        if aspect_ratio > 1:
            glOrtho(-aspect_ratio, aspect_ratio, -1.0, 1.0, -1.0, 1.0)
        else:
            glOrtho(-1.0, 1.0, -1 / aspect_ratio, 1 / aspect_ratio, -1.0, 1.0)

        glMatrixMode(GL_MODELVIEW)
        
    def set_view_parameters(self, x, y, z ):
        self.scale_factor = self.calculate_scale_factor_for_all()
        self.rotation_x = x
        self.rotation_y = y
        self.rotation_z = z
        self.point_cloud_position = QPointF(0, 0)
        self.update()  # Обновляем виджет, чтобы отобразить изменения

    def initializeGL(self):
        glClearColor(*self.background_color)
        glEnable(GL_DEPTH_TEST)

        self.vbo = vbo.VBO(np.array([], dtype=np.float32))
        self.color_vbo = vbo.VBO(np.array([], dtype=np.float32))

    def set_background_color(self, red, green, blue, alpha=1.0):
        self.background_color = (red, green, blue, alpha)
        self.use_light_background = (red + green + blue) / 3 > 0.5
        if self.isValid():
            self.makeCurrent()
            try:
                glClearColor(*self.background_color)
            finally:
                self.doneCurrent()
        self.refresh_point_cloud_colors()

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glPushMatrix()
        glPointSize(1)
        glScalef(self.scale_factor, self.scale_factor, self.scale_factor)
        glTranslatef(self.point_cloud_position.x(), -self.point_cloud_position.y(), 0)  # Применяем смещение точки обзора
        glRotatef(self.rotation_x, 1, 0, 0)
        glRotatef(self.rotation_y, 0, 1, 0)
        glRotatef(self.rotation_z, 0, 0, 1)

        # Отрисовка всех облаков точек
        for filename, cloud_info in self.point_clouds.items():
            if cloud_info.get('active') and filename in self.vbo_data:
                point_vbo, color_vbo, num_points = self.vbo_data[filename]
                point_vbo.bind()
                glVertexPointer(3, GL_FLOAT, 0, None)
                glEnableClientState(GL_VERTEX_ARRAY)

                color_vbo.bind()
                glColorPointer(3, GL_FLOAT, 0, None)
                glEnableClientState(GL_COLOR_ARRAY)

                glDrawArrays(GL_POINTS, 0, num_points)

                glDisableClientState(GL_VERTEX_ARRAY)
                glDisableClientState(GL_COLOR_ARRAY)
                color_vbo.unbind()
                point_vbo.unbind()

        # Отрисовка всех моделей
        for model, model_info in self.models.items():
            if model_info.get('active') and model in self.vbo_data_models:
                vertex_vbo, color_vbo, num_indices = self.vbo_data_models[model]

                vertex_vbo.bind()
                glVertexPointer(3, GL_FLOAT, 0, None)
                glEnableClientState(GL_VERTEX_ARRAY)

                if self.use_light_background:
                    glColor3f(0.05, 0.05, 0.05)
                else:
                    color_vbo.bind()
                    glColorPointer(3, GL_FLOAT, 0, None)
                    glEnableClientState(GL_COLOR_ARRAY)
                glPushMatrix()

                # Отрисовываем с использованием индексного буфера
                glDrawArrays(GL_TRIANGLES, 0, num_indices)

                glPopMatrix()

                vertex_vbo.unbind()
                if self.use_light_background:
                    glColor3f(1.0, 1.0, 1.0)
                else:
                    color_vbo.unbind()
                    glDisableClientState(GL_COLOR_ARRAY)

                glDisableClientState(GL_VERTEX_ARRAY)

        glPopMatrix()

    def set_scale_factor(self, scale):
        self.scale_factor = scale
        self.update()

    def mousePressEvent(self, event):
        self.last_mouse_position = event.position()
        if event.buttons() == Qt.MouseButton.MiddleButton:
            # Изменение режима вращения при нажатии на среднюю кнопку мыши
            self.rotation_mode = "X" if self.rotation_mode == "Z" else "Z"
            self.update()
            
    def normalize_angle(self, angle):
        while angle < 0:
            angle += 360
        while angle >= 360:
            angle = 0
        return angle

    def mouseMoveEvent(self, event):
        rotation_sensitivity = 0.3  # Коэффициент чувствительности вращения
        
        if (self.last_mouse_position and event.buttons() == Qt.MouseButton.LeftButton):
            delta = event.position() - self.last_mouse_position
            if self.rotation_mode == "Z":
                self.rotation_x += delta.y() * rotation_sensitivity
                self.rotation_y += delta.x() * rotation_sensitivity
            else:
                self.rotation_z -= delta.x() * rotation_sensitivity
                
            # Нормализуем углы поворота
            self.rotation_x = self.normalize_angle(self.rotation_x)
            self.rotation_y = self.normalize_angle(self.rotation_y)
            self.rotation_z = self.normalize_angle(self.rotation_z)

            
            self.last_mouse_position = event.position()
            self.update()
            
        shift_sensitivity = 0.00285 / self.scale_factor # Коэффициент чувствительности смещения
            
        if (self.last_mouse_position and event.buttons() == Qt.MouseButton.RightButton):
            delta = event.position() - self.last_mouse_position
            self.point_cloud_position += delta * shift_sensitivity
            self.last_mouse_position = event.position()
            self.update()

    def mouseReleaseEvent(self, event):
        self.last_mouse_position = None
    
    def wheelEvent(self, event):
        angle = event.angleDelta().y()
        
        # Определение коэффициента изменения масштаба
        scale_factor_change = 1.1  # Увеличение или уменьшение масштаба на 10%
        if angle > 0:
            self.scale_factor *= scale_factor_change
        else:
            self.scale_factor /= scale_factor_change
            
        # Предотвращение слишком маленького или слишком большого масштаба
        if self.scale_factor < 0.005:
            self.scale_factor = 0.005
        elif self.scale_factor > 100:
            self.scale_factor = 100

        self.update()
