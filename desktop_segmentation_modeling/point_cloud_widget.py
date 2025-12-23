from OpenGL.arrays import vbo
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtWidgets import QWidget
from OpenGL.GL import *
import open3d as o3d
import numpy as np
import laspy
import pywavefront
import os

try:
    import vulkan as vk

    VULKAN_AVAILABLE = True
except ImportError:
    VULKAN_AVAILABLE = False
    print("Warning: vulkan-python not available. Install with: pip install vulkan")


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

        # Ссылка на монитор производительности (устанавливается из бенчмарка)
        self.performance_monitor = None
        
        # Убеждаемся, что виджет может получать события мыши и клавиатуры
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setEnabled(True)


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

        raw_points = points.copy()
        points_centered = points - np.mean(points, axis=0)

        # Создание и сохранение VBO
        point_vbo = vbo.VBO(np.array(points_centered, dtype=np.float32))
        color_vbo = vbo.VBO(np.array(colors, dtype=np.float32))

        self.vbo_data[filename] = (point_vbo, color_vbo, len(points_centered))
        self.point_clouds[filename] = {'active': True, 'data': points_centered, 'full_data': raw_points}

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

    def set_view_parameters(self, x, y, z):
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
        glTranslatef(self.point_cloud_position.x(), -self.point_cloud_position.y(),
                     0)  # Применяем смещение точки обзора
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
        
        # Записываем метрики производительности, если монитор установлен
        if self.performance_monitor is not None:
            # Получаем elapsed_time из benchmark_controller, если он существует и бенчмарк запущен
            elapsed_time = 0.0
            if hasattr(self.performance_monitor, 'benchmark_controller'):
                controller = self.performance_monitor.benchmark_controller
                # Проверяем, что контроллер существует и бенчмарк запущен
                if controller is not None and hasattr(controller, 'is_running') and controller.is_running:
                    if hasattr(controller, 'elapsed_time'):
                        elapsed_time = controller.elapsed_time
            # Записываем метрики всегда, если монитор установлен
            # record_frame определит этап на основе elapsed_time (или использует текущий этап)
            self.performance_monitor.record_frame(elapsed_time)

        # НЕ вызываем self.update() здесь, чтобы избежать бесконечного цикла
        # update() вызывается из benchmark_controller._perform_actions()

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

        shift_sensitivity = 0.00285 / self.scale_factor  # Коэффициент чувствительности смещения

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


