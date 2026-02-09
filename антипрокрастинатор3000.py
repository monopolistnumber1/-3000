"""
Антипрокрастинатор 3000 - Полная версия с поддержкой iVCam
"""

import sys
import os
import time
import threading
import subprocess
import re
from datetime import datetime, timedelta

# Проверяем и устанавливаем необходимые библиотеки
def install_packages():
    required_packages = [
        'opencv-python',
        'PyQt5',
        'psutil',
        'numpy',
        'pygame-ce',
        'requests',
    ]
    
    print("Проверка и установка необходимых библиотек...")
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_').replace('.', '_').lower())
            print(f"✓ {package} уже установлен")
        except ImportError:
            print(f"⏳ Устанавливаю {package}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--quiet"])
                print(f"✓ {package} успешно установлен")
            except Exception as e:
                print(f"✗ Ошибка установки {package}: {e}")
                if package == 'pygame':
                    try:
                        subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame-ce", "--quiet"])
                        print("✓ pygame-ce успешно установлен")
                    except:
                        print("✗ Не удалось установить pygame. Звук будет недоступен")

# Устанавливаем библиотеки при первом запуске
if __name__ == "__main__":
    install_packages()

# Теперь импортируем все библиотеки
try:
    import cv2
    import numpy as np
    from PyQt5.QtWidgets import *
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    import psutil
    try:
        import pygame
    except:
        import pygame_ce as pygame
    import winsound
    import requests
    
    # Флаг успешной загрузки библиотек
    LIBS_LOADED = True
except ImportError as e:
    print(f"✗ Ошибка загрузки библиотек: {e}")
    LIBS_LOADED = False

