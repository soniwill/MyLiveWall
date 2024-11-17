import os
import json
import signal
import subprocess
import time;
from pathlib import Path

class LiveWallPIDManager:
    def __init__(self):
        self.pid_file = Path(f"/var/run/user/{os.getuid()}/live_wallpaper_pids.json")
        self.create_pid_directory()

    def create_pid_directory(self):
        """Ensure the directory for the PID file exists"""
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)

    def save_process_info(self, main_pid, child_pids):
        """Save the main process PID and its child PIDs"""
        data = {
            'main_pid': main_pid,
            'child_pids': child_pids,
            'timestamp': time.time()
        }
        with open(self.pid_file, 'w') as f:
            json.dump(data, f)

    def load_process_info(self):
        """Load saved process information"""
        try:
            with open(self.pid_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def kill_processes(self):
        """Kill all saved processes"""
        process_info = self.load_process_info()
        print(process_info)
        if not process_info:
            return

        # Tenta matar os processos filhos primeiro
        for pid in process_info.get('child_pids', []):
            try:
                os.kill(int(pid), signal.SIGKILL)
            except ProcessLookupError:
                pass

        # Tenta matar o processo principal
        try:
            main_pid = process_info.get('main_pid')
            if main_pid:
                os.kill(int(main_pid), signal.SIGKILL)
        except ProcessLookupError:
            pass

        # Remove o arquivo de PIDs
        try:
            self.pid_file.unlink()
        except FileNotFoundError:
            pass