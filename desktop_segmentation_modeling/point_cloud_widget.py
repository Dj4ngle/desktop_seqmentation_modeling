from OpenGL.arrays import vbo
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QPointF
from OpenGL.GL import *
import numpy as np
import os

from desktop_segmentation_modeling.point_cloud_colors import adapt_point_colors_for_theme

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

    def _normalize_source_colors(self, colors, point_count):
        if colors is None:
            return np.ones((point_count, 3), dtype=np.float32)
        colors = np.asarray(colors, dtype=np.float32)
        if colors.ndim == 1:
            colors = np.tile(colors.reshape(1, 3), (point_count, 1))
        if len(colors) != point_count:
            return np.ones((point_count, 3), dtype=np.float32)
        return np.clip(colors, 0.0, 1.0)

    def _display_colors_for_theme(self, source_colors):
        return adapt_point_colors_for_theme(source_colors, self.use_light_background)

    def _update_color_vbo(self, filename, display_colors, storage):
        if filename not in storage:
            return
        point_vbo, color_vbo, num_points = storage[filename]
        self.makeCurrent()
        try:
            color_vbo.delete()
            color_vbo = vbo.VBO(np.asarray(display_colors, dtype=np.float32))
        finally:
            self.doneCurrent()
        storage[filename] = (point_vbo, color_vbo, num_points)

    def refresh_theme_adapted_colors(self):
        for filename, cloud in self.point_clouds.items():
            source_colors = cloud.get('source_colors')
            if source_colors is None or filename not in self.vbo_data:
                continue
            display_colors = self._display_colors_for_theme(source_colors)
            cloud['display_colors'] = display_colors
            self._update_color_vbo(filename, display_colors, self.vbo_data)

        for filename, model in self.models.items():
            source_colors = model.get('source_colors')
            if source_colors is None or filename not in self.vbo_data_models:
                continue
            display_colors = self._display_colors_for_theme(source_colors)
            model['display_colors'] = display_colors
            self._update_color_vbo(filename, display_colors, self.vbo_data_models)

    def _create_point_vbos(self, points_centered, colors):
        self.makeCurrent()
        try:
            point_vbo = vbo.VBO(np.asarray(points_centered, dtype=np.float32))
            color_vbo = vbo.VBO(np.asarray(colors, dtype=np.float32))
        finally:
            self.doneCurrent()
        return point_vbo, color_vbo

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
        source_colors = self._normalize_source_colors(colors, len(points_centered))
        display_colors = self._display_colors_for_theme(source_colors)

        self._release_vbo_entry(self.vbo_data, filename)
        point_vbo, color_vbo = self._create_point_vbos(points_centered, display_colors)
        self.vbo_data[filename] = (point_vbo, color_vbo, len(points_centered))
        self.point_clouds[filename] = {
            'active': True,
            'data': points_centered,
            'full_data': raw_points,
            'source_colors': source_colors,
            'display_colors': display_colors,
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
            source_colors = np.ones((len(points), 3), dtype=np.float32)
        else:
            print("Unsupported file format")
            return

        points_centered = self.center_points_for_display(points)
        display_colors = self._display_colors_for_theme(source_colors)
        self._release_vbo_entry(self.vbo_data_models, filename)
        point_vbo, color_vbo = self._create_point_vbos(points_centered, display_colors)
        self.vbo_data_models[filename] = (point_vbo, color_vbo, len(points_centered))
        self.models[filename] = {
            'active': True,
            'data': points_centered,
            'source_colors': source_colors,
            'display_colors': display_colors,
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

        source_colors = np.ones((len(points), 3), dtype=np.float32)
        display_colors = self._display_colors_for_theme(source_colors)
        self._release_vbo_entry(self.vbo_data_models, filename)
        point_vbo, color_vbo = self._create_point_vbos(points, display_colors)
        self.vbo_data_models[filename] = (point_vbo, color_vbo, len(points))
        self.models[filename] = {
            'active': True,
            'data': points,
            'source_colors': source_colors,
            'display_colors': display_colors,
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
        source_colors = self._normalize_source_colors(colors, len(points_centered))
        display_colors = self._display_colors_for_theme(source_colors)

        if metadata is None:
            metadata = self.build_render_metadata(points_centered)

        self._release_vbo_entry(self.vbo_data, filename)
        point_vbo, color_vbo = self._create_point_vbos(points_centered, display_colors)
        self.vbo_data[filename] = (point_vbo, color_vbo, len(points_centered))
        self.point_clouds[filename] = {
            'active': True,
            'data': points_centered,
            'full_data': full_data,
            'source_colors': source_colors,
            'display_colors': display_colors,
            'metadata': metadata,
        }
        self.render_metadata[filename] = metadata
        self.scale_factor = self.calculate_scale_factor_for_all()
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
        self.refresh_theme_adapted_colors()
        self.update()

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

                color_vbo.bind()
                glColorPointer(3, GL_FLOAT, 0, None)
                glEnableClientState(GL_COLOR_ARRAY)
                glPushMatrix()

                # Отрисовываем с использованием индексного буфера
                glDrawArrays(GL_TRIANGLES, 0, num_indices)

                glPopMatrix()

                vertex_vbo.unbind()
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
