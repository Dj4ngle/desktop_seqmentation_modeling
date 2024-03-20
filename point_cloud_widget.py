from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from OpenGL.GL import *
import open3d as o3d
import numpy as np
import laspy
import pywavefront

class OpenGLWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super(OpenGLWidget, self).__init__(parent)
        self.point_cloud = None
        self.model = None
        self.scale_factor = 1
        self.last_mouse_position = None
        self.rotation_x = 0
        self.rotation_y = 0

    def initializeGL(self):
        glClearColor(0, 0, 0, 1)
        glEnable(GL_DEPTH_TEST)

    def find_model_center(self):
        # Вычисление средних значений координат всех вершин
        sum_x = sum_y = sum_z = 0
        for vertex in self.model.vertices:
            sum_x += vertex[0]
            sum_y += vertex[1]
            sum_z += vertex[2]
        num_vertices = len(self.model.vertices)
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

        # Отрисовка облака точек
        glBegin(GL_POINTS)
        if self.point_cloud:
            for point in np.asarray(self.point_cloud.points):
                color = [75, 147, 235]  # Пример цвета
                glColor3d(color[0] / 255, color[1] / 255, color[2] / 255)
                glVertex3d(point[0], point[1], point[2])
        glEnd()

        # Отрисовка модели OBJ
        if self.model:

            #центрирование модели
            center_x, center_y, center_z = self.find_model_center()
            glTranslatef(-center_x, -center_y, -center_z)

            for mesh in self.model.mesh_list:
                glBegin(GL_TRIANGLES)
                for face in mesh.faces:
                    for vertex_i in face:
                        glVertex3f(*self.model.vertices[vertex_i])
                glEnd()

        glPopMatrix()

    def loadPointCloud(self, filename):
        las = laspy.read(filename)
        points = np.vstack((las.x, las.y, las.z)).transpose()
        pcd_center = np.mean(points, axis=0)
        points_centered = points - pcd_center
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points_centered)
        self.point_cloud = pcd
        # убирает модель с экрана, если была
        self.model = None
        self.update()

    def loadModel(self, filename):
        # Загрузка модели OBJ
        self.model = pywavefront.Wavefront(filename, collect_faces=True)
        # убирает облако точек с экрана, если была
        self.point_cloud = None
        self.update()

    def setScaleFactor(self, scale):
        self.scale_factor = scale
        self.update()

    def mousePressEvent(self, event):
        self.last_mouse_position = event.position()

    def mouseMoveEvent(self, event):
        sensitivity = 0.3  # Коэффициент чувствительности вращения
        if self.last_mouse_position:
            dx = event.position().x() - self.last_mouse_position.x()
            dy = event.position().y() - self.last_mouse_position.y()
            self.rotation_x += dy * sensitivity
            self.rotation_y += dx * sensitivity
            self.update()
        self.last_mouse_position = event.position()

    def mouseReleaseEvent(self, event):
        self.last_mouse_position = None
    
    def wheelEvent(self, event):
        angle = event.angleDelta().y()
        scale_factor_change = 0.1  # Коэффициент изменения масштаба
        if angle > 0:
            self.scale_factor += scale_factor_change
        else:
            self.scale_factor -= scale_factor_change
            if self.scale_factor < 0.1:  # Предотвращение слишком маленького масштаба
                self.scale_factor = 0.1
        self.update()
