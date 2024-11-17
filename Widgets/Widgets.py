from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QSlider, QPushButton,
                            QFrame, QHBoxLayout, QSizePolicy, QDialog, QComboBox, QCheckBox, QScrollArea, QGridLayout, QFileDialog)

from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPixmap, QIcon, QImage, QMovie, QPalette
from PyQt6.QtCore import Qt, QSize, QTimer, QEvent, QPropertyAnimation, QParallelAnimationGroup, QPoint, QEasingCurve, QRect

import json
from typing import List
import os
import subprocess
from PyQt6 import QtGui
from Utility import Util
from PIL import Image
from Threads.Threads import CheckProcessedVideo, ProcessVideo, ImageLoader, GifLoader
from collections import Counter
import sys
from Core.LiveWallPIDManager import LiveWallPIDManager
from Core.LiveWallPlayer import  LiveWallPlayer
from Core.LiveWallState import  LiveWallState
import time
import tempfile

import numpy as np
from sklearn.cluster import KMeans
import colorsys

TARGET_WIDTH = 320
TARGET_HEIGHT = 180
THUMBNAIL_PADDING = 15

SCRIPT_PATH = Util.get_file_path("livewallpaperv4.sh")
GRID_COLUMNS = 3


class SettingsDialogWidget(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Settings")
        self.resize(500, 400)

        self.settings = self.load_settings()

        self.layout = QVBoxLayout(self)

        self.all_monitors_var = self.settings.get("play_all_monitors", True)
        self._create_widgets()

        self.center_window()
        self.setLayout(self.layout)
        self.show()

    def _create_widgets(self):
        # Play on all monitors
        all_monitors_layout = QHBoxLayout()
        all_monitors_label = QLabel("Play on all monitors")
        all_monitors_label.setFont(QtGui.QFont("Inter", 14))
        all_monitors_layout.addWidget(all_monitors_label)

        self.all_monitors_checkbox = QCheckBox()
        self.all_monitors_checkbox.setChecked(self.all_monitors_var)
        self.all_monitors_checkbox.stateChanged.connect(self.toggle_monitor_selection)
        all_monitors_layout.addWidget(self.all_monitors_checkbox)

        self.layout.addLayout(all_monitors_layout)

        # Monitor selection
        self.monitor_frame = QWidget(self)
        monitor_layout = QHBoxLayout(self.monitor_frame)

        monitor_label = QLabel("Select Monitor")
        monitor_label.setFont(QtGui.QFont("Inter", 14))
        monitor_layout.addWidget(monitor_label)

        self.monitor_dropdown = QComboBox()
        self.monitor_dropdown.addItems(self.get_available_monitors())
        self.monitor_dropdown.setCurrentText(self.settings.get("selected_monitor", ""))
        monitor_layout.addWidget(self.monitor_dropdown)

        self.monitor_frame.setVisible(not self.all_monitors_var)
        monitor_layout.addStretch(1)
        self.layout.addWidget(self.monitor_frame)

        # Video output
        video_output_layout = QHBoxLayout()
        video_output_label = QLabel("Video output")
        video_output_label.setFont(QtGui.QFont("Inter", 14))
        video_output_layout.addWidget(video_output_label)

        self.video_output_dropdown = QComboBox()
        self.video_output_dropdown.addItems(self.get_mpv_option_available_list("vo"))
        self.video_output_dropdown.setCurrentText(self.settings.get("vo", "gpu"))
        video_output_layout.addWidget(self.video_output_dropdown)

        self.layout.addLayout(video_output_layout)

        # GPU Context
        gpu_context_layout = QHBoxLayout()
        gpu_context_label = QLabel("GPU Context")
        gpu_context_label.setFont(QtGui.QFont("Inter", 14))
        gpu_context_layout.addWidget(gpu_context_label)

        self.gpu_context_dropdown = QComboBox()
        self.gpu_context_dropdown.addItems(self.get_mpv_option_available_list("gpu-context"))
        self.gpu_context_dropdown.setCurrentText(self.settings.get("gpu_context", "auto"))
        gpu_context_layout.addWidget(self.gpu_context_dropdown)

        self.layout.addLayout(gpu_context_layout)

        # GPU API
        gpu_api_layout = QHBoxLayout()
        gpu_api_label = QLabel("GPU API")
        gpu_api_label.setFont(QtGui.QFont("Inter", 14))
        gpu_api_layout.addWidget(gpu_api_label)

        self.gpu_api_dropdown = QComboBox()
        self.gpu_api_dropdown.addItems(self.get_mpv_option_available_list("gpu-api"))
        self.gpu_api_dropdown.setCurrentText(self.settings.get("gpu_api", "auto"))
        gpu_api_layout.addWidget(self.gpu_api_dropdown)

        self.layout.addLayout(gpu_api_layout)

        # HWDEC

        hwdec_layout = QHBoxLayout()
        hwdec_label = QLabel("Hardware Decoding")
        hwdec_label.setFont(QtGui.QFont("Inter", 14))
        hwdec_layout.addWidget(hwdec_label)

        self.hwdec_dropdown = QComboBox()
        self.hwdec_dropdown.addItems(self.get_mpv_option_available_list("hwdec"))
        self.hwdec_dropdown.setCurrentText(self.settings.get("hwdec", "auto"))
        hwdec_layout.addWidget(self.hwdec_dropdown)

        self.layout.addLayout(hwdec_layout)

        # Botões de ação
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.setStyleSheet(f"background-color: {Util.COLORS['accent']};")
        save_button.clicked.connect(self.save_settings)
        button_layout.addWidget(save_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet(f"background-color: {Util.COLORS['bg_secondary']};")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        self.layout.addLayout(button_layout)

    def toggle_monitor_selection(self):
        self.monitor_frame.setVisible(not self.all_monitors_checkbox.isChecked())

    def center_window(self):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

    def get_available_monitors(self) -> List[str]:
        try:
            result = subprocess.run(['xrandr', '--listmonitors'], capture_output=True, text=True)
            monitors = []
            for line in result.stdout.split('\n')[1:]:
                if line.strip():
                    monitors.append(line.split()[-1])
            return monitors if monitors else ["Monitor 1"]
        except Exception as e:
            print(f"Erro ao listar monitores: {e}")
            return ["Monitor 1"]

    def get_mpv_option_available_list(self, option: str) -> List[str]:
        try:
            result = subprocess.run(["mpv", f"--{option}=help"], stdout=subprocess.PIPE, text=True)
            return [line.split()[0] for line in result.stdout.splitlines()[1:] if line.strip()]
        except Exception as e:
            print(f"Erro ao listar opções para {option}: {e}")
            return []

    @staticmethod
    def load_settings() -> dict:
        config_path = os.path.expanduser("~/.config/MyLiveWall/settings.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Erro ao carregar configurações: {e}")
        return {
            "play_all_monitors": True,
            "selected_monitor": "",
            "vo": "gpu",
            "gpu_context": "auto",
            "gpu_api": "auto",
            "hwdec": "auto"
        }

    def save_settings(self):
        settings = {
            "play_all_monitors": self.all_monitors_checkbox.isChecked(),
            "selected_monitor": self.monitor_dropdown.currentText(),
            "vo": self.video_output_dropdown.currentText(),
            "gpu_context": self.gpu_context_dropdown.currentText(),
            "gpu_api": self.gpu_api_dropdown.currentText(),
            "hwdec": self.hwdec_dropdown.currentText()

        }

        config_dir = os.path.expanduser("~/.config/MyLiveWall")
        config_path = os.path.join(config_dir, "settings.json")

        try:
            os.makedirs(config_dir, exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(settings, f, indent=4)
            self.accept()
        except Exception as e:
            print(f"Erro ao salvar configurações: {e}")


class VideoThumbnailWidget(QWidget):
    def __init__(self, parent, video_path, thumbnail_path, preview_path, on_select, on_playback_toggle, is_playing=False, is_preprocessed=False):
        super().__init__(parent)

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.video_path = video_path
        self.on_select = on_select
        self.on_playback_toggle = on_playback_toggle
        self.selected = False
        self.preview_playing = False
        self.is_preprocessed = is_preprocessed
        self.is_playing = is_playing
        self.thumbnail_pixmap = None
        self.movie_preview = None
        self.thumbnail_label = None
        self.preview_widget = None

        self.videoCheckThread = CheckProcessedVideo(video_path=video_path)
        self.videoCheckThread.video_checked.connect(self.on_video_checked)
        self.videoCheckThread.start()

        self.videoProcessThread = ProcessVideo(video_path=video_path)
        self.videoProcessThread.video_processed.connect(self.on_video_processed)
        # Load play/stop icons
        play_icon_path = Util.get_file_path("../play_icon.png")
        stop_icon_path = Util.get_file_path("../stop_icon.png")
        self.play_icon = QIcon(play_icon_path)
        self.stop_icon = QIcon(stop_icon_path)
        self.success_icon = QIcon(Util.get_file_path("../success_icon.png"))
        self.fail_icon = QIcon(Util.get_file_path("../fail_icon.png"))

        # Layout principal
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Animação para o hover
        self.hover_animation = QPropertyAnimation(self, b"geometry")
        self.hover_animation.setDuration(100)

        # Prepare thumbnail image
        try:
            self.update_thumbnail(thumbnail_path, preview_path)

            # Container para manter tamanho fixo
            self.media_container = QFrame()
            self.media_container.setFixedSize(QSize(TARGET_WIDTH, TARGET_HEIGHT))
            self.media_container.setFrameStyle(QFrame.Shape.NoFrame)
            # self.media_container.setSizePolicy(
            #     QSizePolicy.Policy.Expanding,
            #     QSizePolicy.Policy.Expanding
            # )

            self.media_container.setStyleSheet("margin: 0px; padding: 0px; background-position: center; border-bottom-right-radius: 0px; border-bottom-left-radius: 0px; border-top-left-radius: 10px; border-top-right-radius: 10px")

            # self.media_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

            # Layout para o container de mídia
            media_layout = QVBoxLayout(self.media_container)
            media_layout.setContentsMargins(0, 0, 0, 0)
            media_layout.setSpacing(0)

            # Thumbnail label
            self.thumbnail_label = QLabel(self.media_container)
            self.thumbnail_label.setFixedSize(QSize(TARGET_WIDTH, TARGET_HEIGHT))
            if (self.thumbnail_pixmap!=None):
                self.thumbnail_label.setPixmap(self.thumbnail_pixmap)
            self.thumbnail_label.setStyleSheet("margin: 0px; padding: 5px; background-position: center; background-color: rgba(0, 0, 0, 0); border-radius: 5px;")

            # Widget de vídeo para preview
            self.preview_widget = QLabel(self.media_container)
            self.preview_widget.setFixedSize(QSize(TARGET_WIDTH, TARGET_HEIGHT))
            self.preview_widget.setStyleSheet("margin: 0px; padding: 5px; background-position: center; background-color: rgba(0, 0, 0, 0); border-radius: 5px;")
            self.preview_widget.hide()

            # Adicionar container ao layout principal
            self.layout.addWidget(self.media_container, alignment=Qt.AlignmentFlag.AlignCenter)
            self.setLayout(self.layout)

            # Configura o GIF para o preview
            if (preview_path!=None):
                self.movie_preview = QMovie(preview_path)
                self.preview_widget.setMovie(self.movie_preview)

                # Timer para delay do hover
            self.hover_timer = QTimer()
            self.hover_timer.setSingleShot(True)
            self.hover_timer.timeout.connect(self.start_preview)

            # Instalar event filter para eventos de mouse
            self.setMouseTracking(True)
            self.installEventFilter(self)

            # Definir políticas de tamanho
            self.setSizePolicy(
                QSizePolicy.Policy.Fixed,
                QSizePolicy.Policy.Fixed
            )

            self.overlay_frame = QFrame(self.media_container)
            self.overlay_frame.setFrameStyle(QFrame.Shape.NoFrame)
            self.overlay_frame.setFixedSize(QSize(TARGET_WIDTH, TARGET_HEIGHT))
            self.overlay_frame.setStyleSheet("background-position: center; background-color: rgba(0, 0, 0, 0);")

            # Botão de controle (play/stop) no canto superior direito
            self.control_button = QPushButton()
            self.control_button.setIcon(self.stop_icon if is_playing else self.play_icon)
            self.control_button.setMouseTracking(True)
            self.control_button.setIconSize(QSize(25, 25))
            self.control_button.clicked.connect(self.toggle_playback)
            self.control_button.setStyleSheet("margin: 3px; padding: 3px; background-position: center; background-color: rgba(0, 0, 0, 150); font-size: 18px; color: white; border-radius: 5px;")

            # Botão de pré-processamento no canto superior direito
            self.preprocess_button = QPushButton()
            self.preprocess_button.setIcon(self.success_icon if self.is_preprocessed else self.fail_icon)
            self.preprocess_button.setMouseTracking(True)
            self.preprocess_button.setIconSize(QSize(15, 15))
            self.preprocess_button.clicked.connect(self.preprocess_video)
            self.preprocess_button.setStyleSheet("margin: 3px; padding: 8px; background-position: center; background-color: rgba(0, 0, 0, 150); font-size: 18px; color: white; border-radius: 5px;")
            # self.preprocess_button.setEnabled(False)

            # Layout para posicionar o botão de controle sobre a miniatura
            self.overlay_layout = QHBoxLayout(self.overlay_frame)
            self.overlay_layout.setContentsMargins(0, 0, 0, 0)
            self.overlay_layout.addStretch()
            self.overlay_layout.addWidget(self.control_button, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
            self.overlay_layout.addWidget(self.preprocess_button, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

            # Nome do arquivo
            filename = os.path.basename(video_path)
            name_without_ext = os.path.splitext(filename)[0]
            self.name_label = QLabel(text=name_without_ext)
            self.name_label.setStyleSheet(f"background-color:rgba(150, 150, 150, 50); color: {Util.COLORS['text_secondary']}; font-size: 12px; border-bottom-right-radius: 10px; border-bottom-left-radius: 10px; border-top-left-radius: 0px; border-top-right-radius: 0px")
            self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.name_label.setFixedHeight(45)
            self.name_label.setWordWrap(True)
            self.layout.addWidget(self.name_label)

            # Styling
            self.setStyleSheet(f"background-color: {Util.COLORS['bg_secondary']}; border-radius: 10px;")
            # Adicionar uma propriedade para controlar a posição do widget
            self.pos_animation = QPropertyAnimation(self, b"pos")
            self.pos_animation.setDuration(500)  # 300ms


        except Exception as e:
            print(f"Erro ao criar thumbnail: {e}")

    def moveEvent(self, event):
        """Sobrescreve o evento de movimento para atualizar a posição durante a animação"""
        super().moveEvent(event)
        # Atualizar layout se necessário
        if self.parent():
            self.parent().update()

    def on_video_checked(self, is_preprocessed):
        self.is_preprocessed = is_preprocessed
        self.preprocess_button.setIcon(self.success_icon if self.is_preprocessed else self.fail_icon)


    def update_thumbnail(self, thumbnail_path, preview_path):

        if (thumbnail_path!=None):
            image = Image.open(thumbnail_path)
            resized_image = self.resize_with_aspect_ratio(image, TARGET_WIDTH, TARGET_HEIGHT)

            # Create black background
            background = Image.new('RGB', (TARGET_WIDTH, TARGET_HEIGHT), Util.COLORS['bg_primary'])

            # Center image
            x = (TARGET_WIDTH - resized_image.width) // 2
            y = (TARGET_HEIGHT - resized_image.height) // 2
            background.paste(resized_image, (x, y))

            # Convert to QPixmap
            qt_image = QImage(background.tobytes(), TARGET_WIDTH, TARGET_HEIGHT, QImage.Format.Format_RGB888)

            self.thumbnail_pixmap = QPixmap.fromImage(qt_image)
            if (self.thumbnail_label!=None):
                self.thumbnail_label.setPixmap(self.thumbnail_pixmap)

        if (preview_path!=None):
            self.movie_preview = QMovie(preview_path)
            if (self.preview_widget!=None):
                self.preview_widget.setFixedSize(TARGET_WIDTH, TARGET_HEIGHT)
                self.preview_widget.setMovie(self.movie_preview)


    def toggle_playback(self):
        self.is_playing = not self.is_playing
        self.control_button.setIcon(self.stop_icon if self.is_playing else self.play_icon)
        self.on_select(self)
        self.on_playback_toggle(self)


    def preprocess_video(self):
        if not self.is_preprocessed:
            try:
                if (self.is_playing):
                    self.toggle_playback()

                self.setEnabled(False)
                process_video_thread = ProcessVideo.ProcessVideo(self.video_path)
                self.videoProcessThread.start()
            except subprocess.CalledProcessError as e:
                print(f"Error preprocessing video: {e}")
                self.setEnabled(True)

    def on_video_processed(self, is_processed, output_path):

        self.is_preprocessed = is_processed
        self.preprocess_button.setIcon(self.success_icon if is_processed else self.fail_icon)
        self.preprocess_button.setEnabled(not is_processed)
        self.setEnabled(True)

        if (is_processed):
            os.remove(self.video_path)
            renamed_path = os.path.splitext(self.video_path)[0] + ".mp4"
            os.rename(output_path, renamed_path)
            self.video_path = renamed_path


    def set_playing(self, is_playing):
        self.is_playing = is_playing
        self.control_button.setIcon(self.stop_icon if is_playing else self.play_icon)

    def on_hover(self, event):
        #if not self.selected:
            #self.setStyleSheet(f"background-color: {Util.COLORS['hover']}; border-radius: 80px;")
        self.hover_animation.stop()
        start_geometry = self.geometry()
        end_geometry = QRect(start_geometry.x() - 5, start_geometry.y() - 5,
                             start_geometry.width() + 10, start_geometry.height() + 10)
        self.hover_animation.setStartValue(start_geometry)
        self.hover_animation.setEndValue(end_geometry)
        self.hover_animation.start()
        super().enterEvent(event)

    def on_leave(self, event):
        # if not self.selected:
        #     self.setStyleSheet(f"background-color: {Util.COLORS['bg_secondary']}; border-radius: 10px;")

        self.hover_animation.stop()
        end_geometry = self.geometry()
        start_geometry = QRect(end_geometry.x() + 5, end_geometry.y() + 5,
                               end_geometry.width() - 10, end_geometry.height() - 10)
        self.hover_animation.setStartValue(end_geometry)
        self.hover_animation.setEndValue(start_geometry)
        self.hover_animation.start()
        super().leaveEvent(event)

    def start_preview(self):
        if not self.preview_playing and self.movie_preview!=None:
            self.preview_playing = True
            self.thumbnail_label.hide()
            self.preview_widget.show()
            self.movie_preview.start()
            self.hover_animation.stop()

            # size = self.movie_preview.scaledSize().expandedTo(self.preview_widget.size())
            # self.movie_preview.setScaledSize(QSize(end_geometry.width(),self.preview_widget.height()))

    def stop_preview(self):
        if self.preview_playing:
            self.preview_playing = False
            self.movie_preview.stop()
            self.preview_widget.hide()
            self.thumbnail_label.show()


    def eventFilter(self, obj, event):
        if obj==self:
            if event.type()==QEvent.Type.Enter:
                self.on_hover(event)
                self.hover_timer.start(500)
            elif event.type()==QEvent.Type.Leave:
                self.hover_timer.stop()
                self.stop_preview()
                self.on_leave(event)
        return super().eventFilter(obj, event)

    def set_selected(self, selected):
        self.selected = selected
        self.setStyleSheet(f"background-color: {Util.COLORS['selected'] if selected else Util.COLORS['bg_secondary']}; border-radius: 10px;")

    def resize_with_aspect_ratio(self, image, target_width, target_height):
        """Redimensiona a imagem mantendo o aspect ratio"""
        original_width, original_height = image.size
        aspect_ratio = original_width / original_height

        if original_width > original_height:
            new_width = target_width
            new_height = int(target_width / aspect_ratio)
            if new_height > target_height:
                new_height = target_height
                new_width = int(target_height * aspect_ratio)
        else:
            new_height = target_height
            new_width = int(target_height * aspect_ratio)
            if new_width > target_width:
                new_width = target_width
                new_height = int(target_width / aspect_ratio)

        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)


class BackgroundWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.opacity = 0
        self.r, self.g ,self.b = 26, 26 ,26


    def setOpacity(self, value):
        self.opacity = value
        self.update()

    def setColor(self, r,g,b,a):
        self.r, self.g, self.b, self.opacity = r, g, b, a
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(self.r, self.g ,self.b, self.opacity))


class MyLiveWallWidget(QMainWindow):
    def __init__(self):
        super().__init__()

        # Configurações da janela
        self.setWindowTitle("My LiveWall")
        self.setGeometry(100, 100, 1024, 768)
        #self.setStyleSheet(f"background-color: {Util.COLORS['bg_primary']};")
        self.setStyleSheet(f"background-color: transparent;")
        #self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Variáveis
        self.video_dir = ""
        self.selected_thumbnail = None
        self.video_process = None
        self.process_manager = LiveWallPIDManager()
        self.wallpaper_state = LiveWallState()
        self.thumbnail_loaders = []

        self.thumbnails_row_col = []

        # Configurações do grid
        self.THUMBNAIL_WIDTH = TARGET_WIDTH  # Largura desejada para cada thumbnail
        self.THUMBNAIL_HEIGHT = TARGET_HEIGHT  # Altura desejada para cada thumbnail
        self.MIN_COLUMNS = 2  # Número mínimo de colunas
        self.grid_columns = self.MIN_COLUMNS  # Inicial
        #self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground ,True)



        self._create_widgets()
        self._load_initial_state()

        # Criar timer para verificar redimensionamento
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.handle_resize)

        # Adicionar variável para controlar animações
        self.animation_group = None
        self.ANIMATION_DURATION = 500  # Duração da animação em milissegundos

    def resizeEvent(self, event):
        """Sobrescreve o evento de redimensionamento para atualizar o grid"""
        super().resizeEvent(event)
        # Reinicia o timer toda vez que a janela é redimensionada
        self.resize_timer.start(150)  # 150ms delay para evitar atualizações muito frequentes

    def handle_resize(self):
        """Manipula o redimensionamento da janela"""
        try:
            # Calcular novo número de colunas
            scroll_width = self.video_scroll_area.viewport().width()
            spacing = self.main_container_layout.spacing()
            margins = self.main_container_layout.contentsMargins()
            available_width = scroll_width - margins.left() - margins.right() - spacing *2

            # Considera o espaçamento entre os thumbnails
            width_with_spacing = self.THUMBNAIL_WIDTH + spacing
            new_columns = max(self.MIN_COLUMNS, (available_width + spacing) // width_with_spacing)

            if new_columns!=self.grid_columns:
                self.grid_columns = new_columns
                self.reorganize_grid()

        except Exception as e:
            print(f"Erro durante o redimensionamento: {e}")

    def on_grid_reorganized(self):
        for i, info in enumerate(self.thumbnails_row_col):
            row = info["row"]
            col = info["col"]
            thumbnail = info["thumbnail"]
            self.main_container_layout.addWidget(thumbnail, row, col)


    def reorganize_grid(self):
        """Reorganiza os widgets no grid"""
        if not self.video_dir:
            return

        # Cancelar animações anteriores se existirem
        if self.animation_group and self.animation_group.state()==QParallelAnimationGroup.State.Running:
            self.animation_group.stop()

        self.thumbnails_row_col.clear()

        # Criar novo grupo de animações
        self.animation_group = QParallelAnimationGroup()
        self.animation_group.finished.connect(self.on_grid_reorganized)

        # Armazenar widgets e suas informações
        widgets_info = []

        # Coletar todos os widgets existentes e suas informações
        for i in range(self.main_container_layout.count()):
            item = self.main_container_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, VideoThumbnailWidget):
                    widgets_info.append({
                        'widget': widget,
                        'video_path': widget.video_path,
                        'is_selected': widget==self.selected_thumbnail,
                        'is_playing': widget.is_playing,
                        'current_pos': widget.pos()
                    })

        # Calcular novas posições mantendo os widgets no layout
        margin_left = self.main_container_layout.contentsMargins().left()
        margin_top = self.main_container_layout.contentsMargins().top()
        spacing = self.main_container_layout.spacing()

        for i, info in enumerate(widgets_info):
            widget = info['widget']
            row = i // self.grid_columns
            col = i % self.grid_columns

            # Calcular nova posição
            new_x = margin_left + col * (self.THUMBNAIL_WIDTH + spacing)
            new_y = margin_top + row * (self.THUMBNAIL_HEIGHT + spacing)
            new_pos = QPoint(new_x, new_y)

            # Criar animação de posição
            animation = QPropertyAnimation(widget, b"pos")
            animation.setDuration(self.ANIMATION_DURATION)
            animation.setStartValue(info['current_pos'])
            animation.setEndValue(new_pos)
            animation.setEasingCurve(QEasingCurve.Type.InBack)  # Suavização da animação

            # Adicionar ao grupo de animações
            self.animation_group.addAnimation(animation)

            # Atualizar posição no layout (necessário para manter o layout correto)
            self.thumbnails_row_col.append({
                'thumbnail': widget,
                'row': row,
                'col': col
            })

        # Iniciar animações
        self.animation_group.start()

    def capture_frame(video_path, output_image, timestamp="00:00:01"):
        """
        Captura um frame do vídeo usando ffmpeg.
        """
        command = [
            "ffmpeg",
            '-y',
            "-ss", timestamp,  # Tempo do frame (1 segundo por padrão)
            "-i", video_path,  # Caminho do vídeo
            "-frames:v", "1",  # Número de frames a capturar
            "-q:v", "2",  # Qualidade da imagem
            output_image  # Caminho da saída
        ]
        subprocess.run(command, check=True)

    def get_dominant_color(image_path):
        """
        Analisa a cor predominante de uma imagem.
        """
        image = Image.open(image_path)
        image = image.resize((50, 50))  # Reduz o tamanho para acelerar o processamento
        pixels = list(image.getdata())
        most_common_color = Counter(pixels).most_common(1)[0][0]
        return most_common_color

    def get_dominant_colors(image_path, num_colors=3):
        """
        Identifica as cores que mais se destacam em uma imagem usando KMeans.
        """
        image = Image.open(image_path).convert("RGB")
        image = image.resize((100, 100))  # Reduz o tamanho para acelerar o processamento
        pixels = np.array(image).reshape(-1, 3)  # Transforma em uma lista de pixels (R, G, B)

        # Aplica KMeans para encontrar os clusters de cores
        kmeans = KMeans(n_clusters=num_colors, random_state=0)
        kmeans.fit(pixels)

        # Obtém as cores dos clusters e ordena pela frequência
        colors = kmeans.cluster_centers_.astype(int)
        labels, counts = np.unique(kmeans.labels_, return_counts=True)
        sorted_colors = [colors[i] for i in labels[np.argsort(-counts)]]
        return sorted_colors

    def get_vibrant_colors(image_path, num_colors=5):
        """
        Identifica as cores mais vibrantes da imagem.
        """
        image = Image.open(image_path).convert("RGB")
        image = image.resize((100, 100))  # Reduz o tamanho para acelerar o processamento
        pixels = np.array(image).reshape(-1, 3)  # Lista de pixels (R, G, B)

        vibrant_pixels = []
        for r, g, b in pixels:
            # Converte RGB para HSV
            h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            s, v = s * 255, v * 255  # Normaliza saturação e valor para 0-255
            # Considera apenas cores com alta saturação e brilho
            if s > 100 and v > 100:  # Ajuste os limites conforme necessário
                vibrant_pixels.append((r, g, b, s, v))

        # Ordena por saturação e brilho, decrescente
        vibrant_pixels.sort(key=lambda x: (x[3], x[4]), reverse=True)

        # Retorna as `num_colors` cores mais vibrantes (R, G, B)
        return [pixel[:3] for pixel in vibrant_pixels[:num_colors]]

    def color_to_qcolor(color):
        """
        Converte uma cor (R, G, B) para um objeto QColor.
        """
        return QColor(*color)

    def _load_initial_state(self):
        """Load and apply initial state"""
        state = self.wallpaper_state.load_state()
        if state and state.get("video_path"):
            self.video_dir = os.path.dirname(state["video_path"])
            path = os.path.exists(state["video_path"])
            if not os.path.exists(path):
                path = None
            self.update_videos(initial_video=path, is_playing=state.get("is_playing", False))

    def _create_widgets(self):
        # Layout principal

        self.background = BackgroundWidget()
        self.setCentralWidget(self.background)
        main_layout = QVBoxLayout(self.background)
        #main_layout = QVBoxLayout()
        #self.centralWidget = QWidget()
        #self.centralWidget.setLayout(main_layout)
        #self.setCentralWidget(self.centralWidget)
        self.background.setOpacity(128)

        # Header
        header_layout = QHBoxLayout()
        header_frame = QFrame()
        header_frame.setStyleSheet(f"background-color: transparent;")
        header_frame.setLayout(header_layout)
        header_frame.setFixedHeight(80)
        main_layout.addWidget(header_frame)

        # Título
        title_label = QLabel("Video Wallpaper")
        title_label.setStyleSheet(f"color: {Util.COLORS['text_primary']};font-size: 18x;font-weight: bold;")
        header_layout.addWidget(title_label)

        # Botões
        button_layout = QHBoxLayout()
        header_layout.addLayout(button_layout)

        # Ícones
        folder_icon = QIcon(Util.get_file_path("../folder_icon.png"))
        refresh_icon = QIcon(Util.get_file_path("../refresh_icon.png"))
        menu_icon = QIcon(Util.get_file_path("../menu-bar.png"))

        # Botões
        self.menu_button = QPushButton()
        self.menu_button.setIcon(menu_icon)
        self.menu_button.setIconSize(QSize(20, 20))
        self.menu_button.setStyleSheet(f"""
            background-color: {Util.COLORS['bg_secondary']};
            border-radius: 8px;
            padding: 5px;
        """)
        self.menu_button.clicked.connect(self.show_settings)
        button_layout.addWidget(self.menu_button)

        self.folder_button = QPushButton()
        self.folder_button.setIcon(folder_icon)
        self.folder_button.setIconSize(QSize(20, 20))
        self.folder_button.setStyleSheet(f"""
            background-color: {Util.COLORS['bg_secondary']};
            border-radius: 8px;
            padding: 5px;
        """)
        self.folder_button.clicked.connect(self.select_folder)
        button_layout.addWidget(self.folder_button)

        self.refresh_button = QPushButton()
        self.refresh_button.setIcon(refresh_icon)
        self.refresh_button.setIconSize(QSize(20, 20))
        self.refresh_button.setStyleSheet(f"""
            background-color: {Util.COLORS['bg_secondary']};
            border-radius: 8px;
            padding: 5px;
        """)
        self.refresh_button.clicked.connect(self.update_videos)
        button_layout.addWidget(self.refresh_button)

        # Container principal
        # main_container = QFrame()
        # main_container.setStyleSheet(f"background-color: transparent;")
        # main_layout.addWidget(main_container)
        # main_container_layout = QVBoxLayout()
        # main_container.setLayout(main_container_layout)

        main_container = QWidget()
        main_container.setStyleSheet(f"background-color: transparent;")
        main_layout.addWidget(main_container, alignment=Qt.AlignmentFlag.AlignCenter)
        main_container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Frame scrollável
        self.video_frame = QScrollArea()
        self.video_frame.setWidgetResizable(True)
        self.video_frame.setStyleSheet(f"""
            background-color: {Util.COLORS['bg_primary']};
            border: none;
        """)

        # Área de rolagem para vídeos
        self.video_scroll_area = QScrollArea()
        self.video_scroll_area.setWidgetResizable(True)
        self.video_scroll_content = QWidget()
        self.video_scroll_area.setWidget(self.video_scroll_content)
        main_layout.addWidget(self.video_scroll_area)
        # main_container_layout.addWidget(self.video_frame)
        self.main_container_layout = QGridLayout(self.video_scroll_content)
        self.main_container_layout.setSpacing(30)  # Espaçamento entre thumbnails
        # self.main_container_layout.setContentsMargins(120, 60, 60, 60)  # Margens


        # Permitir que o conteúdo se expanda horizontalmente
        self.video_scroll_content.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )


    def show_settings(self):
        settings_dialog = SettingsDialogWidget(self)

    def select_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Video Folder")
        if folder_path:
            self.video_dir = folder_path
            self.update_videos()


    def load_videos(self, video_dir):
        """Obtém uma lista de vídeos no diretório especificado."""
        videos = [os.path.join(video_dir, file) for file in os.listdir(video_dir)
                  if file.lower().endswith((".mp4", ".mkv", ".webm"))]
        return videos

    def update_videos(self, initial_video=None, is_playing=False):
        """Atualiza a lista de vídeos"""
        if not self.video_dir:
            return

        self.selected_thumbnail = None

        # Limpar layout existente
        while self.main_container_layout.count():
            item = self.main_container_layout.takeAt(0)
            if item and item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.deleteLater()

        # Carregar vídeos
        videos = self.load_videos(self.video_dir)
        for i, video_path in enumerate(videos):
            is_current = initial_video and os.path.samefile(video_path, initial_video)

            # Criar thumbnail
            temp_thumbnail = VideoThumbnailWidget(
                self.video_frame,
                video_path,
                None,
                None,
                self.select_video,
                self.toggle_video_playback,
                is_playing=is_playing and is_current
            )

            # Configurar tamanho
            # temp_thumbnail.setFixedSize(self.THUMBNAIL_WIDTH, self.THUMBNAIL_HEIGHT)

            # Adicionar ao grid
            row = i // self.grid_columns
            col = i % self.grid_columns
            self.main_container_layout.addWidget(temp_thumbnail, row, col)

            # Iniciar carregamento das miniaturas
            self.start_thumbnail_loading(temp_thumbnail, video_path, is_current)

    def start_thumbnail_loading(self, thumbnail, video_path, is_current):
        """Inicia o carregamento das miniaturas em background"""
        thumbnail_loaderImg = ImageLoader(video_path)
        thumbnail_loaderGif = GifLoader(video_path)

        thumbnail_loaderImg.thumbnail_ready.connect(self.on_thumbnail_loadedImg)
        thumbnail_loaderGif.thumbnail_ready.connect(self.on_thumbnail_loadedGif)

        thumbnail_loaderImg.start()
        thumbnail_loaderGif.start()

        self.thumbnail_loaders.append(thumbnail_loaderImg)
        self.thumbnail_loaders.append(thumbnail_loaderGif)

        if is_current:
            self.select_video(thumbnail)

    def on_thumbnail_loadedImg(self, video_path, thumbnail_path):
        """Atualiza a miniatura do vídeo assim que o carregamento assíncrono estiver concluído."""
        # Procurar o item de miniatura que corresponde ao caminho do vídeo e atualizar
        for i in range(self.main_container_layout.count()):
            widget = self.main_container_layout.itemAt(i).widget()
            if isinstance(widget, VideoThumbnailWidget) and widget.video_path==video_path:
                widget.update_thumbnail(thumbnail_path, None)
                break

    def on_thumbnail_loadedGif(self, video_path, preview_path):
        """Atualiza a miniatura do vídeo assim que o carregamento assíncrono estiver concluído."""
        # Procurar o item de miniatura que corresponde ao caminho do vídeo e atualizar
        for i in range(self.main_container_layout.count()):
            widget = self.main_container_layout.itemAt(i).widget()
            if isinstance(widget, VideoThumbnailWidget) and widget.video_path==video_path:
                widget.update_thumbnail(None, preview_path)
                break


    def toggle_video_playback(self, thumbnail):
        if thumbnail.is_playing:
            self.apply_selection()
            self.selected_thumbnail.video_path = thumbnail.video_path
            self.wallpaper_state.save_state(thumbnail.video_path, True)
        else:
            self.process_manager.kill_processes()
            self.video_process = None
            self.wallpaper_state.save_state(thumbnail.video_path, False)

        for i in range(self.main_container_layout.count()):
            widget = self.main_container_layout.itemAt(i).widget()
            if isinstance(widget, VideoThumbnailWidget) and widget!=thumbnail:
                widget.set_playing(False)

    def select_video(self, thumbnail):
        if self.selected_thumbnail:
            self.selected_thumbnail.set_selected(False)
        thumbnail.set_selected(True)
        self.selected_thumbnail = thumbnail

    def apply_selection(self):
        # Primeiro, mata processos anteriores se existirem
        self.process_manager.kill_processes()

        # Carregar configurações
        settings = SettingsDialogWidget.load_settings()

        player = LiveWallPlayer()
        player.set_video_output(settings["vo"])
        player.set_gpu_context(settings["gpu_context"])
        player.set_gpu_api(settings["gpu_api"])
        player.set_hwdec(settings["hwdec"])
        player.set_selected_monitor(settings["selected_monitor"])
        player.set_play_all_monitors(settings["play_all_monitors"])
        player.set_video_path(self.selected_thumbnail.video_path)
        player.start()

        # Esperar um pouco para os processos filhos iniciarem
        time.sleep(1)

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
            frame_image = temp_file.name
        MyLiveWallWidget.capture_frame(self.selected_thumbnail.video_path, frame_image)
        dominant_color = MyLiveWallWidget.get_dominant_color(frame_image)
        dominant_colors= MyLiveWallWidget.get_dominant_colors(frame_image)
        vibrant_colors = MyLiveWallWidget.get_vibrant_colors(frame_image, num_colors=3)
        print("Cores vibrantes (R, G, B):", vibrant_colors)

        print(f"Cor predominante: {dominant_color}")
        print(f"Cores predominantes: {dominant_colors}")
        q_color = MyLiveWallWidget.color_to_qcolor(vibrant_colors[0])
        palette = MyLiveWallWidget.palette(self)
        palette.setColor(QPalette.ColorRole.Window, q_color)
        MyLiveWallWidget.setPalette(self, palette)
        #MyLiveWallWidget.setAutoFillBackground(True)
        self.background.setColor(q_color.getRgb()[0],q_color.getRgb()[1],q_color.getRgb()[2], 128)

        # Obter PIDs dos processos xwinwrap
        child_pids = []
        try:
            ps_output = subprocess.check_output(['pgrep', 'xwinwrap']).decode()
            child_pids = [int(pid) for pid in ps_output.splitlines()]
        except subprocess.CalledProcessError:
            pass

        # Salvar informações dos processos
        self.process_manager.save_process_info(0, child_pids)

        # Save state
        self.wallpaper_state.save_state(self.selected_thumbnail.video_path, True)

        return 0, child_pids

    def closeEvent(self, event):
        # if self.video_process:
        #     parent = psutil.Process(self.video_process.pid)
        #     # Terminar o processo e todos os subprocessos
        #     for child in parent.children(recursive=True):
        #         child.terminate()
        #     parent.terminate()  # Termina o próprio script
        #     self.video_process = None
        self.close()