# Альтернативная реализация с использованием Vulkan
if VULKAN_AVAILABLE:
    class VulkanWidget(QWidget):
        """
        Виджет для визуализации облаков точек с использованием Vulkan API.
        Точки хранятся в GPU-буферах и отрисовываются через командные буферы Vulkan.

        Требования:
        - Установленный пакет vulkan-python: pip install vulkan
        - Vulkan SDK и драйверы на системе

        Основные возможности:
        - Загрузка облаков точек (.las, .pcd) в GPU-буферы
        - Загрузка моделей (.obj) в GPU-буферы
        - Управление трансформациями (масштаб, поворот, перенос)
        - Создание и запись командных буферов для отрисовки

        Использование:
            widget = VulkanWidget(parent)
            widget.load_point_cloud("path/to/cloud.las")
            widget.show()

        Примечание: Для полного рендеринга требуется интеграция с QVulkanWindow
        или создание swapchain, render pass и graphics pipeline. Текущая реализация
        предоставляет инфраструктуру для работы с буферами и командными буферами.
        """

        def __init__(self, parent=None):
            super(VulkanWidget, self).__init__(parent)
            self.point_clouds = {}
            self.models = {}
            self.scale_factor = 2
            self.last_mouse_position = None
            self.rotation_x = 1
            self.rotation_y = 1
            self.rotation_z = 1
            self.rotation_mode = "Z"
            self.point_cloud_position = QPointF(0, 0)

            # Vulkan структуры
            self.instance = None
            self.physical_device = None
            self.device = None
            self.queue = None
            self.command_pool = None
            self.command_buffers = []
            self.render_pass = None
            self.pipeline = None
            self.pipeline_layout = None
            self.descriptor_set_layout = None
            self.descriptor_pool = None
            self.descriptor_sets = []

            # Буферы для данных
            self.vulkan_buffers = {}  # {filename: (vertex_buffer, color_buffer, num_points, vertex_memory, color_memory)}
            self.vulkan_buffers_models = {}

            # Матрицы трансформации
            self.projection_matrix = np.eye(4, dtype=np.float32)
            self.view_matrix = np.eye(4, dtype=np.float32)
            self.model_matrix = np.eye(4, dtype=np.float32)

            # Uniform буфер для матриц
            self.uniform_buffer = None
            self.uniform_memory = None

            # Инициализация Vulkan
            self._init_vulkan()

            # Инициализация uniform буфера
            self._init_uniform_buffer()

            self.vbo_data = self.vulkan_buffers
            self.vbo_data_models = self.vulkan_buffers_models

        def _init_vulkan(self):
            """Инициализация Vulkan instance и устройств"""
            try:
                # Создание Vulkan instance
                app_info = vk.VkApplicationInfo(
                    pApplicationName="Point Cloud Viewer",
                    applicationVersion=vk.VK_MAKE_VERSION(1, 0, 0),
                    pEngineName="No Engine",
                    engineVersion=vk.VK_MAKE_VERSION(1, 0, 0),
                    apiVersion=vk.VK_API_VERSION_1_0
                )

                create_info = vk.VkInstanceCreateInfo(
                    pApplicationInfo=app_info

                )

                self.instance = vk.vkCreateInstance(create_info, None)

                # Выбор физического устройства
                physical_devices = vk.vkEnumeratePhysicalDevices(self.instance)
                if not physical_devices:
                    raise RuntimeError("No Vulkan physical devices found")

                self.physical_device = physical_devices[0]

                # Получение свойств устройства
                queue_family_properties = vk.vkGetPhysicalDeviceQueueFamilyProperties(self.physical_device)
                graphics_queue_family_index = None

                for i, props in enumerate(queue_family_properties):
                    if props.queueFlags & vk.VK_QUEUE_GRAPHICS_BIT:
                        graphics_queue_family_index = i
                        break

                if graphics_queue_family_index is None:
                    raise RuntimeError("No graphics queue family found")

                # Создание логического устройства
                queue_priority = 1.0
                queue_create_info = vk.VkDeviceQueueCreateInfo(
                    queueFamilyIndex=graphics_queue_family_index,
                    queueCount=1,
                    pQueuePriorities=[queue_priority]
                )

                device_create_info = vk.VkDeviceCreateInfo(
                    queueCreateInfoCount=1,
                    pQueueCreateInfos=[queue_create_info]
                )

                self.device = vk.vkCreateDevice(self.physical_device, device_create_info, None)

                # Получение очереди
                self.queue = vk.vkGetDeviceQueue(self.device, graphics_queue_family_index, 0)

                # Создание пула команд
                command_pool_info = vk.VkCommandPoolCreateInfo(
                    flags=vk.VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT,
                    queueFamilyIndex=graphics_queue_family_index
                )
                self.command_pool = vk.vkCreateCommandPool(self.device, command_pool_info, None)

                print("Vulkan initialized successfully")

            except Exception as e:
                print(f"Failed to initialize Vulkan: {e}")
                raise

        def _init_uniform_buffer(self):
            """Инициализация uniform буфера для матриц трансформации"""
            if not self.device:
                return

            # Размер буфера для MVP матрицы (4x4 float32 = 64 байта)
            buffer_size = 16 * 4  # 16 элементов * 4 байта

            try:
                self.uniform_buffer, self.uniform_memory = self._create_buffer(
                    buffer_size,
                    vk.VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT,
                    vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT
                )

                # Инициализация начальными значениями
                initial_mvp = np.eye(4, dtype=np.float32)
                mvp_flat = np.ascontiguousarray(initial_mvp.flatten()).astype(np.float32)
                self._update_buffer_data(self.uniform_buffer, self.uniform_memory, mvp_flat)
            except Exception as e:
                import traceback
                print(f"Failed to create uniform buffer: {e}\n{traceback.format_exc()}")
                self.uniform_buffer = None
                self.uniform_memory = None

        def _create_buffer(self, size, usage, properties):
            """Создание буфера и выделение памяти"""
            # Убеждаемся, что size является целым числом (VkDeviceSize)
            buffer_size = int(size)
            if buffer_size <= 0:
                raise ValueError(f"Buffer size must be positive, got {buffer_size}")

            try:
                buffer_info = vk.VkBufferCreateInfo(
                    size=buffer_size,
                    usage=usage,
                    sharingMode=vk.VK_SHARING_MODE_EXCLUSIVE
                )

                buffer = vk.vkCreateBuffer(self.device, buffer_info, None)

                # Получение требований к памяти
                mem_requirements = vk.vkGetBufferMemoryRequirements(self.device, buffer)

                # Поиск подходящего типа памяти
                mem_properties = vk.vkGetPhysicalDeviceMemoryProperties(self.physical_device)
                memory_type_index = None

                for i in range(mem_properties.memoryTypeCount):
                    if (mem_requirements.memoryTypeBits & (1 << i)) and \
                            (mem_properties.memoryTypes[i].propertyFlags & properties) == properties:
                        memory_type_index = i
                        break

                if memory_type_index is None:
                    # Попробуем найти хотя бы HOST_VISIBLE память
                    for i in range(mem_properties.memoryTypeCount):
                        if (mem_requirements.memoryTypeBits & (1 << i)) and \
                                (mem_properties.memoryTypes[i].propertyFlags & vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT):
                            memory_type_index = i
                            break

                    if memory_type_index is None:
                        raise RuntimeError("Failed to find suitable memory type")

                # Выделение памяти
                alloc_info = vk.VkMemoryAllocateInfo(
                    allocationSize=mem_requirements.size,
                    memoryTypeIndex=memory_type_index
                )

                memory = vk.vkAllocateMemory(self.device, alloc_info, None)
                vk.vkBindBufferMemory(self.device, buffer, memory, 0)

                return buffer, memory
            except Exception as e:
                raise RuntimeError(f"Failed to create buffer: {e}") from e

        def _update_buffer_data(self, buffer, memory, data):
            """Обновление данных в буфере (Исправленная версия с поддержкой C-contiguous)"""
            import ctypes

            # Убеждаемся, что данные являются C-contiguous массивом
            if isinstance(data, np.ndarray):
                if not data.flags['C_CONTIGUOUS']:
                    data = np.ascontiguousarray(data, dtype=data.dtype)
            else:
                # Если это не numpy массив, конвертируем
                data = np.ascontiguousarray(data, dtype=np.float32)

            data_size = data.nbytes

            # 1. Маппинг памяти
            mapped_ptr = vk.vkMapMemory(self.device, memory, 0, data_size, 0)

            try:
                # 2. Пытаемся получить "сырой" адрес памяти (int)
                ptr_address = getattr(mapped_ptr, "value", mapped_ptr)

                # 3. Выбираем способ копирования
                if isinstance(ptr_address, int):
                    # ПУТЬ А: У нас есть адрес памяти (int) - используем memmove
                    src = data.ctypes.data_as(ctypes.POINTER(ctypes.c_byte))
                    dst = ctypes.cast(ptr_address, ctypes.POINTER(ctypes.c_byte))
                    ctypes.memmove(dst, src, data_size)

                else:
                    # ПУТЬ Б: mapped_ptr - это буферный объект - используем memoryview
                    # Убеждаемся, что данные C-contiguous перед созданием memoryview
                    dst_mv = memoryview(mapped_ptr).cast('B')
                    src_mv = memoryview(data).cast('B')
                    dst_mv[:data_size] = src_mv[:data_size]

            finally:
                vk.vkUnmapMemory(self.device, memory)

        def load_point_cloud(self, filename):
            """Загрузка облака точек в GPU-буферы Vulkan"""
            if filename not in self.point_clouds:
                self.point_clouds[filename] = {'active': False, 'data': None}

            if filename in self.vulkan_buffers:
                self.point_clouds[filename]['active'] = True
                self.update()
                return

            # Загрузка данных
            file_extension = os.path.splitext(filename)[1].lower()
            if file_extension == '.las':
                las = laspy.read(filename)
                points = np.vstack((las.x, las.y, las.z)).transpose()
                colors = np.vstack((las.red, las.green, las.blue)).transpose() / 255.0
            elif file_extension == '.pcd':
                pcd = o3d.io.read_point_cloud(filename)
                points = np.asarray(pcd.points)
                colors = np.ones_like(points)
            elif file_extension == '.csv':
                return
            else:
                print("Unsupported file format")
                return

            raw_points = points.copy()
            points_centered = points - np.mean(points, axis=0)

            # Конвертация в float32
            points_data = np.array(points_centered, dtype=np.float32)
            colors_data = np.array(colors, dtype=np.float32)

            # Создание GPU-буферов
            points_size = points_data.nbytes
            colors_size = colors_data.nbytes

            vertex_buffer, vertex_memory = self._create_buffer(
                points_size,
                vk.VK_BUFFER_USAGE_VERTEX_BUFFER_BIT,
                vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT
            )

            color_buffer, color_memory = self._create_buffer(
                colors_size,
                vk.VK_BUFFER_USAGE_VERTEX_BUFFER_BIT,
                vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT
            )

            # Загрузка данных в буферы
            self._update_buffer_data(vertex_buffer, vertex_memory, points_data)
            self._update_buffer_data(color_buffer, color_memory, colors_data)

            # Сохранение буферов
            self.vulkan_buffers[filename] = (
                vertex_buffer, color_buffer, len(points_centered),
                vertex_memory, color_memory
            )
            self.point_clouds[filename] = {
                'active': True,
                'data': points_centered,
                'full_data': raw_points
            }

            self.scale_factor = self.calculate_scale_factor_for_all()
            self.update()

        def load_model(self, filename):
            """Загрузка модели в GPU-буферы Vulkan"""
            if filename not in self.models:
                self.models[filename] = {'active': False, 'data': None}

            if filename in self.vulkan_buffers_models:
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
                colors = np.ones((len(points), 3), dtype=np.float32)
            else:
                print("Unsupported file format")
                return

            points_centered = points - np.mean(points, axis=0)

            # Создание GPU-буферов с C-contiguous данными
            points_data = np.ascontiguousarray(points_centered, dtype=np.float32)
            colors_data = np.ascontiguousarray(colors, dtype=np.float32)

            vertex_buffer, vertex_memory = self._create_buffer(
                points_data.nbytes,
                vk.VK_BUFFER_USAGE_VERTEX_BUFFER_BIT,
                vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT
            )

            color_buffer, color_memory = self._create_buffer(
                colors_data.nbytes,
                vk.VK_BUFFER_USAGE_VERTEX_BUFFER_BIT,
                vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT
            )

            # Загрузка данных
            self._update_buffer_data(vertex_buffer, vertex_memory, points_data)
            self._update_buffer_data(color_buffer, color_memory, colors_data)

            self.vulkan_buffers_models[filename] = (
                vertex_buffer, color_buffer, len(points_centered),
                vertex_memory, color_memory
            )
            self.models[filename] = {
                'active': True,
                'data': points_centered,
                'num_polygons': total_faces
            }

            self.scale_factor = self.calculate_scale_factor_for_all()
            self.update()

        def calculate_scale_factor_for_all(self):
            """Вычисление масштабного коэффициента"""
            max_cloud = 0
            max_model = 0

            if self.vulkan_buffers:
                for key, buf_data in self.vulkan_buffers.items():
                    if self.point_clouds[key]['active']:
                        points = self.point_clouds[key]['data']
                        if points is not None and len(points) > 0:
                            size = np.max(points, axis=0) - np.min(points, axis=0)
                            max_cloud = max(max_cloud, np.max(size))

            if self.vulkan_buffers_models:
                for key, buf_data in self.vulkan_buffers_models.items():
                    if self.models[key]['active']:
                        points = self.models[key]['data']
                        if points is not None and len(points) > 0:
                            size = np.max(points, axis=0) - np.min(points, axis=0)
                            max_model = max(max_model, np.max(size))

            max_size = max(max_cloud, max_model)
            scale_factor = 1.5 / max_size if max_size != 0 else 1
            return scale_factor

        def set_view_parameters(self, x, y, z):
            """Установка параметров вида"""
            self.scale_factor = self.calculate_scale_factor_for_all()
            self.rotation_x = x
            self.rotation_y = y
            self.rotation_z = z
            self.point_cloud_position = QPointF(0, 0)
            self.update()

        def set_scale_factor(self, scale):
            """Установка масштабного коэффициента"""
            self.scale_factor = scale
            self.update()

        def _create_command_buffer(self):
            """Создание командного буфера для отрисовки"""
            alloc_info = vk.VkCommandBufferAllocateInfo(
                commandPool=self.command_pool,
                level=vk.VK_COMMAND_BUFFER_LEVEL_PRIMARY,
                commandBufferCount=1
            )

            command_buffers = vk.vkAllocateCommandBuffers(self.device, alloc_info)
            return command_buffers[0]

        def _record_command_buffer(self, command_buffer, render_pass_begin_info=None):
            """
            Запись команд отрисовки в командный буфер.

            Args:
                command_buffer: Командный буфер для записи
                render_pass_begin_info: Информация о начале render pass (если доступна)
            """
            begin_info = vk.VkCommandBufferBeginInfo(
                flags=vk.VK_COMMAND_BUFFER_USAGE_SIMULTANEOUS_USE_BIT
            )
            vk.vkBeginCommandBuffer(command_buffer, begin_info)

            # Начало render pass (если предоставлен)
            if render_pass_begin_info:
                vk.vkCmdBeginRenderPass(
                    command_buffer,
                    render_pass_begin_info,
                    vk.VK_SUBPASS_CONTENTS_INLINE
                )

            # Отрисовка облаков точек
            for filename, cloud_info in self.point_clouds.items():
                if cloud_info['active'] and filename in self.vulkan_buffers:
                    vertex_buffer, color_buffer, num_points, _, _ = self.vulkan_buffers[filename]

                    # Привязка вершинных буферов
                    offsets = [0]
                    vk.vkCmdBindVertexBuffers(
                        command_buffer,
                        0,  # firstBinding
                        1,  # bindingCount
                        [vertex_buffer],
                        offsets
                    )

                    vk.vkCmdBindVertexBuffers(
                        command_buffer,
                        1,  # binding для цветов
                        1,
                        [color_buffer],
                        offsets
                    )

                    # Отрисовка точек
                    vk.vkCmdDraw(
                        command_buffer,
                        num_points,  # vertexCount
                        1,  # instanceCount
                        0,  # firstVertex
                        0  # firstInstance
                    )

            # Отрисовка моделей
            for model, model_info in self.models.items():
                if model_info['active'] and model in self.vulkan_buffers_models:
                    vertex_buffer, color_buffer, num_indices, _, _ = self.vulkan_buffers_models[model]

                    offsets = [0]
                    vk.vkCmdBindVertexBuffers(command_buffer, 0, 1, [vertex_buffer], offsets)
                    vk.vkCmdBindVertexBuffers(command_buffer, 1, 1, [color_buffer], offsets)

                    # Отрисовка треугольников
                    vk.vkCmdDraw(command_buffer, num_indices, 1, 0, 0)

            # Конец render pass
            if render_pass_begin_info:
                vk.vkCmdEndRenderPass(command_buffer)

            vk.vkEndCommandBuffer(command_buffer)

        def _apply_transformations(self, points):
            """Применяет трансформации (масштаб, поворот, перенос) к точкам"""
            if len(points) == 0:
                return points
            
            import math
            
            # Конвертируем точки в однородные координаты (x, y, z, 1)
            if points.shape[1] == 3:
                homogeneous_points = np.ones((len(points), 4), dtype=np.float32)
                homogeneous_points[:, :3] = points
            else:
                homogeneous_points = points.copy()
            
            # Матрица масштабирования
            scale = self.scale_factor
            scale_matrix = np.array([
                [scale, 0, 0, 0],
                [0, scale, 0, 0],
                [0, 0, scale, 0],
                [0, 0, 0, 1]
            ], dtype=np.float32)
            
            # Матрицы поворота
            rx = math.radians(self.rotation_x)
            ry = math.radians(self.rotation_y)
            rz = math.radians(self.rotation_z)
            
            cos_x, sin_x = math.cos(rx), math.sin(rx)
            cos_y, sin_y = math.cos(ry), math.sin(ry)
            cos_z, sin_z = math.cos(rz), math.sin(rz)
            
            rot_x = np.array([
                [1, 0, 0, 0],
                [0, cos_x, -sin_x, 0],
                [0, sin_x, cos_x, 0],
                [0, 0, 0, 1]
            ], dtype=np.float32)
            
            rot_y = np.array([
                [cos_y, 0, sin_y, 0],
                [0, 1, 0, 0],
                [-sin_y, 0, cos_y, 0],
                [0, 0, 0, 1]
            ], dtype=np.float32)
            
            rot_z = np.array([
                [cos_z, -sin_z, 0, 0],
                [sin_z, cos_z, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1]
            ], dtype=np.float32)
            
            # Матрица переноса
            tx = self.point_cloud_position.x()
            ty = -self.point_cloud_position.y()
            translate_matrix = np.array([
                [1, 0, 0, tx],
                [0, 1, 0, ty],
                [0, 0, 1, 0],
                [0, 0, 0, 1]
            ], dtype=np.float32)
            
            # Комбинированная матрица модели
            # В OpenGL порядок вызова: glScale -> glTranslate -> glRotate
            # OpenGL применяет матрицы справа налево, поэтому фактический порядок: Rz * Ry * Rx * T * S
            # В матричном виде для применения к точкам: S * T * Rx * Ry * Rz
            # Но так как мы применяем к точкам (point' = M * point), нужен порядок: S * T * Rx * Ry * Rz
            # Однако для соответствия визуализации в OpenGL используем тот же порядок
            # Порядок: Scale -> Translate -> Rotate (Rx, Ry, Rz)
            # В матричном виде: Rz * Ry * Rx * T * S (применяется к точкам)
            model_matrix = rot_z @ rot_y @ rot_x @ translate_matrix @ scale_matrix
            
            # Применяем трансформацию ко всем точкам
            transformed = (model_matrix @ homogeneous_points.T).T
            
            # Возвращаем только x, y, z (убираем w)
            return transformed[:, :3]
        
        def _update_uniform_buffer(self):
            """Обновление uniform буфера с матрицами трансформации"""
            # Вычисление матриц трансформации
            import math

            # Матрица масштабирования
            scale = self.scale_factor
            scale_matrix = np.array([
                [scale, 0, 0, 0],
                [0, scale, 0, 0],
                [0, 0, scale, 0],
                [0, 0, 0, 1]
            ], dtype=np.float32)

            # Матрицы поворота
            rx = math.radians(self.rotation_x)
            ry = math.radians(self.rotation_y)
            rz = math.radians(self.rotation_z)

            cos_x, sin_x = math.cos(rx), math.sin(rx)
            cos_y, sin_y = math.cos(ry), math.sin(ry)
            cos_z, sin_z = math.cos(rz), math.sin(rz)

            rot_x = np.array([
                [1, 0, 0, 0],
                [0, cos_x, -sin_x, 0],
                [0, sin_x, cos_x, 0],
                [0, 0, 0, 1]
            ], dtype=np.float32)

            rot_y = np.array([
                [cos_y, 0, sin_y, 0],
                [0, 1, 0, 0],
                [-sin_y, 0, cos_y, 0],
                [0, 0, 0, 1]
            ], dtype=np.float32)

            rot_z = np.array([
                [cos_z, -sin_z, 0, 0],
                [sin_z, cos_z, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1]
            ], dtype=np.float32)

            # Матрица переноса
            tx = self.point_cloud_position.x()
            ty = -self.point_cloud_position.y()
            translate_matrix = np.array([
                [1, 0, 0, tx],
                [0, 1, 0, ty],
                [0, 0, 1, 0],
                [0, 0, 0, 1]
            ], dtype=np.float32)

            # Комбинированная матрица модели
            self.model_matrix = translate_matrix @ rot_z @ rot_y @ rot_x @ scale_matrix

            # Обновление uniform буфера, если он существует
            if self.uniform_buffer and self.uniform_memory:
                # Комбинированная MVP матрица
                mvp = self.projection_matrix @ self.view_matrix @ self.model_matrix
                # Убеждаемся, что матрица C-contiguous перед передачей
                mvp_flat = np.ascontiguousarray(mvp.flatten(), dtype=np.float32)
                self._update_buffer_data(self.uniform_buffer, self.uniform_memory, mvp_flat)

        def paintEvent(self, event):
            """
            Обработка события отрисовки.
            
            Примечание: Vulkan требует сложной настройки swapchain, framebuffers и pipeline.
            Для упрощения используем QPainter для базовой отрисовки, пока не будет полной реализации Vulkan.
            """
            from PyQt6.QtGui import QPainter, QColor, QPen
            from PyQt6.QtCore import QPointF
            
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Черный фон
            painter.fillRect(self.rect(), QColor(0, 0, 0))
            
            # Обновление uniform буфера с текущими трансформациями
            self._update_uniform_buffer()
            
            # Простая отрисовка точек через QPainter (временное решение)
            # В реальной реализации здесь должен быть полный Vulkan рендеринг
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            
            # Отрисовка облаков точек
            for filename, cloud_info in self.point_clouds.items():
                if cloud_info.get('active') and cloud_info.get('data') is not None:
                    points_data = cloud_info['data']
                    if len(points_data) > 0:
                        # Применяем трансформации к точкам
                        # Сначала применяем model_matrix (масштаб, поворот, перенос)
                        transformed_points = self._apply_transformations(points_data)
                        
                        # Проекция точек на экран
                        width = self.width()
                        height = self.height()
                        center_x = width / 2
                        center_y = height / 2
                        
                        # Отрисовываем только часть точек для производительности
                        step = max(1, len(transformed_points) // 10000)  # Ограничиваем количество точек
                        for i in range(0, len(transformed_points), step):
                            point = transformed_points[i]
                            if len(point) >= 3:
                                # Ортогональная проекция с учетом aspect ratio
                                aspect_ratio = width / height if height > 0 else 1.0
                                
                                # Применяем проекционную матрицу
                                if aspect_ratio > 1:
                                    x = point[0] / aspect_ratio
                                else:
                                    x = point[0]
                                y = point[1] * aspect_ratio if aspect_ratio <= 1 else point[1]
                                
                                # Масштабирование и центрирование
                                screen_x = int(center_x + x * 100)
                                screen_y = int(center_y - y * 100)  # Инвертируем Y для правильной ориентации
                                
                                if 0 <= screen_x < width and 0 <= screen_y < height:
                                    painter.drawPoint(screen_x, screen_y)
            
            # Создание и запись командного буфера (для будущего использования)
            if self.command_pool:
                try:
                    command_buffer = self._create_command_buffer()
                    self._record_command_buffer(command_buffer)
                except Exception as e:
                    # Игнорируем ошибки командного буфера, так как у нас нет полного Vulkan контекста
                    pass
            
            painter.end()
            
            # Записываем метрики производительности, если монитор установлен
            if self.performance_monitor is not None:
                # Получаем elapsed_time из benchmark_controller, если он существует и бенчмарк запущен
                elapsed_time = 0.0
                if hasattr(self.performance_monitor, 'benchmark_controller'):
                    controller = self.performance_monitor.benchmark_controller
                    # Проверяем, что контроллер существует и бенчмарк запущен
                    if controller is not None and hasattr(controller, 'is_running') and controller.is_running:
                        if hasattr(controller, 'elapsed_time'):
                            elapsed_time = controller.elapsed_time
                # Записываем метрики всегда, если монитор установлен
                # record_frame определит этап на основе elapsed_time (или использует текущий этап)
                self.performance_monitor.record_frame(elapsed_time)

        def resizeEvent(self, event):
            """Обработка изменения размера окна"""
            width = event.size().width()
            height = event.size().height()

            if height == 0:
                height = 1

            # Обновление проекционной матрицы
            aspect_ratio = width / height
            if aspect_ratio > 1:
                self.projection_matrix = np.array([
                    [1 / aspect_ratio, 0, 0, 0],
                    [0, 1, 0, 0],
                    [0, 0, 1, 0],
                    [0, 0, 0, 1]
                ], dtype=np.float32)
            else:
                self.projection_matrix = np.array([
                    [1, 0, 0, 0],
                    [0, aspect_ratio, 0, 0],
                    [0, 0, 1, 0],
                    [0, 0, 0, 1]
                ], dtype=np.float32)

            self.update()

        def mousePressEvent(self, event):
            """Обработка нажатия мыши"""
            self.last_mouse_position = event.position()
            if event.buttons() == Qt.MouseButton.MiddleButton:
                self.rotation_mode = "X" if self.rotation_mode == "Z" else "Z"
                self.update()

        def normalize_angle(self, angle):
            """Нормализация угла"""
            while angle < 0:
                angle += 360
            while angle >= 360:
                angle = 0
            return angle

        def mouseMoveEvent(self, event):
            """Обработка движения мыши"""
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

            shift_sensitivity = 0.00285 / self.scale_factor  # Коэффициент чувствительности смещения

            if (self.last_mouse_position and event.buttons() == Qt.MouseButton.RightButton):
                delta = event.position() - self.last_mouse_position
                self.point_cloud_position += delta * shift_sensitivity
                self.last_mouse_position = event.position()
                self.update()

        def mouseReleaseEvent(self, event):
            """Обработка отпускания мыши"""
            self.last_mouse_position = None

        def wheelEvent(self, event):
            """Обработка колесика мыши"""
            angle = event.angleDelta().y()
            scale_factor_change = 1.1

            if angle > 0:
                self.scale_factor *= scale_factor_change
            else:
                self.scale_factor /= scale_factor_change

            if self.scale_factor < 0.005:
                self.scale_factor = 0.005
            elif self.scale_factor > 100:
                self.scale_factor = 100

            self.update()

        def cleanup(self):
            """Очистка ресурсов Vulkan"""
            if not self.device:
                return

            try:
                # Освобождение буферов облаков точек
                for buf_data in self.vulkan_buffers.values():
                    if len(buf_data) >= 5:
                        if buf_data[0]:  # vertex_buffer
                            vk.vkDestroyBuffer(self.device, buf_data[0], None)
                        if buf_data[3]:  # vertex_memory
                            vk.vkFreeMemory(self.device, buf_data[3], None)
                        if buf_data[1]:  # color_buffer
                            vk.vkDestroyBuffer(self.device, buf_data[1], None)
                        if buf_data[4]:  # color_memory
                            vk.vkFreeMemory(self.device, buf_data[4], None)

                # Освобождение буферов моделей
                for buf_data in self.vulkan_buffers_models.values():
                    if len(buf_data) >= 5:
                        if buf_data[0]:
                            vk.vkDestroyBuffer(self.device, buf_data[0], None)
                        if buf_data[3]:
                            vk.vkFreeMemory(self.device, buf_data[3], None)
                        if buf_data[1]:
                            vk.vkDestroyBuffer(self.device, buf_data[1], None)
                        if buf_data[4]:
                            vk.vkFreeMemory(self.device, buf_data[4], None)

                # Освобождение uniform буфера
                if self.uniform_buffer:
                    vk.vkDestroyBuffer(self.device, self.uniform_buffer, None)
                if self.uniform_memory:
                    vk.vkFreeMemory(self.device, self.uniform_memory, None)

                # Освобождение командных буферов (если есть)
                if self.command_buffers and self.command_pool:
                    vk.vkFreeCommandBuffers(
                        self.device,
                        self.command_pool,
                        len(self.command_buffers),
                        self.command_buffers
                    )

                # Освобождение пула команд
                if self.command_pool:
                    vk.vkDestroyCommandPool(self.device, self.command_pool, None)

                # Уничтожение устройства
                if self.device:
                    vk.vkDestroyDevice(self.device, None)
                    self.device = None

                # Уничтожение instance
                if self.instance:
                    vk.vkDestroyInstance(self.instance, None)
                    self.instance = None

            except Exception as e:
                print(f"Error during Vulkan cleanup: {e}")

        def __del__(self):
            """Деструктор"""
            self.cleanup()
else:
    # Заглушка если Vulkan недоступен
    class VulkanWidget(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            print("VulkanWidget: Vulkan not available. Install vulkan-python package.")


def create_point_cloud_widget(backend=None, parent=None):
    """
    Фабричная функция для создания виджета визуализации облаков точек.

    Args:
        backend: 'opengl' или 'vulkan'. Если None, используется настройка из config.RENDERER_BACKEND
        parent: Родительский виджет

    Returns:
        OpenGLWidget или VulkanWidget в зависимости от выбранного бэкенда

    Примеры использования:
        # Использование настройки по умолчанию из config.py
        widget = create_point_cloud_widget(parent=window)

        # Явное указание бэкенда
        widget = create_point_cloud_widget(backend='vulkan', parent=window)
        widget = create_point_cloud_widget(backend='opengl', parent=window)
    """
    from desktop_segmentation_modeling.config import RENDERER_BACKEND

    if backend is None:
        backend = RENDERER_BACKEND

    backend = backend.lower()

    if backend == 'vulkan':
        if VULKAN_AVAILABLE:
            return VulkanWidget(parent)
        else:
            print("Vulkan requested but not available. Falling back to OpenGL.")
            return OpenGLWidget(parent)
    else:
        # По умолчанию используем OpenGL
        return OpenGLWidget(parent)
