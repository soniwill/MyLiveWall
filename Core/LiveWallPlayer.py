import subprocess
import json
from screeninfo import get_monitors

class LiveWallPlayer:
    def __init__(self):
        self.video_output = "gpu"
        self.gpu_context = "x11vk"
        self.gpu_api = "vulkan"
        self.hwdec = "vulkan"
        self.play_all_monitors = True
        self.selected_monitor = ""
        self.video_path = ""
        self.pids = []

    def set_video_output(self, output):
        self.video_output = output

    def set_gpu_context(self, context):
        self.gpu_context = context

    def set_gpu_api(self, api):
        self.gpu_api = api

    def set_hwdec(self, hwdec):
        self.hwdec = hwdec

    def set_play_all_monitors(self, play_all):
        self.play_all_monitors = play_all

    def set_selected_monitor(self, monitor):
        self.selected_monitor = monitor
        self.play_all_monitors = False

    def set_video_path(self, path):
        self.video_path = path

    def calculate_aspect(self, width, height):
        gcd_value = self.gcd(width, height)
        return f"{width // gcd_value}:{height // gcd_value}"

    @staticmethod
    def gcd(a, b):
        while b:
            a, b = b, a % b
        return a

    def _screen(self, geometry, aspect):
        cmd = [
            "xwinwrap", "-fdt", "-ni", "-nf", "-un", "-o", "1.0", "-d", "-g", geometry,
            "--", "mpv", "--fullscreen", "--no-config", "--no-stop-screensaver",
            f"--vo={self.video_output}", f"--hwdec={self.hwdec}",
            f"--gpu-api={self.gpu_api}", f"--gpu-context={self.gpu_context}",
            "--loop-file", f"--geometry={geometry}", "--panscan=1.0", "--no-audio",
            "--no-osd-bar", "-wid", "WID", "--no-input-default-bindings", self.video_path
        ]
        process = subprocess.Popen(cmd)
        return process.pid

    def process_monitor(self, monitor):
        width, height = monitor.width, monitor.height
        geometry = f"{width}x{height}+{monitor.x}+{monitor.y}"
        aspect = self.calculate_aspect(width, height)
        pid = self._screen(geometry, aspect)
        self.pids.append(pid)

    def start(self):
        monitors = get_monitors()
        if self.play_all_monitors:
            for monitor in monitors:
                self.process_monitor(monitor)
        else:
            selected_monitor = next(
                (m for m in monitors if m.name == self.selected_monitor), None
            )
            if selected_monitor:
                self.process_monitor(selected_monitor)
            else:
                print("Monitor selecionado não encontrado")
                return

    def get_pids_json(self):
        return json.dumps({"pids": self.pids})


