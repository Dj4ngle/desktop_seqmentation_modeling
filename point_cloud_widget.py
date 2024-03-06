from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from OpenGL.GL import *
import open3d as o3d
import numpy as np
import laspy

class OpenGLWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super(OpenGLWidget, self).__init__(parent)
        self.point_cloud = None
        self.scale_factor = 1   
        self.last_mouse_position = None
        self.rotation_x = 0
        self.rotation_y = 0

    def initializeGL(self):
        glClearColor(0, 0, 0, 1)
        glEnable(GL_DEPTH_TEST)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glPushMatrix()
        glPointSize(1)
        glScalef(self.scale_factor, self.scale_factor, self.scale_factor)
        glRotatef(self.rotation_x, 1, 0, 0)
        glRotatef(self.rotation_y, 0, 1, 0)
        glBegin(GL_POINTS)

        if self.point_cloud:
            for point in self.point_cloud.points:
                color = [75, 147, 235]
                glColor3d(color[0] / 255, color[1] / 255, color[2] / 255)
                glVertex3d(point[0], point[1], point[2])
        glEnd()
        glPopMatrix()

    def loadPointCloud(self, filename):
        las = laspy.read(filename)
        # Преобразование данных точек в numpy массив
        points = np.vstack((las.x, las.y, las.z)).transpose()
        # Центрирование облака точек
        pcd_center = np.mean(points, axis=0)
        points_centered = points - pcd_center
        # Создание объекта облака точек для open3d
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points_centered)
        # Обновление внутреннего представления облака точек
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
