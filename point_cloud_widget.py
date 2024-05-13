from OpenGL.arrays import vbo
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QPointF
from OpenGL.GL import *
import open3d as o3d
import numpy as np
import laspy
import pywavefront

class OpenGLWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super(OpenGLWidget, self).__init__(parent)
        self.point_clouds = {}
        self.models = {}
        self.scale_factor = 2
        self.last_mouse_position = None
        self.rotation_x = -90
        self.rotation_y = 0
        self.rotation_z = 0
        self.point_cloud_position = QPointF(0, 0)  # Текущее положение облака точек

        self.vbo = None
        self.num_points = 0

    def initializeGL(self):
        glClearColor(0, 0, 0, 1)
        glEnable(GL_DEPTH_TEST)

        self.vbo = vbo.VBO(np.array([], dtype=np.float32))

    def updatePointCloud(self, point_cloud):
        # Получение данных точек из объекта PointCloud
        points = np.asarray(point_cloud.points)

        # Убедимся, что данные существуют
        if points.size == 0:
            return  # Выходим, если нет данных

        # Преобразование данных точек для использования в VBO
        if self.vbo is None:
            self.vbo = vbo.VBO(points.astype(np.float32))
        else:
            self.vbo.set_array(points.astype(np.float32))
            self.vbo.bind()

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
        # TODO добавить обработку цветов
        for point_cloud in self.point_clouds.values():
            self.updatePointCloud(point_cloud)

            if self.vbo:
                self.vbo.bind()
                glEnableClientState(GL_VERTEX_ARRAY)
                glVertexPointer(3, GL_FLOAT, 0, self.vbo)
                glDrawArrays(GL_POINTS, 0, self.num_points)
                glDisableClientState(GL_VERTEX_ARRAY)
                self.vbo.unbind()

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

    def loadPointCloud(self, filename):
        las = laspy.read(filename)
        points = np.vstack((las.x, las.y, las.z)).transpose()
        pcd_center = np.mean(points, axis=0)
        points_centered = points - pcd_center
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points_centered)
        self.point_clouds[filename] = pcd
        self.update()

    def loadModel(self, filename):
        model = pywavefront.Wavefront(filename, collect_faces=True)
        self.models[filename] = model
        self.update()

    def setScaleFactor(self, scale):
        self.scale_factor = scale
        self.update()

    def mousePressEvent(self, event):
        self.last_mouse_position = event.position()

    def mouseMoveEvent(self, event):
        rotation_sensitivity = 0.3  # Коэффициент чувствительности вращения
        shift_sensitivity = 0.001  # Коэффициент чувствительности смещения
        
        if (self.last_mouse_position and event.buttons() == Qt.MouseButton.LeftButton):
            delta = event.position() - self.last_mouse_position
            self.rotation_z += delta.x() * rotation_sensitivity
            self.rotation_x += delta.y() * rotation_sensitivity
            self.last_mouse_position = event.position()
            self.update()
            
        if (self.last_mouse_position and event.buttons() == Qt.MouseButton.RightButton):
            # delta = event.position() - self.last_mouse_position
            # self.scene_offset = [2, 2, 0]
            # self.last_mouse_position = event.position()
            # self.update()
            delta = event.position() - self.last_mouse_position
            self.point_cloud_position += delta * shift_sensitivity
            self.last_mouse_position = event.position()
            self.update()

    def mouseReleaseEvent(self, event):
        self.last_mouse_position = None
    
    def wheelEvent(self, event):
        angle = event.angleDelta().y()
        scale_factor_change = 0.5  # Коэффициент изменения масштаба
        if angle > 0:
            self.scale_factor += scale_factor_change
        else:
            self.scale_factor -= scale_factor_change
            if self.scale_factor < 0.1:  # Предотвращение слишком маленького масштаба
                self.scale_factor = 0.1
        self.update()
