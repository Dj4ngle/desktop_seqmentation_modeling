from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from OpenGL.GL import *
import open3d as o3d
import numpy as np

class OpenGLWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super(OpenGLWidget, self).__init__(parent)
        self.point_cloud = None
        self.scale_factor = 3
        self.last_mouse_position = None
        self.rotation_x = 0
        self.rotation_y = 0

    def initializeGL(self):
        glClearColor(0, 25, 0, 1)
        glEnable(GL_DEPTH_TEST)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glPushMatrix()
        glPointSize(5)
        glScalef(self.scale_factor, self.scale_factor, self.scale_factor)
        glRotatef(self.rotation_x, 1, 0, 0)
        glRotatef(self.rotation_y, 0, 1, 0)
        glBegin(GL_POINTS)
        if self.point_cloud:
            for point in self.point_cloud.points:
                glColor3d(point[0], point[1], point[2])
                glVertex3d(point[0], point[1], point[2])
        glEnd()
        glPopMatrix()

    def loadPointCloud(self, filename):
        pcd = o3d.io.read_point_cloud(filename)
        # Пример нормализации и центрирования облака точек
        pcd = pcd.voxel_down_sample(voxel_size=0.0005)
        pcd_center = pcd.get_center()
        pcd.points = o3d.utility.Vector3dVector(np.asarray(pcd.points) - pcd_center)
        self.point_cloud = pcd
        self.update()  # Обновление виджета для отрисовки

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
