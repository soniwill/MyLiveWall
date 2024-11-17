import json
import os

class LiveWallState:
    """Manages persistent state of the video wallpaper"""
    def __init__(self):
        self.config_dir = os.path.expanduser("~/.config/MyLiveWall")
        self.state_file = os.path.join(self.config_dir, "state.json")
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        """Ensure configuration directory exists"""
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)

    def save_state(self, video_path, is_playing=True):
        """Save current wallpaper state"""
        state = {
            "video_path": video_path,
            "is_playing": is_playing
        }
        with open(self.state_file, "w") as f:
            json.dump(state, f)

    def load_state(self):
        """Load saved wallpaper state"""
        if not os.path.exists(self.state_file):
            return None
        try:
            with open(self.state_file, "r") as f:
                return json.load(f)
        except:
            return None

    def clear_state(self):
        """Clear saved state"""
        if os.path.exists(self.state_file):
            os.remove(self.state_file)