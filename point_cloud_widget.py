from PyQt6.QtOpenGLWidgets import QOpenGLWidget
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

    def initializeGL(self):
        glClearColor(0, 0, 0, 1)
        glEnable(GL_DEPTH_TEST)

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
        glRotatef(self.rotation_x, 1, 0, 0)
        glRotatef(self.rotation_y, 0, 1, 0)
        glRotatef(self.rotation_z, 0, 0, 1) 

        color = [75 / 255, 147 / 255, 235 / 255]  # Пример цвета
        # Отрисовка всех облаков точек
        for point_cloud in self.point_clouds.values():
            glBegin(GL_POINTS)
            for point in np.asarray(point_cloud.points):
                # glColor3d(color[0], color[1], color[2])
                glVertex3d(point[0], point[1], point[2])
            glEnd()

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
        sensitivity = 0.3  # Коэффициент чувствительности вращения
        if self.last_mouse_position:
            delta = event.position() - self.last_mouse_position
            self.rotation_z += delta.x() * sensitivity
            self.rotation_x += delta.y() * sensitivity
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
