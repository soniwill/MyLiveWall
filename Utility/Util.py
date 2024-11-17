import sys
import os
import subprocess
import tempfile
import hashlib
import urllib.parse
from PIL import Image
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass

# Cores inspiradas no Pop!_OS
COLORS = {
    'bg_primary': '#2B2B2B',
    'bg_secondary': '#333333',
    'accent': '#48B9C7',
    'text_primary': '#FFFFFF',
    'text_secondary': '#BBBBBB',
    'hover': '#3E3E3E',
    'selected': '#48B9C7',
    'border': '#404040'
}
def get_file_path(file_name):
        # Define o caminho do script .sh de acordo com o modo (desenvolvimento ou executável)
        if getattr(sys, 'frozen', False):
            # Caminho no executável gerado pelo PyInstaller
            base_path = sys._MEIPASS
        else:
            # Caminho no ambiente de desenvolvimento
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, file_name)

def get_thumbnail_path(file_path):
    """Get the thumbnail path from the freedesktop thumbnail cache"""
    file_uri = f"file://{urllib.parse.quote(os.path.abspath(file_path))}"
    file_hash = hashlib.md5(file_uri.encode()).hexdigest()

    cache_dirs = [
        os.path.expanduser("~/.cache/thumbnails/large"),
        os.path.expanduser("~/.cache/thumbnails/normal"),
        os.path.expanduser("~/.thumbnails/large"),
        os.path.expanduser("~/.thumbnails/normal")
    ]

    for cache_dir in cache_dirs:
        thumb_path = os.path.join(cache_dir, f"{file_hash}.png")
        if os.path.exists(thumb_path):
            return thumb_path

    return None

def get_gif_path(file_path):
    """Get the thumbnail path from the freedesktop thumbnail cache"""
    cache_dir = os.path.expanduser("~/.cache/my_gif_cache")

    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    file_hash = hashlib.md5(os.path.abspath(file_path).encode()).hexdigest()
    gif_cache_path = os.path.join(cache_dir, f"{file_hash}.gif")

    # Check if the cached GIF already exists
    if os.path.exists(gif_cache_path):
        return gif_cache_path

    return None

def generate_thumbnail(video_path):
    """Generate a thumbnail using PIL and ffmpeg"""
    try:
        temp_thumb = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        temp_thumb_path = temp_thumb.name
        temp_thumb.close()

        command = [
            './ffmpeg',
            '-y',
            '-i', video_path,
            '-ss', '00:00:01',
            '-vframes', '1',
            '-f', 'image2',
            temp_thumb_path
        ]

        subprocess.run(command, capture_output=True)

        if os.path.exists(temp_thumb_path):
            return temp_thumb_path

    except Exception as e:
        print(f"Erro ao gerar thumbnail: {e}")
        return None

def aspect_ratio_size(image, target_width, target_height):
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

    return new_width, new_height

def generate_thumbnail_gif(video_path, thumbnail_size=(150, 100)):
    """Generate a thumbnail using PIL and ffmpeg"""
    cache_dir = os.path.expanduser("~/.cache/my_gif_cache")
    try:
        file_hash = hashlib.md5(os.path.abspath(video_path).encode()).hexdigest()
        gif_cache_path = os.path.join(cache_dir, f"{file_hash}.gif")

        image = Image.open(get_linux_thumbnail(video_path))
        w, h = aspect_ratio_size(image, thumbnail_size[0], thumbnail_size[1])

        # subprocess.run(ffmpeg_command)
        VideoToGif.VideoToGif.create_preview(video_path, width=w, output_gif=gif_cache_path, frame_skip=5, fps=10)

        if os.path.exists(gif_cache_path):
            return gif_cache_path

    except Exception as e:
        print(f"Erro ao gerar thumbnail: {e}")
        return None

