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
        self.rotation_x = 0
        self.rotation_y = 0
        self.rotation_z = 0
        self.rotation_mode = "Z"
        self.point_cloud_position = QPointF(0, 0)  # Текущее положение облака точек

        self.vbo = None
        self.num_points = 0
        self.color = (1.0, 1.0, 1.0)  # Белый цвет по умолчанию


    def load_point_cloud(self, filename):
        # Определение формата файла по расширению
        file_extension = os.path.splitext(filename)[1].lower()

        if file_extension == '.las':
            # Загрузка LAS файла
            las = laspy.read(filename)
            points = np.vstack((las.x, las.y, las.z)).transpose()
            # Чтение RGB цвета
            colors = np.vstack((las.red, las.green, las.blue)).transpose() / 255.0  # Нормализуем цвета к диапазону [0, 1]

        elif file_extension == '.pcd':
            # Загрузка PCD файла
            pcd = o3d.io.read_point_cloud(filename)
            points = np.asarray(pcd.points)
            colors = np.ones_like(points)  # Белый цвет по умолчанию
        else:
            print("Unsupported file format")
            return

        # Убираем отрицательные значения цветов
        # colors = np.abs(colors)
    
        # Центрирование точек
        pcd_center = np.mean(points, axis=0)
        points_centered = points - pcd_center

        # Создание объекта PointCloud в Open3D
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points_centered)
        pcd.colors = o3d.utility.Vector3dVector(colors)

        # Сохранение облака точек в словарь
        self.point_clouds[filename] = pcd
        
        # Вычисление и установка масштабного коэффициента для всех загруженных облаков точек
        self.scale_factor = self.calculate_scale_factor_for_all()
    
        self.update()
        
    def calculate_scale_factor_for_all(self):
        max_size = 0

        for pcd in self.point_clouds.values():
            points = np.asarray(pcd.points)
            size = np.max(points, axis=0) - np.min(points, axis=0)
            max_size = max(max_size, np.max(size))

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

    def update_point_cloud(self, point_cloud):
        # Получение данных точек из объекта PointCloud
        points = np.asarray(point_cloud.points)
        colors = np.asarray(point_cloud.colors)
        # Убедимся, что данные существуют
        if points.size == 0:
            return  # Выходим, если нет данных
        
            # Если массив цветов пустой, устанавливаем белый цвет по умолчанию
        if colors.size == 0:
            colors = np.ones_like(points) * [1.0, 1.0, 1.0]  # Белый цвет

        # Преобразование данных точек для использования в VBO
        if self.vbo is None:
            self.vbo = vbo.VBO(points.astype(np.float32))
            self.color_vbo = vbo.VBO(colors.astype(np.float32))
        else:
            self.vbo.set_array(points.astype(np.float32))
            self.color_vbo.set_array(colors.astype(np.float32))

        # Сохранение количества точек для последующего рендеринга
        self.num_points = points.shape[0]

    def find_model_center(self, model):
        # Вычисление средних значений координат всех вершин
        sum_x = sum_y = sum_z = 0
        for vertex in model.vertices:
            sum_x += vertex[0]
            sum_y += vertex[1]
            sum_z += vertex[2]
        num_vertices = len(model.vertices)
        center_x = sum_x / num_vertices
        center_y = sum_y / num_vertices
        center_z = sum_z / num_vertices
        return center_x, center_y, center_z

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
        for point_cloud in self.point_clouds.values():
            self.update_point_cloud(point_cloud)

            if self.vbo:
                glEnableClientState(GL_VERTEX_ARRAY)
                glEnableClientState(GL_COLOR_ARRAY)
                
                self.vbo.bind()
                glVertexPointer(3, GL_FLOAT, 0, self.vbo)
                
                self.vbo.unbind()
                self.color_vbo.bind()
                
                glColorPointer(3, GL_FLOAT, 0, self.color_vbo)
                
                glDrawArrays(GL_POINTS, 0, self.num_points)
                
                glDisableClientState(GL_COLOR_ARRAY)
                glDisableClientState(GL_VERTEX_ARRAY)
                self.color_vbo.unbind()

        # Отрисовка всех моделей
        for model in self.models.values():
            # Центрирование модели (можно оптимизировать)
            center_x, center_y, center_z = self.find_model_center(model)
            glTranslatef(-center_x, -center_y, -center_z)

            for mesh in model.mesh_list:
                glBegin(GL_TRIANGLES)
                for face in mesh.faces:
                    for vertex_i in face:
                        glVertex3f(*model.vertices[vertex_i])
                glEnd()

        glPopMatrix()

    def load_model(self, filename):
        model = pywavefront.Wavefront(filename, collect_faces=True)
        self.models[filename] = model
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
            angle -= 360
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
        print(self.scale_factor)
        if angle > 0:
            self.scale_factor *= scale_factor_change
        else:
            self.scale_factor /= scale_factor_change
            
        # Предотвращение слишком маленького или слишком большого масштаба
        if self.scale_factor < 0.005:
            self.scale_factor = 0.005
        elif self.scale_factor > 10:
            self.scale_factor = 10

        self.update()