class IVCamManager:
    """Менеджер для работы с iVCam"""
    
    def __init__(self):
        self.ivcam_connected = False
        self.cap = None
        self.camera_index = None
        self.ivcam_installed = False
        self.ivcam_running = False
        
    def detect_ivcam(self):
        """Поиск iVCam среди доступных камер"""
        print("🔍 Поиск iVCam...")
        
        # Сначала проверяем, установлен ли iVCam драйвер
        self.check_ivcam_installation()
        
        if not self.ivcam_installed:
            print("✗ iVCam не установлен на компьютере")
            return False
        
        # Пробуем найти iVCam среди камер
        max_cameras = 10
        for i in range(max_cameras):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    # Проверяем разрешение (iVCam обычно дает 640x480 или 1280x720)
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    
                    # iVCam обычно имеет специфические разрешения
                    if (width, height) in [(640, 480), (1280, 720), (1920, 1080)]:
                        print(f"✓ Найден iVCam на камере #{i} ({width}x{height})")
                        self.camera_index = i
                        cap.release()
                        return True
                cap.release()
        
        print("✗ iVCam не найден среди доступных камер")
        return False
    
    def check_ivcam_installation(self):
        """Проверка установки iVCam на компьютере"""
        try:
            # Проверяем Windows реестр или системные файлы
            import winreg
            
            try:
                # Проверяем ключ реестра iVCam
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
                
                for i in range(0, winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        subkey = winreg.OpenKey(key, subkey_name)
                        
                        try:
                            display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                            if "iVCam" in display_name:
                                print(f"✓ iVCam найден в системе: {display_name}")
                                self.ivcam_installed = True
                                return True
                        except:
                            pass
                    except:
                        continue
                        
            except Exception as e:
                print(f"Ошибка проверки реестра: {e}")
                
        except ImportError:
            # Если не Windows или нет winreg
            print("⚠️ Не могу проверить установку iVCam (не Windows система)")
            self.ivcam_installed = True  # Предполагаем, что установлен
        
        # Проверяем наличие драйвера через DirectShow
        try:
            cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
            if cap.isOpened():
                cap.release()
                self.ivcam_installed = True
                print("✓ Виртуальная камера обнаружена (возможно iVCam)")
                return True
        except:
            pass
        
        return False
    
    def start_ivcam(self, camera_index=None):
        """Запуск iVCam"""
        if camera_index is not None:
            self.camera_index = camera_index
        
        if self.camera_index is None:
            # Автопоиск iVCam
            if not self.detect_ivcam():
                return False
        
        try:
            # Используем DirectShow для Windows
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            
            if self.cap.isOpened():
                # Настраиваем параметры для лучшей производительности
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap.set(cv2.CAP_PROP_FPS, 30)
                
                # Пробуем прочитать первый кадр
                ret, frame = self.cap.read()
                if ret:
                    print(f"✓ iVCam подключен на камере #{self.camera_index}")
                    self.ivcam_connected = True
                    self.ivcam_running = True
                    return True
                else:
                    self.cap.release()
                    self.cap = None
                    return False
            else:
                return False
                
        except Exception as e:
            print(f"✗ Ошибка подключения к iVCam: {e}")
            return False
    
    def get_frame(self):
        """Получение кадра с iVCam"""
        if self.cap and self.ivcam_connected:
            ret, frame = self.cap.read()
            if ret:
                return frame
        return None
    
    def release(self):
        """Освобождение ресурсов iVCam"""
        if self.cap:
            self.cap.release()
            self.cap = None
        self.ivcam_connected = False
        self.ivcam_running = False
    
    def is_connected(self):
        """Проверка подключения iVCam"""
        return self.ivcam_connected
    
    def get_connection_info(self):
        """Получение информации о подключении"""
        if self.cap and self.ivcam_connected:
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.cap.get(cv2.CAP_PROP_FPS)
        else:
            width = height = fps = 0
        
        return {
            'connected': self.ivcam_connected,
            'camera_index': self.camera_index,
            'resolution': f"{width}x{height}",
            'fps': fps,
            'installed': self.ivcam_installed
        }
    
    def scan_all_cameras(self):
        """Сканирование всех доступных камер для отладки"""
        print("📡 Сканирование всех камер...")
        cameras = []
        
        max_cameras = 10
        for i in range(max_cameras):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                
                cameras.append({
                    'index': i,
                    'width': width,
                    'height': height,
                    'fps': fps
                })
                
                print(f"  Камера #{i}: {width}x{height} @ {fps}FPS")
                cap.release()
            else:
                print(f"  Камера #{i}: недоступна")
        
        return cameras


class EyeTrackerApp(QMainWindow):
    """Главное окно приложения с поддержкой iVCam"""
    
    # Сигналы для межпоточного взаимодействия
    update_timer_signal = pyqtSignal(str)
    update_progress_signal = pyqtSignal(int)
    update_status_signal = pyqtSignal(str, str)
    update_face_status_signal = pyqtSignal(str, str)
    update_camera_status_signal = pyqtSignal(str, str)
    timer_finished_signal = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        
        if not LIBS_LOADED:
            self.show_error_dialog()
            return
            
        self.init_variables()
        self.init_ui()
        self.connect_signals()
        self.setup_ivcam()
    
    def show_error_dialog(self):
        """Показать сообщение об ошибке загрузки библиотек"""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("Ошибка загрузки библиотек")
        msg.setInformativeText(
            "Не удалось загрузить необходимые библиотеки.\n"
            "Убедитесь, что установлены:\n"
            "- opencv-python\n- PyQt5\n- psutil\n- numpy\n- pygame-ce\n- requests"
        )
        msg.setWindowTitle("Ошибка")
        msg.exec_()
        sys.exit(1)
    
    def init_variables(self):
        """Инициализация переменных"""
        # Основные переменные
        self.is_tracking = False
        self.timer_running = False
        self.timer_paused = False
        self.timer_seconds = 0
        self.alarm_playing = False
        self.face_detected = False
        self.camera_index = 0
        self.use_ivcam = False
        
        # Потоки
        self.timer_thread = None
        self.tracking_thread = None
        
        # Менеджер iVCam
        self.ivcam_manager = IVCamManager()
        
        # Инициализация звука
        try:
            pygame.mixer.init()
        except:
            print("Предупреждение: не удалось инициализировать звук")
        
        # Загрузка каскадов Haar
        try:
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            self.eye_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_eye.xml'
            )
        except:
            print("Предупреждение: не удалось загрузить каскады Haar")
            self.face_cascade = None
            self.eye_cascade = None
    
    def setup_ivcam(self):
        """Настройка iVCam"""
        # Проверяем доступность iVCam
        self.check_ivcam_availability()
    
    def check_ivcam_availability(self):
        """Проверка доступности iVCam"""
        # В отдельном потоке проверяем iVCam
        threading.Thread(target=self._check_ivcam_thread, daemon=True).start()
    
    def _check_ivcam_thread(self):
        """Фоновая проверка iVCam"""
        time.sleep(2)  # Даем время на загрузку интерфейса
        
        # Проверяем установку iVCam
        ivcam_installed = self.ivcam_manager.check_ivcam_installation()
        
        if ivcam_installed:
            # Сканируем камеры
            cameras = self.ivcam_manager.scan_all_cameras()
            
            # Обновляем список камер в интерфейсе
            QTimer.singleShot(0, lambda: self.update_camera_list(cameras))
            
            self.update_camera_status_signal.emit(
                "✅ iVCam обнаружен в системе",
                "green"
            )
        else:
            self.update_camera_status_signal.emit(
                "⚠️ iVCam не установлен",
                "orange"
            )
    
    def update_camera_list(self, cameras):
        """Обновление списка камер в интерфейсе"""
        self.camera_combo.clear()
        self.camera_combo.addItem("Автоопределение")
        
        for cam in cameras:
            self.camera_combo.addItem(
                f"Камера #{cam['index']} ({cam['width']}x{cam['height']})"
            )
        
        # Обновляем ivcam_combo
        self.ivcam_combo.clear()
        self.ivcam_combo.addItem("Автоопределение iVCam")
        for cam in cameras:
            self.ivcam_combo.addItem(
                f"Камера #{cam['index']} ({cam['width']}x{cam['height']})"
            )
    
    def init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle("👁️ Антипрокрастинатор 3000 v3.0 - iVCam Edition")
        self.setGeometry(100, 100, 1200, 800)
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Главный layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Заголовок
        title = QLabel("👁️ Антипрокрастинатор 3000 - С поддержкой iVCam")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #2c3e50;
            padding: 10px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #3498db, stop:0.5 #9b59b6, stop:1 #e74c3c);
            color: white;
            border-radius: 10px;
        """)
        main_layout.addWidget(title)
        
        # Контейнер для основных виджетов
        container = QHBoxLayout()
        
        # Левая панель - таймер и статус
        left_panel = QVBoxLayout()
        
        # Группа таймера
        timer_group = QGroupBox("⏱️ Таймер концентрации")
        timer_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3498db;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        timer_layout = QVBoxLayout()
        
        # Ввод времени
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("Время (минуты):"))
        self.time_spin = QSpinBox()
        self.time_spin.setRange(1, 240)
        self.time_spin.setValue(25)
        self.time_spin.setFixedWidth(80)
        time_layout.addWidget(self.time_spin)
        
        # Опции таймера
        self.auto_extend_checkbox = QCheckBox("Авто-продление")
        self.auto_extend_checkbox.setToolTip("Автоматически продлевать таймер, если вы работаете")
        time_layout.addWidget(self.auto_extend_checkbox)
        
        time_layout.addStretch()
        timer_layout.addLayout(time_layout)
        
        # Отображение таймера
        self.timer_label = QLabel("Таймер: Не активен")
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #e74c3c;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 5px;
            border: 1px solid #ddd;
        """)
        timer_layout.addWidget(self.timer_label)
        
        # Прогресс бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #3498db;
                border-radius: 5px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #2ecc71;
                border-radius: 3px;
            }
        """)
        timer_layout.addWidget(self.progress_bar)
        
        # Кнопки управления
        button_layout = QHBoxLayout()
        self.start_btn = QPushButton("▶️ Старт таймера")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #229954;
                padding: 12px 24px;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.start_btn.clicked.connect(self.start_timer)
        button_layout.addWidget(self.start_btn)
        
        self.pause_btn = QPushButton("⏸️ Пауза")
        self.pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #d68910;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.pause_btn.clicked.connect(self.pause_timer)
        self.pause_btn.setEnabled(False)
        button_layout.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton("⏹️ Стоп")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_timer)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)
        
        timer_layout.addLayout(button_layout)
        timer_group.setLayout(timer_layout)
        left_panel.addWidget(timer_group)
        
        # Группа статуса
        status_group = QGroupBox("📊 Статус системы")
        status_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #2ecc71;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """)
        
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("📡 Отслеживание неактивно")
        self.status_label.setStyleSheet("""
            font-size: 12px; 
            padding: 8px;
            background-color: #f8f9fa;
            border-radius: 3px;
        """)
        status_layout.addWidget(self.status_label)
        
        self.face_status_label = QLabel("😐 Лицо: Не обнаружено")
        self.face_status_label.setStyleSheet("""
            font-size: 12px; 
            padding: 8px;
            background-color: #fff5f5;
            border-radius: 3px;
        """)
        status_layout.addWidget(self.face_status_label)
        
        self.eyes_status_label = QLabel("👁️ Глаза: Не обнаружены")
        self.eyes_status_label.setStyleSheet("""
            font-size: 12px; 
            padding: 8px;
            background-color: #fff5f5;
            border-radius: 3px;
        """)
        status_layout.addWidget(self.eyes_status_label)
        
        self.camera_status_label = QLabel("📷 Камера: Не выбрана")
        self.camera_status_label.setStyleSheet("""
            font-size: 12px; 
            padding: 8px;
            background-color: #f0f8ff;
            border-radius: 3px;
        """)
        status_layout.addWidget(self.camera_status_label)
        
        self.alarm_status_label = QLabel("🔇 Сигнал: Выключен")
        self.alarm_status_label.setStyleSheet("""
            font-size: 12px; 
            padding: 8px;
            background-color: #f0fff4;
            border-radius: 3px;
        """)
        status_layout.addWidget(self.alarm_status_label)
        
        # Информация о iVCam
        self.ivcam_info_label = QLabel("📱 iVCam: Не проверен")
        self.ivcam_info_label.setStyleSheet("""
            font-size: 12px; 
            padding: 8px;
            background-color: #f5f0ff;
            border-radius: 3px;
        """)
        status_layout.addWidget(self.ivcam_info_label)
        
        status_group.setLayout(status_layout)
        left_panel.addWidget(status_group)
        
        container.addLayout(left_panel)
        
        # Центральная панель - камеры
        center_panel = QVBoxLayout()
        
        # Группа выбора камеры
        camera_group = QGroupBox("📷 Выбор камеры")
        camera_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #9b59b6;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """)
        
        camera_layout = QVBoxLayout()
        
        # Переключатель типа камеры
        cam_type_layout = QHBoxLayout()
        cam_type_layout.addWidget(QLabel("Тип камеры:"))
        
        self.camera_type_combo = QComboBox()
        self.camera_type_combo.addItems(["Встроенная камера ПК", "iVCam (телефон через USB)"])
        self.camera_type_combo.currentIndexChanged.connect(self.on_camera_type_changed)
        cam_type_layout.addWidget(self.camera_type_combo)
        
        camera_layout.addLayout(cam_type_layout)
        
        # Для встроенной камеры
        self.pc_camera_frame = QWidget()
        pc_camera_layout = QVBoxLayout(self.pc_camera_frame)
        
        pc_cam_layout = QHBoxLayout()
        pc_cam_layout.addWidget(QLabel("Камера ПК:"))
        self.camera_combo = QComboBox()
        self.camera_combo.addItems(["Автоопределение", "Камера 0", "Камера 1", "Камера 2"])
        pc_cam_layout.addWidget(self.camera_combo)
        
        self.test_cam_btn = QPushButton("🔍 Тест камеры")
        self.test_cam_btn.clicked.connect(self.test_camera)
        self.test_cam_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 8px 15px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        pc_cam_layout.addWidget(self.test_cam_btn)
        
        self.scan_cameras_btn = QPushButton("📡 Сканировать камеры")
        self.scan_cameras_btn.clicked.connect(self.scan_cameras)
        self.scan_cameras_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                padding: 8px 15px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        pc_cam_layout.addWidget(self.scan_cameras_btn)
        
        pc_camera_layout.addLayout(pc_cam_layout)
        camera_layout.addWidget(self.pc_camera_frame)
        
        # Для iVCam
        self.ivcam_frame = QWidget()
        self.ivcam_frame.setVisible(False)
        ivcam_layout = QVBoxLayout(self.ivcam_frame)
        
        # Выбор iVCam камеры
        ivcam_selection_layout = QHBoxLayout()
        ivcam_selection_layout.addWidget(QLabel("iVCam камера:"))
        
        self.ivcam_combo = QComboBox()
        self.ivcam_combo.addItems(["Автоопределение iVCam", "Камера 1", "Камера 2", "Камера 3"])
        ivcam_selection_layout.addWidget(self.ivcam_combo)
        
        self.ivcam_test_btn = QPushButton("📱 Тест iVCam")
        self.ivcam_test_btn.clicked.connect(self.test_ivcam)
        self.ivcam_test_btn.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                padding: 8px 15px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
        """)
        ivcam_selection_layout.addWidget(self.ivcam_test_btn)
        
        ivcam_layout.addLayout(ivcam_selection_layout)
        
        # Кнопки управления iVCam
        ivcam_buttons_layout = QHBoxLayout()
        
        self.ivcam_check_btn = QPushButton("🔍 Проверить iVCam")
        self.ivcam_check_btn.clicked.connect(self.check_ivcam)
        self.ivcam_check_btn.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                padding: 8px 15px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d68910;
            }
        """)
        ivcam_buttons_layout.addWidget(self.ivcam_check_btn)
        
        self.ivcam_help_btn = QPushButton("❓ Помощь iVCam")
        self.ivcam_help_btn.clicked.connect(self.show_ivcam_help)
        self.ivcam_help_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 8px 15px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        ivcam_buttons_layout.addWidget(self.ivcam_help_btn)
        
        ivcam_layout.addLayout(ivcam_buttons_layout)
        
        # Статус iVCam
        self.ivcam_status_label = QLabel("iVCam не проверен")
        self.ivcam_status_label.setWordWrap(True)
        self.ivcam_status_label.setStyleSheet("""
            font-size: 11px;
            color: #7f8c8d;
            padding: 8px;
            background-color: #f8f9fa;
            border-radius: 3px;
            border: 1px solid #ddd;
        """)
        ivcam_layout.addWidget(self.ivcam_status_label)
        
        camera_layout.addWidget(self.ivcam_frame)
        
        # Предпросмотр камеры
        self.camera_preview = QLabel("Камера не активна")
        self.camera_preview.setAlignment(Qt.AlignCenter)
        self.camera_preview.setMinimumHeight(250)
        self.camera_preview.setStyleSheet("""
            QLabel {
                background-color: black;
                color: white;
                border: 2px solid #ccc;
                border-radius: 5px;
                font-size: 14px;
                padding: 10px;
            }
        """)
        camera_layout.addWidget(self.camera_preview)
        
        camera_group.setLayout(camera_layout)
        center_panel.addWidget(camera_group)
        
        container.addLayout(center_panel)
        
        # Правая панель - статистика и настройки
        right_panel = QVBoxLayout()
        
        # Панель статистики
        stats_group = QGroupBox("📈 Статистика и настройки")
        stats_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #34495e;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """)
        
        stats_layout = QVBoxLayout()
        
        # Статистика
        self.stats_label = QLabel("Сессия: 0 минут\nФокус: 0%\nОтвлечений: 0")
        self.stats_label.setStyleSheet("""
            font-size: 12px;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 5px;
            border: 1px solid #ddd;
        """)
        stats_layout.addWidget(self.stats_label)
        
        # Настройки отслеживания
        sensitivity_layout = QHBoxLayout()
        sensitivity_layout.addWidget(QLabel("Чувствительность:"))
        self.sensitivity_slider = QSlider(Qt.Horizontal)
        self.sensitivity_slider.setRange(1, 10)
        self.sensitivity_slider.setValue(5)
        self.sensitivity_slider.setTickPosition(QSlider.TicksBelow)
        self.sensitivity_slider.setTickInterval(1)
        sensitivity_layout.addWidget(self.sensitivity_slider)
        stats_layout.addLayout(sensitivity_layout)
        
        # Чекбоксы настроек
        self.enable_sound_checkbox = QCheckBox("Включить звуковые сигналы")
        self.enable_sound_checkbox.setChecked(True)
        stats_layout.addWidget(self.enable_sound_checkbox)
        
        self.strict_mode_checkbox = QCheckBox("Строгий режим (сигнал при малейшем отвлечении)")
        stats_layout.addWidget(self.strict_mode_checkbox)
        
        stats_group.setLayout(stats_layout)
        right_panel.addWidget(stats_group)
        
        # Информационная панель
        info_group = QGroupBox("ℹ️ Информация")
        info_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3498db;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """)
        
        info_layout = QVBoxLayout()
        
        info_text = QLabel(
            "👁️ <b>Антипрокрастинатор 3000</b><br><br>"
            "• Отслеживает ваше лицо и глаза<br>"
            "• Сигнализирует при отвлечении<br>"
            "• Поддержка iVCam и камер ПК<br>"
            "• Статистика продуктивности<br>"
            "• Настраиваемая чувствительность"
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("""
            font-size: 11px;
            padding: 10px;
            background-color: #f0f8ff;
            border-radius: 5px;
            border: 1px solid #ddd;
        """)
        info_layout.addWidget(info_text)
        
        info_group.setLayout(info_layout)
        right_panel.addWidget(info_group)
        
        # Кнопка помощи
        help_btn = QPushButton("❓ Помощь")
        help_btn.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                padding: 12px 24px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
        """)
        help_btn.clicked.connect(self.show_help)
        right_panel.addWidget(help_btn)
        
        container.addLayout(right_panel)
        main_layout.addLayout(container)
        
        # Статус бар
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов к работе. Проверьте iVCam подключение.")
        
        # Инициализация статистики
        self.session_start_time = None
        self.focus_time = 0
        self.distraction_count = 0
        self.total_session_time = 0
    
    def connect_signals(self):
        """Подключение сигналов"""
        self.update_timer_signal.connect(self.update_timer_display)
        self.update_progress_signal.connect(self.progress_bar.setValue)
        self.update_status_signal.connect(self.update_status_display)
        self.update_face_status_signal.connect(self.update_face_status_display)
        self.update_camera_status_signal.connect(self.update_camera_status_display)
        self.timer_finished_signal.connect(self.on_timer_finished)
    
    def show_help(self):
        """Показать общую справку"""
        help_text = """
        <h3>👁️ Антипрокрастинатор 3000 - Помощь</h3>
        
        <b>Основные функции:</b>
        • Отслеживание лица и глаз через камеру
        • Таймер концентрации (25 минут по умолчанию)
        • Звуковые сигналы при отвлечении
        • Поддержка iVCam (камера телефона)
        • Статистика продуктивности
        
        <b>Как использовать:</b>
        1. Выберите тип камеры (ПК или iVCam)
        2. Настройте таймер (25-240 минут)
        3. Нажмите "Старт таймера"
        4. Смотрите на экран во время работы
        
        <b>Советы:</b>
        • Используйте iVCam для лучшего угла обзора
        • Отрегулируйте чувствительность под себя
        • Включите строгий режим для максимальной фокусировки
        """
        
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Помощь")
        msg.setText(help_text)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
    
    def on_camera_type_changed(self, index):
        """Обработка изменения типа камеры"""
        self.use_ivcam = (index == 1)  # 0 = ПК, 1 = iVCam
        
        if self.use_ivcam:
            self.pc_camera_frame.setVisible(False)
            self.ivcam_frame.setVisible(True)
            self.camera_status_label.setText("📱 Камера: iVCam (не подключен)")
            self.status_bar.showMessage("Выбрана камера iVCam. Проверьте подключение.")
            
            # Проверяем iVCam
            self.check_ivcam()
        else:
            self.pc_camera_frame.setVisible(True)
            self.ivcam_frame.setVisible(False)
            self.camera_status_label.setText("💻 Камера: ПК (не активна)")
            self.status_bar.showMessage("Выбрана встроенная камера ПК.")
        
        # Останавливаем текущую камеру
        self.ivcam_manager.release()
    
    def update_camera_status_display(self, text, color):
        """Обновление статуса камеры"""
        self.camera_status_label.setText(text)
        self.camera_status_label.setStyleSheet(f"color: {color};")
    
    def check_ivcam(self):
        """Проверка iVCam"""
        self.status_bar.showMessage("🔍 Проверка iVCam...")
        
        # В отдельном потоке проверяем iVCam
        threading.Thread(target=self._check_ivcam_thread_main, daemon=True).start()
    
    def _check_ivcam_thread_main(self):
        """Поток проверки iVCam"""
        # Проверяем установку
        installed = self.ivcam_manager.check_ivcam_installation()
        
        if installed:
            # Сканируем камеры
            cameras = self.ivcam_manager.scan_all_cameras()
            
            # Обновляем интерфейс
            QTimer.singleShot(0, lambda: self.update_camera_list(cameras))
            
            self.update_camera_status_signal.emit(
                "✅ iVCam обнаружен в системе",
                "green"
            )
            
            # Обновляем статус iVCam
            cam_info = "✅ iVCam установлен\n"
            for cam in cameras:
                cam_info += f"Камера #{cam['index']}: {cam['width']}x{cam['height']}\n"
            
            QTimer.singleShot(0, lambda: self.ivcam_status_label.setText(cam_info))
            QTimer.singleShot(0, lambda: self.ivcam_info_label.setText("📱 iVCam: Установлен и готов"))
            
            QTimer.singleShot(0, lambda: self.status_bar.showMessage(
                f"iVCam обнаружен! Найдено {len(cameras)} камер.", 5000
            ))
        else:
            self.update_camera_status_signal.emit(
                "⚠️ iVCam не найден",
                "orange"
            )
            QTimer.singleShot(0, lambda: self.ivcam_status_label.setText(
                "iVCam не найден. Убедитесь, что:\n"
                "1. iVCam установлен на компьютере\n"
                "2. iVCam запущен на телефоне\n"
                "3. Телефон подключен через USB"
            ))
            QTimer.singleShot(0, lambda: self.status_bar.showMessage(
                "iVCam не найден. Проверьте установку.", 5000
            ))
    
    def test_ivcam(self):
        """Тестирование iVCam"""
        self.status_bar.showMessage("Тестирование iVCam...")
        
        # Получаем выбранную камеру
        selected_index = self.ivcam_combo.currentIndex()
        camera_index = None
        
        if selected_index == 0:
            # Автоопределение
            camera_index = None
        else:
            # Парсим номер камеры из текста
            text = self.ivcam_combo.currentText()
            match = re.search(r'Камера #(\d+)', text)
            if match:
                camera_index = int(match.group(1))
        
        # В отдельном потоке тестируем
        threading.Thread(target=self._test_ivcam_thread, daemon=True, args=(camera_index,)).start()
    
    def _test_ivcam_thread(self, camera_index):
        """Поток тестирования iVCam"""
        try:
            # Запускаем iVCam
            if self.ivcam_manager.start_ivcam(camera_index):
                # Пробуем получить кадр
                frame = self.ivcam_manager.get_frame()
                
                if frame is not None:
                    info = self.ivcam_manager.get_connection_info()
                    
                    self.update_camera_status_signal.emit(
                        f"✅ iVCam подключен (камера #{info['camera_index']})",
                        "green"
                    )
                    
                    # Показываем тестовое изображение
                    self.show_test_frame(frame)
                    
                    # Обновляем статус
                    QTimer.singleShot(0, lambda: self.ivcam_status_label.setText(
                        f"iVCam работает!\n"
                        f"Камера: #{info['camera_index']}\n"
                        f"Разрешение: {info['resolution']}\n"
                        f"FPS: {info['fps']:.1f}"
                    ))
                    
                    QTimer.singleShot(0, lambda: self.status_bar.showMessage(
                        f"iVCam успешно подключен! Камера #{info['camera_index']}", 5000
                    ))
                    
                    # Закрываем соединение после теста
                    time.sleep(3)
                    self.ivcam_manager.release()
                    
                    return
        except Exception as e:
            print(f"Ошибка тестирования iVCam: {e}")
        
        self.update_camera_status_signal.emit(
            "❌ Не удалось подключиться к iVCam",
            "red"
        )
        QTimer.singleShot(0, lambda: self.ivcam_status_label.setText(
            "Не удалось подключиться к iVCam.\n"
            "Убедитесь, что:\n"
            "1. iVCam запущен на телефоне\n"
            "2. Телефон подключен по USB\n"
            "3. На телефоне разрешена отладка по USB"
        ))
        QTimer.singleShot(0, lambda: self.status_bar.showMessage(
            "Не удалось подключиться к iVCam. Проверьте подключение.", 5000
        ))
    
    def show_ivcam_help(self):
        """Показать справку по iVCam"""
        help_text = """
        <h3>📱 Инструкция по настройке iVCam</h3>
        
        <b>1. Установка на телефон:</b>
        • Установите <b>iVCam</b> из App Store (iOS) или Google Play (Android)
        
        <b>2. Установка на компьютер:</b>
        • Скачайте iVCam с официального сайта: <b>http://www.e2esoft.com/ivcam/</b>
        • Установите программу на компьютер
        
        <b>3. Настройка подключения:</b>
        • Подключите телефон к компьютеру через USB
        • <b>На Android:</b> Включите "Отладку по USB" в настройках разработчика
        • Запустите iVCam на телефоне и компьютере
        
        <b>4. Проверка:</b>
        • Нажмите "Проверить iVCam" в программе
        • Если iVCam найден, выберите камеру из списка
        • Нажмите "Тест iVCam" для проверки изображения
        
        <b>5. Если не работает:</b>
        • Перезагрузите телефон и компьютер
        • Переустановите iVCam на компьютере
        • Попробуйте другой USB-кабель
        """
        
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Помощь по iVCam")
        msg.setText(help_text)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
    
    def scan_cameras(self):
        """Сканирование всех камер"""
        self.status_bar.showMessage("📡 Сканирование камер...")
        
        threading.Thread(target=self._scan_cameras_thread, daemon=True).start()
    
    def _scan_cameras_thread(self):
        """Поток сканирования камер"""
        cameras = []
        max_cameras = 10
        
        for i in range(max_cameras):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                
                cameras.append({
                    'index': i,
                    'width': width,
                    'height': height,
                    'fps': fps
                })
                cap.release()
        
        # Обновляем интерфейс
        QTimer.singleShot(0, lambda: self.update_camera_list(cameras))
        
        if cameras:
            info = f"Найдено {len(cameras)} камер:\n"
            for cam in cameras:
                info += f"• Камера #{cam['index']}: {cam['width']}x{cam['height']}\n"
            
            QTimer.singleShot(0, lambda: self.ivcam_status_label.setText(info))
            QTimer.singleShot(0, lambda: self.status_bar.showMessage(
                f"Найдено {len(cameras)} камер", 5000
            ))
        else:
            QTimer.singleShot(0, lambda: self.ivcam_status_label.setText(
                "Камеры не найдены. Убедитесь, что камеры подключены."
            ))
            QTimer.singleShot(0, lambda: self.status_bar.showMessage(
                "Камеры не найдены", 5000
            ))
    
    def show_test_frame(self, frame):
        """Показать тестовый кадр"""
        # Добавляем текст "Тест iVCam"
        cv2.putText(frame, "Тест iVCam - РАБОТАЕТ", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        # Конвертируем для Qt
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        
        # Масштабируем и отображаем
        scaled_pixmap = pixmap.scaled(self.camera_preview.size(), 
                                     Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.camera_preview.setPixmap(scaled_pixmap)
    
    def test_camera(self):
        """Тестирование встроенной камеры"""
        try:
            # Парсим номер камеры из текста
            text = self.camera_combo.currentText()
            camera_index = 0
            
            if text != "Автоопределение":
                match = re.search(r'Камера #(\d+)', text)
                if match:
                    camera_index = int(match.group(1))
                else:
                    # Если нет номера в тексте, берем индекс
                    camera_index = self.camera_combo.currentIndex()
            
            cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
            
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                
                if ret:
                    # Показываем тестовый кадр
                    self.show_test_frame(frame)
                    
                    self.update_camera_status_signal.emit(
                        f"💻 Камера ПК #{camera_index} работает",
                        "green"
                    )
                    self.status_bar.showMessage(f"Камера #{camera_index} работает нормально!", 3000)
                else:
                    QMessageBox.warning(self, "Ошибка", "Не удалось получить изображение")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось открыть камеру")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при тестировании камеры:\n{str(e)}")
    
    def start_timer(self):
        """Запуск таймера"""
        try:
            minutes = self.time_spin.value()
            if minutes <= 0:
                QMessageBox.warning(self, "Ошибка", "Введите положительное число минут")
                return
            
            # Проверка камеры
            if self.use_ivcam:
                # Получаем выбранную камеру iVCam
                selected_index = self.ivcam_combo.currentIndex()
                camera_index = None
                
                if selected_index == 0:
                    # Автоопределение
                    camera_index = None
                else:
                    # Парсим номер камеры
                    text = self.ivcam_combo.currentText()
                    match = re.search(r'Камера #(\d+)', text)
                    if match:
                        camera_index = int(match.group(1))
                
                # Запускаем iVCam
                if not self.ivcam_manager.start_ivcam(camera_index):
                    QMessageBox.warning(self, "Ошибка", 
                                      "Не удалось подключиться к iVCam.\n"
                                      "Проверьте:\n"
                                      "1. iVCam запущен на телефоне и компьютере\n"
                                      "2. Телефон подключен по USB\n"
                                      "3. На телефоне включена отладка по USB")
                    return
                
                info = self.ivcam_manager.get_connection_info()
                self.update_camera_status_signal.emit(
                    f"📱 iVCam подключен (камера #{info['camera_index']})",
                    "green"
                )
            else:
                # Проверяем встроенную камеру
                text = self.camera_combo.currentText()
                camera_index = 0
                
                if text != "Автоопределение":
                    match = re.search(r'Камера #(\d+)', text)
                    if match:
                        camera_index = int(match.group(1))
                    else:
                        camera_index = self.camera_combo.currentIndex()
                
                cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    QMessageBox.warning(self, "Ошибка", "Не удалось открыть встроенную камеру")
                    return
                cap.release()
                
                self.update_camera_status_signal.emit(
                    f"💻 Камера ПК #{camera_index} активна",
                    "green"
                )
            
            self.timer_seconds = minutes * 60
            self.is_tracking = True
            self.timer_running = True
            self.timer_paused = False
            
            # Инициализация статистики
            self.session_start_time = time.time()
            self.focus_time = 0
            self.distraction_count = 0
            self.total_session_time = 0
            self.last_face_time = time.time()
            
            # Обновляем интерфейс
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            self.status_label.setText("✅ Отслеживание активно")
            self.status_bar.showMessage(f"Таймер запущен на {minutes} минут")
            
            # Запускаем потоки
            self.timer_thread = threading.Thread(target=self.run_timer, daemon=True)
            self.tracking_thread = threading.Thread(target=self.track_eyes, daemon=True)
            
            self.timer_thread.start()
            self.tracking_thread.start()
            
            camera_type = "iVCam (телефон)" if self.use_ivcam else "ПК"
            self.status_bar.showMessage(f"Таймер установлен на {minutes} минут. Отслеживание через {camera_type} активировано.", 3000)
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить таймер:\n{str(e)}")
            self.stop_timer()
    
    def pause_timer(self):
        """Пауза таймера"""
        if self.timer_paused:
            # Возобновляем
            self.timer_paused = False
            self.pause_btn.setText("⏸️ Пауза")
            self.status_bar.showMessage("Таймер возобновлен")
            self.status_label.setText("▶️ Отслеживание возобновлено")
        else:
            # Ставим на паузу
            self.timer_paused = True
            self.pause_btn.setText("▶️ Продолжить")
            self.status_bar.showMessage("Таймер на паузе")
            self.status_label.setText("⏸️ Отслеживание на паузе")
    
    def stop_timer(self):
        """Остановка таймера"""
        self.is_tracking = False
        self.timer_running = False
        self.timer_paused = False
        
        # Останавливаем iVCam
        self.ivcam_manager.release()
        
        # Обновляем интерфейс
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setText("⏸️ Пауза")
        
        self.status_label.setText("📡 Отслеживание неактивно")
        self.timer_label.setText("Таймер: Не активен")
        self.face_status_label.setText("😐 Лицо: Не обнаружено")
        self.eyes_status_label.setText("👁️ Глаза: Не обнаружены")
        self.alarm_status_label.setText("🔇 Сигнал: Выключен")
        self.alarm_status_label.setStyleSheet("color: #27ae60;")
        
        # Останавливаем звук
        self.alarm_playing = False
        
        # Обновляем статистику
        if self.session_start_time:
            session_duration = time.time() - self.session_start_time
            focus_percentage = (self.focus_time / session_duration * 100) if session_duration > 0 else 0
            self.stats_label.setText(
                f"Сессия: {int(session_duration/60)} минут\n"
                f"Фокус: {focus_percentage:.1f}%\n"
                f"Отвлечений: {self.distraction_count}"
            )
        
        self.status_bar.showMessage("Таймер остановлен", 3000)
    
    def run_timer(self):
        """Выполнение таймера в отдельном потоке"""
        try:
            start_time = time.time()
            end_time = start_time + self.timer_seconds
            last_update = time.time()
            
            while self.timer_running and time.time() < end_time:
                if not self.timer_paused:
                    current_time = time.time()
                    remaining = int(end_time - current_time)
                    minutes = remaining // 60
                    seconds = remaining % 60
                    
                    # Обновляем каждую секунду или чаще
                    if current_time - last_update >= 0.1:  # Обновляем каждые 100 мс
                        # Обновляем таймер
                        self.update_timer_signal.emit(f"{minutes:02d}:{seconds:02d}")
                        
                        # Обновляем прогресс бар (более плавно)
                        progress = 100 - int((remaining / self.timer_seconds) * 100)
                        self.update_progress_signal.emit(progress)
                        
                        last_update = current_time
                
                time.sleep(0.05)  # Чаще проверяем состояние
            
            if self.timer_running:
                self.timer_finished_signal.emit()
                
        except Exception as e:
            print(f"Ошибка в таймере: {e}")
    
    def update_timer_display(self, time_str):
        """Обновление отображения таймера"""
        self.timer_label.setText(f"Таймер: {time_str}")
    
    def on_timer_finished(self):
        """Действия при завершении таймера"""
        self.stop_timer()
        
        # Воспроизводим звук завершения
        self.play_completion_sound()
        
        # Показываем статистику
        session_duration = time.time() - self.session_start_time if self.session_start_time else 0
        focus_percentage = (self.focus_time / session_duration * 100) if session_duration > 0 else 0
        
        QMessageBox.information(self, "Время вышло!",
                              f"🎉 Отличная работа!\n\n"
                              f"📊 Статистика сессии:\n"
                              f"• Длительность: {int(session_duration/60)} минут\n"
                              f"• Время в фокусе: {focus_percentage:.1f}%\n"
                              f"• Отвлечений: {self.distraction_count}\n\n"
                              f"Можно отдохнуть 5-10 минут.")
    
    def track_eyes(self):
        """Отслеживание глаз в отдельном потоке"""
        cap = None
        
        try:
            if self.use_ivcam:
                # Используем iVCam
                print("Начато отслеживание через iVCam...")
            else:
                # Используем встроенную камеру
                text = self.camera_combo.currentText()
                camera_index = 0
                
                if text != "Автоопределение":
                    match = re.search(r'Камера #(\d+)', text)
                    if match:
                        camera_index = int(match.group(1))
                    else:
                        camera_index = self.camera_combo.currentIndex()
                
                cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
                
                if not cap.isOpened():
                    self.update_status_signal.emit("error", "Не удалось открыть камеру ПК")
                    return
                
                # Устанавливаем разрешение
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                print("Начато отслеживание через камеру ПК...")
            
            frame_counter = 0
            no_face_frames = 0
            last_face_time = time.time()
            
            while self.is_tracking and not self.timer_paused:
                # Получаем кадр
                if self.use_ivcam:
                    frame = self.ivcam_manager.get_frame()
                    if frame is None:
                        time.sleep(0.05)
                        continue
                else:
                    ret, frame = cap.read()
                    if not ret:
                        break
                
                frame_counter += 1
                if frame_counter % 2 != 0:  # Обрабатываем каждый второй кадр
                    continue
                
                # Зеркальное отражение (только для фронтальной камеры)
                if not self.use_ivcam:
                    frame = cv2.flip(frame, 1)
                
                # Преобразуем в оттенки серого
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                face_detected = False
                eyes_detected = False
                
                # Детекция лиц
                if self.face_cascade is not None:
                    faces = self.face_cascade.detectMultiScale(
                        gray,
                        scaleFactor=1.1,
                        minNeighbors=5,
                        minSize=(50, 50)
                    )
                    
                    if len(faces) > 0:
                        face_detected = True
                        no_face_frames = 0
                        last_face_time = time.time()
                        
                        # Обновляем статистику фокуса
                        self.focus_time += 0.05  # Примерно время между кадрами
                        
                        # Детекция глаз
                        for (x, y, w, h) in faces:
                            roi_gray = gray[y:y+h, x:x+w]
                            if self.eye_cascade is not None:
                                eyes = self.eye_cascade.detectMultiScale(roi_gray)
                                if len(eyes) >= 1:  # Хотя бы один глаз
                                    eyes_detected = True
                                    break
                    else:
                        no_face_frames += 1
                
                # Определяем статус
                if face_detected:
                    if eyes_detected:
                        status = "Смотрим на экран"
                        status_color = "green"
                        if self.alarm_playing:
                            self.alarm_playing = False
                    else:
                        status = "Глаза не видны"
                        status_color = "orange"
                else:
                    if no_face_frames > 15:  # Если лицо не найдено 15 кадров подряд
                        status = "Отвернулись от экрана"
                        status_color = "red"
                        
                        # Проверяем, прошло ли достаточно времени с последнего отвлечения
                        if time.time() - last_face_time > 3:  # 3 секунды
                            self.distraction_count += 1
                            last_face_time = time.time()
                            
                        if not self.alarm_playing and self.enable_sound_checkbox.isChecked():
                            self.alarm_playing = True
                            self.play_alarm()
                    else:
                        status = "Лицо не обнаружено"
                        status_color = "red"
                
                # Отправляем статус в GUI
                self.update_face_status_signal.emit(
                    "😀 Лицо: Обнаружено" if face_detected else "😐 Лицо: Не обнаружено",
                    "green" if face_detected else "red"
                )
                
                self.update_status_signal.emit(
                    f"👁️ {status}",
                    status_color
                )
                
                # Обновляем статистику в реальном времени
                if self.session_start_time:
                    session_duration = time.time() - self.session_start_time
                    focus_percentage = (self.focus_time / session_duration * 100) if session_duration > 0 else 0
                    QTimer.singleShot(0, lambda: self.stats_label.setText(
                        f"Сессия: {int(session_duration/60)} мин\n"
                        f"Фокус: {focus_percentage:.1f}%\n"
                        f"Отвлечений: {self.distraction_count}"
                    ))
                
                # Обновляем предпросмотр камеры
                self.update_camera_preview(frame, face_detected, eyes_detected)
                
                time.sleep(0.05)  # Небольшая задержка
                
        except Exception as e:
            print(f"Ошибка в отслеживании глаз: {e}")
        finally:
            if cap:
                cap.release()
            if self.use_ivcam:
                self.ivcam_manager.release()
    
    def update_camera_preview(self, frame, face_detected, eyes_detected):
        """Обновление предпросмотра камеры"""
        try:
            # Рисуем рамки для отладки
            if face_detected and self.face_cascade is not None:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, 1.1, 5)
                for (x, y, w, h) in faces:
                    color = (0, 255, 0) if eyes_detected else (0, 165, 255)  # Зеленый если глаза, оранжевый если нет
                    cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                    
                    # Детекция глаз внутри лица
                    roi_gray = gray[y:y+h, x:x+w]
                    if self.eye_cascade is not None:
                        eyes = self.eye_cascade.detectMultiScale(roi_gray)
                        for (ex, ey, ew, eh) in eyes:
                            cv2.rectangle(frame, (x+ex, y+ey), (x+ex+ew, y+ey+eh), (255, 0, 0), 1)
            
            # Добавляем текст статуса
            status_text = "✅ В фокусе" if (face_detected and eyes_detected) else "❌ Отвлеклись"
            color = (0, 255, 0) if (face_detected and eyes_detected) else (0, 0, 255)
            cv2.putText(frame, status_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
            # Добавляем время
            if self.session_start_time:
                elapsed = int(time.time() - self.session_start_time)
                time_text = f"Время: {elapsed//60:02d}:{elapsed%60:02d}"
                cv2.putText(frame, time_text, (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Конвертируем для Qt
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            
            # Масштабируем и отображаем
            scaled_pixmap = pixmap.scaled(self.camera_preview.size(), 
                                         Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.camera_preview.setPixmap(scaled_pixmap)
        except Exception as e:
            print(f"Ошибка обновления предпросмотра: {e}")
    
    def update_status_display(self, text, color):
        """Обновление статуса глаз"""
        self.eyes_status_label.setText(text)
        self.eyes_status_label.setStyleSheet(f"color: {color};")
    
    def update_face_status_display(self, text, color):
        """Обновление статуса лица"""
        self.face_status_label.setText(text)
        self.face_status_label.setStyleSheet(f"color: {color};")
    
    def play_alarm(self):
        """Воспроизведение звукового сигнала"""
        if not self.enable_sound_checkbox.isChecked():
            return
            
        try:
            # Используем winsound для Windows
            winsound.Beep(1000, 300)
            
            # Обновляем статус
            self.alarm_status_label.setText("🔊 Сигнал: Включен")
            self.alarm_status_label.setStyleSheet("color: #e74c3c;")
            
            # Запускаем поток для повторения сигнала
            threading.Thread(target=self.repeat_alarm, daemon=True).start()
        except:
            # Если winsound не работает, пробуем pygame
            try:
                pygame.mixer.init()
                pygame.mixer.Sound.play(pygame.mixer.Sound(buffer=bytes([128]*8000)))
                self.alarm_status_label.setText("🔊 Сигнал: Включен")
                self.alarm_status_label.setStyleSheet("color: #e74c3c;")
                threading.Thread(target=self.repeat_alarm_pygame, daemon=True).start()
            except:
                self.alarm_status_label.setText("⚠️ Сигнал: Ошибка")
                self.alarm_status_label.setStyleSheet("color: #f39c12;")
    
    def repeat_alarm(self):
        """Повторение звукового сигнала (winsound)"""
        while self.alarm_playing and self.is_tracking and not self.timer_paused:
            try:
                winsound.Beep(1000, 300)
                time.sleep(1)
            except:
                break
    
    def repeat_alarm_pygame(self):
        """Повторение звукового сигнала (pygame)"""
        while self.alarm_playing and self.is_tracking and not self.timer_paused:
            try:
                pygame.mixer.Sound.play(pygame.mixer.Sound(buffer=bytes([128]*8000)))
                time.sleep(1)
            except:
                break
    
    def play_completion_sound(self):
        """Воспроизведение звука завершения"""
        if not self.enable_sound_checkbox.isChecked():
            return
            
        try:
            winsound.Beep(1000, 500)
            winsound.Beep(1200, 300)
            winsound.Beep(1400, 200)
        except:
            try:
                pygame.mixer.init()
                pygame.mixer.Sound.play(pygame.mixer.Sound(buffer=bytes([128]*16000)))
            except:
                pass
    
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        reply = QMessageBox.question(self, "Выход",
                                   "Вы уверены, что хотите выйти?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.stop_timer()
            event.accept()
        else:
            event.ignore()


def main():
    """Главная функция"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Создаем и показываем главное окно
    window = EyeTrackerApp()
    
    # Центрируем окно
    window.show()
    
    # Получаем размеры экрана
    screen = QApplication.primaryScreen()
    screen_geometry = screen.geometry()
    window_geometry = window.frameGeometry()
    
    # Центрируем окно
    window.move(
        screen_geometry.center() - window_geometry.center()
    )
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()