from PyQt6.QtCore import pyqtSignal, QThread
from Utility import  Util


class GifLoader(QThread):
    thumbnail_ready = pyqtSignal(str, str)  # Sinal para enviar o caminho do vídeo e as miniaturas

    def __init__(self, video_path):
        super().__init__()
        self.video_path = video_path

    def run(self):
        # Carregar miniaturas
        preview_path = Util.get_linux_thumbnail_preview(self.video_path)
        self.thumbnail_ready.emit(self.video_path, preview_path)

class ImageLoader(QThread):
    thumbnail_ready = pyqtSignal(str, str)  # Sinal para enviar o caminho do vídeo e as miniaturas

    def __init__(self, video_path):
        super().__init__()
        self.video_path = video_path

    def run(self):
        # Carregar miniaturas
        thumbnail_path = Util.get_linux_thumbnail(self.video_path)
        self.thumbnail_ready.emit(self.video_path, thumbnail_path)



import os
import subprocess


class ProcessVideo(QThread):
    video_processed = pyqtSignal(bool, str)  # Sinal para enviar o caminho do vídeo e as miniaturas

    def __init__(self, video_path):
        super().__init__()
        self.video_path = video_path

    def run(self):
        print(f"Preprocessing video: {self.video_path}")
        output_path = os.path.splitext(self.video_path)[0] + "_processed.mp4"
        print(f"Preprocessed video: {output_path}")
        try:
            subprocess.run([
                './ffmpeg',
                '-y',
                '-hwaccel', 'vulkan',
                '-init_hw_device', 'vulkan=gpu:0',
                '-filter_hw_device', 'gpu',
                '-i', self.video_path,
                '-c:v', 'hevc_nvenc',
                '-preset', 'p7',
                '-rc', 'vbr',
                '-b:v', '5M',
                '-metadata', f'preprocessed="yes"',
                '-movflags', '+use_metadata_tags',
                output_path
            ], check=True)
            self.video_processed.emit(True, output_path)
        except subprocess.CalledProcessError as e:
            self.video_processed.emit(False, output_path)



class CheckProcessedVideo(QThread):
    video_checked = pyqtSignal(bool)  # Sinal para enviar o caminho do vídeo e as miniaturas

    def __init__(self, video_path):
        super().__init__()
        self.video_path = video_path

    def run(self):
        # Carregar miniaturas
        cmd = [
            './ffprobe',
            '-v', 'error',
            '-show_entries', 'format_tags=preprocessed',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            self.video_path
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            # Adicione estes prints para debug
            comp = result.stdout.replace('\r', '').replace('\n', '').strip()
            comp2 = '"yes"'
            # print(f"Conteúdo exato: '{comp}'")  # Com aspas para ver espaços invisíveis
            # print(f"Bytes da string: {[ord(c) for c in comp]}")
            # print(f"Bytes da string: {[ord(c) for c in comp2]}")
            # print(f"Comprimento: {len(comp)}")
            # print(f"Comprimento: {len(comp2)}")

            if result.returncode==0 and comp==comp2:
                self.video_checked.emit(True)
            else:
                self.video_checked.emit(False)
        except subprocess.CalledProcessError:
            self.video_checked.emit(False)
