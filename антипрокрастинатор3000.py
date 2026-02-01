import sys
import os
import time
import threading
import cv2
import numpy as np
import pygame
import psutil
import winsound
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class EyeTrackerApp(QMainWindow):
    update_timer_signal = pyqtSignal(str)
    update_status_signal = pyqtSignal(str, str)
    update_alarm_signal = pyqtSignal(str, str)
    update_face_status_signal = pyqtSignal(str, str)
    show_block_window_signal = pyqtSignal(str)
    update_camera_preview_signal = pyqtSignal(QPixmap)
    timer_finished_signal = pyqtSignal()
    volume_warning_signal = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.init_variables()
        self.init_ui()
        self.setup_signals()
        self.setup_audio_control()
        
    def init_variables(self):
        """Инициализация переменных"""
        try:
            pygame.mixer.init()
        except:
            pass
        
        # Основные переменные
        self.is_tracking = False
        self.timer_running = False
        self.timer_seconds = 0
        self.blacklist = []
        self.eye_detected = True
        self.alarm_playing = False
        self.camera_index = 0
        
        # Потоки
        self.timer_thread = None
        self.tracking_thread = None
        self.monitoring_thread = None
        self.audio_monitor_thread = None
        
        # Камера
        self.cap = None
        
        # Словарь для хранения окон блокировки
        self.block_windows = {}
        
        # Список всех процессов для автодополнения
        self.all_processes = []
        self.update_process_list()
        
        # Инициализация детектора лица
        try:
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            self.eye_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_eye.xml'
            )
        except:
            self.face_cascade = None
            self.eye_cascade = None
    
    def setup_audio_control(self):
        """Настройка контроля громкости"""
        self.volume_monitoring = False
        self.min_volume = 20  # Минимальная громкость в процентах
    
    def setup_signals(self):
        """Настройка соединений сигналов и слотов"""
        self.update_timer_signal.connect(self.update_timer_display)
        self.update_status_signal.connect(self.update_status_display)
        self.update_alarm_signal.connect(self.update_alarm_display)
        self.update_face_status_signal.connect(self.update_face_status_display)
        self.show_block_window_signal.connect(self.create_block_window)
        self.update_camera_preview_signal.connect(self.update_camera_preview)
        self.timer_finished_signal.connect(self.on_timer_finished)
        self.volume_warning_signal.connect(self.show_volume_warning)
    
    def update_process_list(self):
        """Обновление списка всех процессов для автодополнения"""
        self.all_processes = []
        try:
            for proc in psutil.process_iter(['name']):
                try:
                    name = proc.info['name']
                    if name:
                        # Убираем расширение .exe
                        if name.lower().endswith('.exe'):
                            name = name[:-4]
                        if name not in self.all_processes:
                            self.all_processes.append(name)
                except:
                    continue
        except:
            pass
    
    def init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle("антипрокрастинатор3000 - Концентрация внимания")
        self.setGeometry(100, 100, 1000, 800)
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Главный layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Заголовок
        title_label = QLabel("антипрокрастинатор3000 - Контроль концентрации")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont("Arial", 18, QFont.Bold)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)
        
        # Контейнер для основной информации
        info_container = QHBoxLayout()
        
        # Левая колонка - Таймер и статус
        left_column = QVBoxLayout()
        
        # Группа таймера
        timer_group = QGroupBox("⏱️ Таймер концентрации")
        timer_layout = QVBoxLayout()
        
        # Ввод времени
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("Время (минут):"))
        self.time_spin = QSpinBox()
        self.time_spin.setRange(1, 120)
        self.time_spin.setValue(25)
        self.time_spin.setFixedWidth(80)
        time_layout.addWidget(self.time_spin)
        time_layout.addStretch()
        timer_layout.addLayout(time_layout)
        
        # Отображение таймера
        self.timer_display = QLabel("Таймер: Не активен")
        self.timer_display.setFont(QFont("Arial", 16, QFont.Bold))
        self.timer_display.setAlignment(Qt.AlignCenter)
        timer_layout.addWidget(self.timer_display)
        
        # Кнопки управления таймером
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("▶️ Старт таймера")
        self.start_btn.clicked.connect(self.start_timer)
        self.start_btn.setMinimumHeight(40)
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ Стоп таймера")
        self.stop_btn.clicked.connect(self.stop_timer)
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white;")
        btn_layout.addWidget(self.stop_btn)
        
        timer_layout.addLayout(btn_layout)
        timer_group.setLayout(timer_layout)
        left_column.addWidget(timer_group)
        
        # Группа статуса
        status_group = QGroupBox("📊 Статус отслеживания")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("📡 Отслеживание неактивно")
        self.status_label.setFont(QFont("Arial", 11))
        status_layout.addWidget(self.status_label)
        
        self.face_status_label = QLabel("😐 Лицо: Не обнаружено")
        status_layout.addWidget(self.face_status_label)
        
        self.eye_status_label = QLabel("👁️ Глаза: Не обнаружены")
        status_layout.addWidget(self.eye_status_label)
        
        self.alarm_status_label = QLabel("🔇 Сигнал: Выключен")
        self.alarm_status_label.setStyleSheet("color: green;")
        status_layout.addWidget(self.alarm_status_label)
        
        self.volume_status_label = QLabel("🔊 Громкость: Норма")
        self.volume_status_label.setStyleSheet("color: green;")
        status_layout.addWidget(self.volume_status_label)
        
        status_group.setLayout(status_layout)
        left_column.addWidget(status_group)
        
        info_container.addLayout(left_column)
        
        # Правая колонка - Черный список
        right_column = QVBoxLayout()
        
        # Группа добавления приложений
        add_group = QGroupBox("🚫 Черный список приложений")
        add_layout = QVBoxLayout()
        
        # Поле ввода с автодополнением
        self.app_input = QLineEdit()
        self.app_input.setPlaceholderText("Введите название приложения (например: chrome, telegram)...")
        self.app_input.textChanged.connect(self.update_autocomplete)
        add_layout.addWidget(self.app_input)
        
        # Виджет для подсказок
        self.suggestions_list = QListWidget()
        self.suggestions_list.setMaximumHeight(150)
        self.suggestions_list.itemClicked.connect(self.select_suggestion)
        self.suggestions_list.hide()
        add_layout.addWidget(self.suggestions_list)
        
        # Кнопка добавления
        self.add_btn = QPushButton("➕ Добавить в черный список")
        self.add_btn.clicked.connect(self.add_to_blacklist)
        add_layout.addWidget(self.add_btn)
        
        add_group.setLayout(add_layout)
        right_column.addWidget(add_group)
        
        # Список заблокированных приложений
        list_group = QGroupBox("Заблокированные приложения")
        list_layout = QVBoxLayout()
        
        self.blacklist_widget = QListWidget()
        list_layout.addWidget(self.blacklist_widget)
        
        # Кнопки управления списком
        list_btn_layout = QHBoxLayout()
        self.clear_btn = QPushButton("🗑️ Очистить список")
        self.clear_btn.clicked.connect(self.clear_blacklist)
        list_btn_layout.addWidget(self.clear_btn)
        
        self.remove_btn = QPushButton("❌ Удалить выбранное")
        self.remove_btn.clicked.connect(self.remove_from_blacklist)
        list_btn_layout.addWidget(self.remove_btn)
        
        list_layout.addLayout(list_btn_layout)
        list_group.setLayout(list_layout)
        right_column.addWidget(list_group)
        
        info_container.addLayout(right_column)
        
        main_layout.addLayout(info_container)
        
        # Панель камеры
        camera_group = QGroupBox("📷 Настройки камеры")
        camera_layout = QHBoxLayout()
        
        # Выбор камеры
        cam_layout = QVBoxLayout()
        cam_layout.addWidget(QLabel("Выберите камеру:"))
        self.camera_combo = QComboBox()
        self.camera_combo.addItems(["Камера 0", "Камера 1", "Камера 2", "Камера 3"])
        cam_layout.addWidget(self.camera_combo)
        
        # Кнопка теста камеры
        self.test_cam_btn = QPushButton("🔍 Тест камеры")
        self.test_cam_btn.clicked.connect(self.test_camera)
        cam_layout.addWidget(self.test_cam_btn)
        camera_layout.addLayout(cam_layout)
        
        # Предпросмотр камеры
        preview_layout = QVBoxLayout()
        self.camera_label = QLabel("Камера не активна")
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setMinimumHeight(200)
        self.camera_label.setStyleSheet("""
            QLabel {
                background-color: black;
                color: white;
                border: 1px solid #ccc;
                border-radius: 5px;
                font-size: 14px;
            }
        """)
        preview_layout.addWidget(self.camera_label)
        
        # Чекбокс для отображения камеры
        self.show_camera_check = QCheckBox("Показывать изображение с камеры")
        self.show_camera_check.stateChanged.connect(self.toggle_camera_preview)
        preview_layout.addWidget(self.show_camera_check)
        
        camera_layout.addLayout(preview_layout)
        camera_group.setLayout(camera_layout)
        main_layout.addWidget(camera_group)
        
        # Информационная панель
        info_group = QGroupBox("📋 Инструкция")
        info_layout = QVBoxLayout()
        
        info_text = QLabel("""
        <b>Инструкция по использованию:</b><br><br>
        1. <b>Установите время работы</b> (в минутах)<br>
        2. <b>Добавьте приложения в черный список</b> - просто введите название (chrome, telegram, steam и т.д.)<br>
        3. <b>Нажмите "Старт таймера"</b><br>
        4. <b>Сядьте так, чтобы камера видела ваше лицо</b><br>
        5. <b>Во время работы таймера:</b><br>
           - Система следит за вашими глазами через камеру<br>
           - При отводе взгляда от экрана звучит сигнал<br>
           - Приложения из черного списка будут блокироваться<br>
           - Громкость не может быть ниже минимального уровня<br>
        6. <b>Таймер автоматически остановится</b> по истечении времени
        """)
        info_text.setWordWrap(True)
        info_text.setStyleSheet("font-size: 12px;")
        info_layout.addWidget(info_text)
        
        info_group.setLayout(info_layout)
        main_layout.addWidget(info_group)
        
        # Статус бар
        self.statusBar().showMessage("Готов к работе")
        
        # Применение стилей
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ccc;
                border-radius: 5px;
                margin-top: 5px;
                padding-top: 10px;
                font-size: 13px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
            QLineEdit, QSpinBox, QComboBox, QListWidget {
                padding: 6px;
                border: 1px solid #ccc;
                border-radius: 3px;
                font-size: 12px;
            }
            QLabel {
                font-size: 12px;
            }
        """)
    
    def update_autocomplete(self, text):
        """Обновление автодополнения"""
        if not text:
            self.suggestions_list.hide()
            return
        
        # Обновляем список процессов
        self.update_process_list()
        
        # Фильтруем процессы по введенному тексту
        suggestions = []
        search_text = text.lower()
        
        for process in self.all_processes:
            if search_text in process.lower():
                suggestions.append(process)
        
        # Ограничиваем количество подсказок
        suggestions = suggestions[:10]
        
        # Обновляем список подсказок
        self.suggestions_list.clear()
        
        if suggestions:
            for suggestion in suggestions:
                item = QListWidgetItem(suggestion)
                self.suggestions_list.addItem(item)
            self.suggestions_list.show()
        else:
            self.suggestions_list.hide()
    
    def select_suggestion(self, item):
        """Выбор подсказки из списка"""
        self.app_input.setText(item.text())
        self.suggestions_list.hide()
        self.app_input.setFocus()
    
    def add_to_blacklist(self):
        """Добавление приложения в черный список"""
        app_name = self.app_input.text().strip()
        
        if not app_name:
            QMessageBox.warning(self, "Предупреждение", "Введите название приложения")
            return
        
        # Проверяем, нет ли уже такого приложения в списке
        for i in range(self.blacklist_widget.count()):
            if self.blacklist_widget.item(i).text() == app_name:
                QMessageBox.warning(self, "Предупреждение", "Это приложение уже есть в черном списке")
                self.app_input.clear()
                return
        
        # Добавляем в список
        self.blacklist.append(app_name)
        self.blacklist_widget.addItem(app_name)
        self.app_input.clear()
        self.suggestions_list.hide()
        
        self.statusBar().showMessage(f"Приложение '{app_name}' добавлено в черный список", 3000)
        QMessageBox.information(self, "Успех", f"Приложение '{app_name}' добавлено в черный список")
    
    def remove_from_blacklist(self):
        """Удаление выбранного приложения из черного списка"""
        selected_items = self.blacklist_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Предупреждение", "Выберите приложение для удаления")
            return
        
        for item in selected_items:
            app_name = item.text()
            if app_name in self.blacklist:
                self.blacklist.remove(app_name)
            self.blacklist_widget.takeItem(self.blacklist_widget.row(item))
            
            # Закрываем окно блокировки, если оно открыто
            if app_name in self.block_windows:
                window = self.block_windows[app_name]
                window.close()
                del self.block_windows[app_name]
        
        self.statusBar().showMessage("Приложение удалено из черного списка", 3000)
    
    def clear_blacklist(self):
        """Очистка черного списка"""
        if self.blacklist_widget.count() == 0:
            return
        
        reply = QMessageBox.question(self, "Подтверждение", 
                                   "Вы уверены, что хотите очистить весь черный список?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Закрываем все окна блокировки
            for app_name, window in self.block_windows.items():
                window.close()
            
            self.block_windows.clear()
            self.blacklist.clear()
            self.blacklist_widget.clear()
            self.statusBar().showMessage("Черный список очищен", 3000)
    
    def test_camera(self):
        """Тестирование камеры"""
        try:
            camera_index = self.camera_combo.currentIndex()
            cap = cv2.VideoCapture(camera_index)
            
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                
                if ret:
                    QMessageBox.information(self, "Успех", "Камера работает нормально!")
                else:
                    QMessageBox.warning(self, "Ошибка", "Не удалось получить изображение с камеры")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось открыть камеру")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при тестировании камеры: {str(e)}")
    
    def toggle_camera_preview(self, state):
        """Включение/выключение предпросмотра камеры"""
        if state == Qt.Checked and self.is_tracking:
            self.start_camera_preview()
        elif state == Qt.Unchecked:
            self.camera_label.setText("Камера не активна")
    
    def start_timer(self):
        """Запуск таймера и отслеживания"""
        try:
            minutes = self.time_spin.value()
            if minutes <= 0:
                QMessageBox.warning(self, "Ошибка", "Введите положительное число минут")
                return
            
            self.timer_seconds = minutes * 60
            self.is_tracking = True
            self.timer_running = True
            
            # Обновление интерфейса
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.status_label.setText("✅ Отслеживание активно")
            self.statusBar().showMessage(f"Таймер запущен на {minutes} минут")
            
            # Запуск таймера
            self.timer_thread = threading.Thread(target=self.run_timer, daemon=True)
            self.timer_thread.start()
            
            # Запуск отслеживания глаз
            self.tracking_thread = threading.Thread(target=self.run_eye_tracking, daemon=True)
            self.tracking_thread.start()
            
            # Запуск мониторинга приложений
            self.monitoring_thread = threading.Thread(target=self.monitor_applications, daemon=True)
            self.monitoring_thread.start()
            
            # Запуск мониторинга громкости
            self.audio_monitor_thread = threading.Thread(target=self.monitor_audio, daemon=True)
            self.audio_monitor_thread.start()
            
            # Запуск предпросмотра камеры, если включен
            if self.show_camera_check.isChecked():
                self.start_camera_preview()
            
            QMessageBox.information(self, "Таймер запущен", 
                                  f"Таймер установлен на {minutes} минут.\n"
                                  "Система отслеживания активирована.")
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить таймер: {str(e)}")
            self.stop_timer()
    
    def stop_timer(self):
        """Остановка таймера и отслеживания"""
        self.is_tracking = False
        self.timer_running = False
        
        # Остановка мониторинга громкости
        self.volume_monitoring = False
        
        # Обновление интерфейса
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("📡 Отслеживание неактивно")
        self.timer_display.setText("Таймер: Не активен")
        self.eye_status_label.setText("👁️ Глаза: Не обнаружены")
        self.face_status_label.setText("😐 Лицо: Не обнаружено")
        self.alarm_status_label.setText("🔇 Сигнал: Выключен")
        self.alarm_status_label.setStyleSheet("color: green;")
        self.volume_status_label.setText("🔊 Громкость: Норма")
        self.volume_status_label.setStyleSheet("color: green;")
        
        # Остановка звука
        if self.alarm_playing:
            self.alarm_playing = False
        
        self.statusBar().showMessage("Таймер остановлен", 3000)
    
    def run_timer(self):
        """Выполнение таймера в отдельном потоке"""
        try:
            start_time = time.time()
            end_time = start_time + self.timer_seconds
            
            while self.timer_running and time.time() < end_time:
                remaining = int(end_time - time.time())
                minutes = remaining // 60
                seconds = remaining % 60
                
                # Обновление отображения таймера через сигнал
                self.update_timer_signal.emit(f"{minutes:02d}:{seconds:02d}")
                
                time.sleep(1)
            
            if self.timer_running:
                self.timer_finished_signal.emit()
                
        except Exception as e:
            print(f"Ошибка в таймере: {e}")
    
    def update_timer_display(self, time_str):
        """Обновление отображения таймера"""
        self.timer_display.setText(f"⏰ Таймер: {time_str}")
    
    def on_timer_finished(self):
        """Действия по завершении таймера"""
        self.stop_timer()
        QMessageBox.information(self, "Время вышло", "Таймер завершен!\nХорошего отдыха!")
    
    def run_eye_tracking(self):
        """Отслеживание глаз в отдельном потоке"""
        try:
            self.cap = cv2.VideoCapture(self.camera_combo.currentIndex())
            if not self.cap.isOpened():
                self.update_status_signal.emit("error", "Не удалось открыть камеру")
                return
            
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
            
            frame_counter = 0
            face_not_found_counter = 0
            
            while self.is_tracking and self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret:
                    break
                
                frame_counter += 1
                if frame_counter % 3 != 0:
                    continue
                
                # Зеркальное отражение
                frame = cv2.flip(frame, 1)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                face_detected = False
                eyes_detected = False
                
                # Детекция лиц
                if self.face_cascade is not None:
                    faces = self.face_cascade.detectMultiScale(
                        gray,
                        scaleFactor=1.1,
                        minNeighbors=5,
                        minSize=(30, 30)
                    )
                    
                    if len(faces) > 0:
                        face_detected = True
                        face_not_found_counter = 0
                        
                        # Детекция глаз
                        for (x, y, w, h) in faces:
                            roi_gray = gray[y:y+h, x:x+w]
                            if self.eye_cascade:
                                eyes = self.eye_cascade.detectMultiScale(roi_gray)
                                if len(eyes) >= 2:
                                    eyes_detected = True
                                    break
                    else:
                        face_not_found_counter += 1
                
                # Определение статуса
                if face_detected:
                    if eyes_detected:
                        status = "Смотрим на экран"
                        color = "green"
                        if self.alarm_playing:
                            self.alarm_playing = False
                            self.update_alarm_signal.emit("🔇 Сигнал: Выключен", "green")
                    else:
                        status = "Глаза не видны"
                        color = "orange"
                else:
                    if face_not_found_counter > 10:
                        status = "Отвернулись от экрана"
                        color = "red"
                        if not self.alarm_playing:
                            self.alarm_playing = True
                            self.play_alarm()
                    else:
                        status = "Лицо не обнаружено"
                        color = "red"
                
                # Отправка сигналов для обновления GUI
                self.update_face_status_signal.emit(
                    "😀 Лицо: Обнаружено" if face_detected else "😐 Лицо: Не обнаружено",
                    "green" if face_detected else "red"
                )
                
                self.update_status_signal.emit(
                    f"👁️ Глаза: {status}",
                    color
                )
                
                # Обновление предпросмотра камеры
                if self.show_camera_check.isChecked():
                    # Рисование рамок для отладки
                    if face_detected:
                        for (x, y, w, h) in faces:
                            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    
                    # Конвертация для отображения в Qt
                    rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb_image.shape
                    bytes_per_line = ch * w
                    qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    pixmap = QPixmap.fromImage(qt_image)
                    self.update_camera_preview_signal.emit(pixmap)
                
                time.sleep(0.05)
                
        except Exception as e:
            print(f"Ошибка в отслеживании глаз: {e}")
        finally:
            if self.cap is not None:
                self.cap.release()
    
    def start_camera_preview(self):
        """Запуск потока предпросмотра камеры"""
        if not hasattr(self, 'preview_thread') or not self.preview_thread.is_alive():
            self.preview_thread = threading.Thread(target=self.camera_preview_worker, daemon=True)
            self.preview_thread.start()
    
    def camera_preview_worker(self):
        """Рабочий поток для предпросмотра камеры"""
        cap = None
        try:
            cap = cv2.VideoCapture(self.camera_combo.currentIndex())
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
            
            while self.is_tracking and cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    # Зеркальное отражение
                    frame = cv2.flip(frame, 1)
                    
                    # Конвертация для Qt
                    rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb_image.shape
                    bytes_per_line = ch * w
                    qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    pixmap = QPixmap.fromImage(qt_image)
                    self.update_camera_preview_signal.emit(pixmap)
                
                time.sleep(0.03)
                
        except Exception as e:
            print(f"Ошибка в предпросмотре камеры: {e}")
        finally:
            if cap is not None:
                cap.release()
    
    def update_camera_preview(self, pixmap):
        """Обновление изображения камеры"""
        if self.show_camera_check.isChecked():
            scaled_pixmap = pixmap.scaled(self.camera_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.camera_label.setPixmap(scaled_pixmap)
    
    def update_status_display(self, text, color):
        """Обновление статуса глаз"""
        self.eye_status_label.setText(text)
        self.eye_status_label.setStyleSheet(f"color: {color};")
    
    def update_face_status_display(self, text, color):
        """Обновление статуса лица"""
        self.face_status_label.setText(text)
        self.face_status_label.setStyleSheet(f"color: {color};")
    
    def update_alarm_display(self, text, color):
        """Обновление статуса сигнала"""
        self.alarm_status_label.setText(text)
        self.alarm_status_label.setStyleSheet(f"color: {color};")
    
    def play_alarm(self):
        """Воспроизведение звукового сигнала"""
        try:
            # Простой beep звук
            winsound.Beep(1000, 300)
            self.update_alarm_signal.emit("🔊 Сигнал: Включен", "red")
            
            # Запуск потока для повторения сигнала
            alarm_thread = threading.Thread(target=self.repeat_alarm, daemon=True)
            alarm_thread.start()
        except:
            self.update_alarm_signal.emit("⚠️ Сигнал: Ошибка", "orange")
    
    def repeat_alarm(self):
        """Повторение звукового сигнала"""
        try:
            while self.alarm_playing and self.is_tracking:
                winsound.Beep(1000, 300)
                time.sleep(1)
        except:
            pass
    
    def monitor_applications(self):
        """Мониторинг запущенных приложений"""
        while self.is_tracking:
            try:
                # Получаем список запущенных процессов
                current_processes = []
                for proc in psutil.process_iter(['name']):
                    try:
                        proc_name = proc.info['name']
                        if proc_name:
                            # Убираем расширение .exe для сравнения
                            proc_name_lower = proc_name.lower()
                            if proc_name_lower.endswith('.exe'):
                                proc_name_lower = proc_name_lower[:-4]
                            current_processes.append(proc_name_lower)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                # Проверяем каждое приложение из черного списка
                for blocked_app in self.blacklist:
                    blocked_lower = blocked_app.lower()
                    
                    # Проверяем, запущен ли процесс
                    app_running = False
                    for proc_name in current_processes:
                        if blocked_lower == proc_name or blocked_lower in proc_name:
                            app_running = True
                            break
                    
                    # Если приложение запущено и окно блокировки не открыто - открываем
                    if app_running and blocked_app not in self.block_windows:
                        self.show_block_window_signal.emit(blocked_app)
                    
                    # Если приложение не запущено, но окно открыто - закрываем
                    elif not app_running and blocked_app in self.block_windows:
                        window = self.block_windows[blocked_app]
                        window.close()
                        del self.block_windows[blocked_app]
                
                time.sleep(2)  # Проверяем каждые 2 секунды
                
            except Exception as e:
                print(f"Ошибка мониторинга приложений: {e}")
                time.sleep(5)
    
    def monitor_audio(self):
        """Мониторинг и контроль громкости"""
        self.volume_monitoring = True
        
        try:
            # Импортируем pycaw для управления громкостью
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            
            # Получаем интерфейс для управления громкостью
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            
            while self.volume_monitoring and self.is_tracking:
                try:
                    # Получаем текущую громкость
                    current_volume = volume.GetMasterVolumeLevelScalar()
                    volume_percent = int(current_volume * 100)
                    
                    # Проверяем, не слишком ли низкая громкость
                    if volume_percent < self.min_volume:
                        # Устанавливаем минимальную громкость
                        volume.SetMasterVolumeLevelScalar(self.min_volume / 100, None)
                        self.volume_warning_signal.emit()
                        self.volume_status_label.setText(f"🔊 Громкость: Установлена {self.min_volume}%")
                        self.volume_status_label.setStyleSheet("color: orange;")
                    else:
                        self.volume_status_label.setText(f"🔊 Громкость: {volume_percent}%")
                        self.volume_status_label.setStyleSheet("color: green;")
                    
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"Ошибка контроля громкости: {e}")
                    time.sleep(5)
                    
        except ImportError:
            # Если pycaw не установлен, используем альтернативный метод
            self.volume_status_label.setText("🔊 Громкость: Контроль недоступен")
            self.volume_status_label.setStyleSheet("color: orange;")
            
            # Альтернативный метод для Windows
            try:
                import ctypes
                from ctypes import wintypes
                
                # Определяем функции Windows API
                user32 = ctypes.windll.user32
                
                while self.volume_monitoring and self.is_tracking:
                    # Используем системные звуки, которые не зависят от громкости
                    time.sleep(5)
                    
            except:
                pass
    
    def show_volume_warning(self):
        """Показать предупреждение о громкости"""
        QMessageBox.warning(self, "Внимание!", 
                           f"Громкость была увеличена до минимального уровня {self.min_volume}%.\n"
                           "Во время работы таймера нельзя полностью выключать звук!")
    
    def create_block_window(self, app_name):
        """Создание окна блокировки"""
        # Проверяем, не открыто ли уже окно для этого приложения
        if app_name in self.block_windows:
            return
        
        # Создаем окно блокировки
        window = BlockWindow(app_name, self)
        self.block_windows[app_name] = window
        
        # Подключаем сигнал закрытия окна
        window.destroyed.connect(lambda: self.on_block_window_closed(app_name))
        
        # Показываем окно
        window.show()
    
    def on_block_window_closed(self, app_name):
        """Обработка закрытия окна блокировки"""
        if app_name in self.block_windows:
            del self.block_windows[app_name]
    
    def closeEvent(self, event):
        """Обработка закрытия главного окна"""
        # Закрываем все окна блокировки
        for app_name, window in self.block_windows.items():
            window.close()
        
        # Останавливаем все потоки
        self.stop_timer()
        
        # Подтверждение выхода
        reply = QMessageBox.question(self, 'Выход',
                                   "Вы уверены, что хотите выйти?",
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

class BlockWindow(QMainWindow):
    """Окно блокировки приложения"""
    
    def __init__(self, app_name, parent=None):
        super().__init__(parent)
        self.app_name = app_name
        self.monitoring = True
        self.setup_ui()
        self.start_monitoring()
    
    def setup_ui(self):
        """Настройка интерфейса окна блокировки"""
        self.setWindowTitle(f"🚫 {self.app_name} - ЗАБЛОКИРОВАНО")
        
        # Устанавливаем флаги окна
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |  # Всегда поверх других окон
            Qt.FramelessWindowHint |    # Без рамки
            Qt.WindowDoesNotAcceptFocus # Не получает фокус
        )
        
        # Делаем окно полноэкранным
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignCenter)
        
        # Сообщение
        message_label = QLabel(
            f"🚫 ПРИЛОЖЕНИЕ ЗАБЛОКИРОВАНО!\n\n"
            f"📱 {self.app_name}\n\n"
            "❌ Это приложение находится в черном списке\n"
            "✅ Закройте его и вернитесь к работе\n\n"
            "⚠️ Внимание: Фокус на работе!\n"
            "⏱️ Это окно закроется автоматически при закрытии приложения"
        )
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
                padding: 20px;
            }
        """)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)
        
        # Красный фон
        central_widget.setStyleSheet("background-color: #ff4444;")
    
    def start_monitoring(self):
        """Запуск мониторинга приложения"""
        self.monitor_thread = threading.Thread(target=self.monitor_process, daemon=True)
        self.monitor_thread.start()
    
    def monitor_process(self):
        """Мониторинг процесса приложения"""
        while self.monitoring:
            try:
                app_running = False
                
                # Проверяем все процессы
                for proc in psutil.process_iter(['name']):
                    try:
                        proc_name = proc.info['name']
                        if proc_name:
                            # Убираем расширение .exe
                            proc_name_lower = proc_name.lower()
                            if proc_name_lower.endswith('.exe'):
                                proc_name_lower = proc_name_lower[:-4]
                            
                            # Сравниваем с именем заблокированного приложения
                            if (self.app_name.lower() == proc_name_lower or 
                                self.app_name.lower() in proc_name_lower):
                                app_running = True
                                break
                    except:
                        continue
                
                # Если приложение закрыто - закрываем окно
                if not app_running:
                    self.monitoring = False
                    self.close_window_signal()
                    break
                
                time.sleep(2)  # Проверяем каждые 2 секунды
                
            except Exception as e:
                print(f"Ошибка мониторинга процесса: {e}")
                time.sleep(5)
    
    def close_window_signal(self):
        """Сигнал для закрытия окна"""
        self.close()
    
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        self.monitoring = False
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Создание и отображение главного окна
    window = EyeTrackerApp()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    # Установите pycaw для контроля громкости
    # pip install pycaw comtypes
    
    main()