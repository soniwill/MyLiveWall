import subprocess
import os
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass


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


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Cria um GIF preview de um vídeo')
    parser.add_argument('input_video', help='Caminho do vídeo de entrada')
    parser.add_argument('--start', type=float, help='Tempo inicial em segundos')
    parser.add_argument('--end', type=float, help='Tempo final em segundos')
    parser.add_argument('--duration', type=float, default=3.0,
        help='Duração do trecho a ser convertido em segundos')
    parser.add_argument('--width', type=int, default=480,
        help='Largura do GIF em pixels')
    parser.add_argument('--fps', type=int, default=12,
        help='Frames por segundo')
    parser.add_argument('--frame-skip', type=int, default=1,
        help='Número de frames para pular')
    parser.add_argument('--output', help='Caminho do GIF de saída (opcional)')

    args = parser.parse_args()

    # Define o intervalo de tempo se especificado
    time_range = None
    if args.start is not None and args.end is not None:
        time_range = (args.start, args.end)

    VideoToGif.create_preview(
        args.input_video,
        time_range=time_range,
        sample_duration=args.duration,
        width=args.width,
        fps=args.fps,
        frame_skip=args.frame_skip,
        output_gif=args.output
    )


if __name__=="__main__":
    main()