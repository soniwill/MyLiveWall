import sys
import time
import subprocess
from PyQt6.QtWidgets import QApplication
from Widgets.Widgets import  SettingsDialogWidget, MyLiveWallWidget
from Core.LiveWallPIDManager import LiveWallPIDManager
from Core.LiveWallPlayer import  LiveWallPlayer
from Core.LiveWallState import  LiveWallState


if __name__ == "__main__":
    if "--headless" in sys.argv:
        player = LiveWallPlayer()
        process_manager = LiveWallPIDManager()
        settings = SettingsDialogWidget.load_settings()
        wallpaper_state = LiveWallState()
        state = wallpaper_state.load_state()
        # if state and state.get("video_path"):
        #     print(settings)
        player.set_video_output(settings["vo"])
        player.set_gpu_context(settings["gpu_context"])
        player.set_gpu_api(settings["gpu_api"])
        player.set_hwdec(settings["hwdec"])
        player.set_selected_monitor(settings["selected_monitor"])
        player.set_play_all_monitors(settings["play_all_monitors"])
        player.set_video_path(state["video_path"])
        player.start()
        time.sleep(1)

        # Obter PIDs dos processos xwinwrap
        child_pids = []
        try:
            ps_output = subprocess.check_output(['pgrep', 'xwinwrap']).decode()
            child_pids = [int(pid) for pid in ps_output.splitlines()]
        except subprocess.CalledProcessError:
            pass

        # Salvar informações dos processos
        process_manager.save_process_info(0, child_pids)
        try:
            # Manter o modo headless ativo até o encerramento manual
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Headless mode terminated by user.")
        sys.exit(0)
    else:
        app = QApplication(sys.argv)
        window = MyLiveWallWidget()
        window.show()
        sys.exit(app.exec())