from OpenGL.arrays import vbo
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QPointF
from OpenGL.GL import *
import open3d as o3d
import numpy as np
import laspy
import pywavefront
import os

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

        self.vbo = None
        self.num_points = 0
        self.color = (1.0, 1.0, 1.0)  # Белый цвет по умолчанию

        self.vbo_data = {}
        self.vbo_data_models = {}


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
            las = laspy.read(filename)
            points = np.vstack((las.x, las.y, las.z)).transpose()
            colors = np.vstack((las.red, las.green, las.blue)).transpose() / 255.0
        elif file_extension == '.pcd':
            pcd = o3d.io.read_point_cloud(filename)
            points = np.asarray(pcd.points)
            colors = np.ones_like(points)  # Белый цвет по умолчанию
        elif file_extension == '.csv':
            return
        else:
            print("Unsupported file format")
            return

        points_centered = points - np.mean(points, axis=0)
        # Создание и сохранение VBO
        point_vbo = vbo.VBO(np.array(points_centered, dtype=np.float32))
        color_vbo = vbo.VBO(np.array(colors, dtype=np.float32))
        self.vbo_data[filename] = (point_vbo, color_vbo, len(points_centered))
        self.point_clouds[filename] = {'active': True, 'data': points_centered}
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

        points_centered = points - np.mean(points, axis=0)
        point_vbo = vbo.VBO(points_centered)
        color_vbo = vbo.VBO(colors)
        self.vbo_data_models[filename] = (point_vbo, color_vbo, len(points_centered))
        self.models[filename] = {
            'active': True,
            'data': points_centered,
            'num_polygons': total_faces
        }
        self.scale_factor = self.calculate_scale_factor_for_all()
        self.update()

    def calculate_scale_factor_for_all(self):
        max_cloud = 0
        max_model = 0

        if self.vbo_data:
            for key, pcd in self.vbo_data.items():
                if self.point_clouds[key]['active']:
                    points = pcd[0]
                    size = np.max(points, axis=0) - np.min(points, axis=0)
                    max_cloud = max(max_cloud, np.max(size))
        if self.vbo_data_models:
            for key, model in self.vbo_data_models.items():
                if self.models[key]['active']:
                    points = model[0]
                    size = np.max(points, axis=0) - np.min(points, axis=0)
                    max_model = max(max_model, np.max(size))

        max_size = max(max_cloud, max_model)
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
        glClearColor(0, 0, 0, 1)
        glEnable(GL_DEPTH_TEST)

        self.vbo = vbo.VBO(np.array([], dtype=np.float32))
        self.color_vbo = vbo.VBO(np.array([], dtype=np.float32))

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
            if cloud_info['active']:  # Проверяем, активно ли облако
                if filename in self.vbo_data:
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
                    point_vbo.unbind()
                    color_vbo.unbind()

        glEnableClientState(GL_VERTEX_ARRAY)
        # Отрисовка всех моделей
        for model, model_info in self.models.items():
            if model_info['active']:  # Проверяем, активна ли модель для отображения
                vertex_vbo, color_vbo, num_indices = self.vbo_data_models[model]

                vertex_vbo.bind()
                glVertexPointer(3, GL_FLOAT, 0, None)

                color_vbo.bind()
                glColorPointer(3, GL_FLOAT, 0, None)
                glPushMatrix()

                # Отрисовываем с использованием индексного буфера
                glDrawArrays(GL_TRIANGLES, 0, num_indices)

                glPopMatrix()

                vertex_vbo.unbind()
                color_vbo.unbind()

        glDisableClientState(GL_VERTEX_ARRAY)
        glPopMatrix()
        self.update()

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