def check_video_preprocessed(video_path):
    cmd = [
        './ffprobe',
        '-v', 'error',
        '-show_entries', 'format_tags=preprocessed',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
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
        print(f"Conteúdo exato: '{comp}'")  # Com aspas para ver espaços invisíveis
        print(f"Bytes da string: {[ord(c) for c in comp]}")
        print(f"Bytes da string: {[ord(c) for c in comp2]}")
        print(f"Comprimento: {len(comp)}")
        print(f"Comprimento: {len(comp2)}")

        if result.returncode==0 and comp==comp2:
            return True
        else:
            return False
    except subprocess.CalledProcessError:
        return False

def get_linux_thumbnail(video_path):
    thumb_path = get_thumbnail_path(video_path)
    if thumb_path and os.path.exists(thumb_path):
        return thumb_path
    return generate_thumbnail(video_path)


def get_linux_thumbnail_preview(video_path):
    thumb_path = get_gif_path(video_path)
    if thumb_path and os.path.exists(thumb_path):
        return thumb_path
    return generate_thumbnail_gif(video_path)

@dataclass
class VideoMetadata:
    """Classe para armazenar metadados do vídeo."""
    duration: float
    width: int
    height: int
    fps: float


class VideoToGif:
    """Classe estática para converter vídeos em GIFs previews otimizados."""

    @staticmethod
    def get_video_metadata(video_path: str) -> VideoMetadata:
        """
        Obtém metadados do vídeo usando FFprobe.

        Args:
            video_path (str): Caminho do vídeo

        Returns:
            VideoMetadata: Objeto contendo os metadados do vídeo
        """
        # Comando para obter formato do vídeo
        format_cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]

        try:
            result = subprocess.run(format_cmd, capture_output=True, text=True)
            width, height, fps_str, duration = result.stdout.strip().split('\n')

            # Calcula FPS da fração retornada (ex: 30000/1001)
            fps_num, fps_den = map(int, fps_str.split('/'))
            fps = fps_num / fps_den

            return VideoMetadata(
                duration=float(duration),
                width=int(width),
                height=int(height),
                fps=fps
            )
        except Exception as e:
            print(f"Erro ao obter metadados: {str(e)}")
            return VideoMetadata(0.0, 0, 0, 0.0)

    @staticmethod
    def format_timecode(seconds: float) -> str:
        """
        Formata o tempo em segundos para o formato aceito pelo FFmpeg.

        Args:
            seconds (float): Tempo em segundos

        Returns:
            str: Tempo formatado com ponto como separador decimal
        """
        return f"{seconds:.3f}".replace(',', '.')

    @staticmethod
    def calculate_time_range(
            video_duration: float,
            time_range: Optional[Tuple[float, float]],
            sample_duration: float
    ) -> Tuple[float, float]:
        """
        Calcula o intervalo de tempo efetivo para o GIF.

        Args:
            video_duration (float): Duração total do vídeo
            time_range (tuple, optional): Tupla com (início, fim) em segundos
            sample_duration (float): Duração desejada do trecho

        Returns:
            Tuple[float, float]: Tupla com (tempo_inicial, duração)
        """
        if time_range is None:
            # Se não especificado, pega um trecho do meio do vídeo
            middle_point = video_duration / 2
            start_time = max(0, middle_point - (sample_duration / 2))
            duration = min(sample_duration, video_duration - start_time)
        else:
            start_time, end_time = time_range
            # Valida e ajusta o intervalo de tempo
            start_time = max(0, min(start_time, video_duration))
            end_time = min(end_time, video_duration)
            duration = end_time - start_time

        return start_time, duration

    @staticmethod
    def build_filter_complex(
            frame_skip: int,
            width: int,
            fps: int
    ) -> str:
        """
        Constrói a string de filtros complexos do FFmpeg.

        Args:
            frame_skip (int): Número de frames para pular
            width (int): Largura desejada
            fps (int): FPS desejado

        Returns:
            str: String de filtros complexos
        """
        return (
            f"select='not(mod(n,{frame_skip}))',"
            f"scale={width}:-1:flags=lanczos,"
            f"fps={fps},"
            f"split[s0][s1];"
            f"[s0]palettegen=stats_mode=single[p];"
            f"[s1][p]paletteuse=new=true"
        )

    @staticmethod
    def create_preview(
            input_video: str,
            time_range: Optional[Tuple[float, float]] = None,
            sample_duration: float = 3.0,
            width: int = 480,
            fps: int = 12,
            frame_skip: int = 1,
            output_gif: Optional[str] = None
    ) -> bool:
        """
        Cria um GIF preview de um vídeo usando FFmpeg com otimizações.

        Args:
            input_video (str): Caminho do vídeo de entrada
            time_range (tuple, optional): Tupla com (início, fim) em segundos
            sample_duration (float): Duração do trecho em segundos
            width (int): Largura do GIF em pixels
            fps (int): Frames por segundo desejados
            frame_skip (int): Número de frames para pular
            output_gif (str, optional): Caminho do GIF de saída

        Returns:
            bool: True se a conversão foi bem sucedida
        """
        if not os.path.exists(input_video):
            raise FileNotFoundError(f"Vídeo não encontrado: {input_video}")

        if output_gif is None:
            output_gif = str(Path(input_video).with_suffix('')) + "_preview.gif"

        # Obtém metadados do vídeo
        metadata = VideoToGif.get_video_metadata(input_video)

        # Calcula intervalo de tempo
        start_time, duration = VideoToGif.calculate_time_range(
            metadata.duration, time_range, sample_duration
        )
        if (start_time==0 and duration==0):
            duration = 3.0

        # Constrói filtros
        filter_complex = VideoToGif.build_filter_complex(frame_skip, width, fps)

        # Monta comando FFmpeg
        ffmpeg_command: List[str] = [
            "./ffmpeg",
            "-ss", VideoToGif.format_timecode(start_time),
            "-t", VideoToGif.format_timecode(duration),
            "-hwaccel", "auto",
            "-threads", "0",
            "-i", input_video,
            "-vf", filter_complex,
            "-y",
            output_gif
        ]

        try:
            # Executa FFmpeg
            result = subprocess.run(
                ffmpeg_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )

            if os.path.exists(output_gif):
                print(f"GIF preview gerado com sucesso: {output_gif}")
                print(f"Configurações utilizadas:")
                print(f"- Intervalo: {start_time:.2f}s até {start_time + duration:.2f}s")
                print(f"- Duração: {duration:.2f} segundos")
                print(f"- Largura: {width} pixels")
                print(f"- FPS: {fps}")
                print(f"- Frame skip: {frame_skip} (1 a cada {frame_skip} frames)")

                # Mostra comando executado para debug
                print("\nComando FFmpeg executado:")
                print(" ".join(ffmpeg_command))
                return True
            return False

        except subprocess.CalledProcessError as e:
            print(f"Erro ao executar FFmpeg:")
            print(f"Código de erro: {e.returncode}")
            print(f"Saída de erro:")
            print(e.stderr)
            print("\nComando que gerou o erro:")
            print(" ".join(ffmpeg_command))
            return False
        except Exception as e:
            print(f"Erro inesperado: {str(e)}")
            return False