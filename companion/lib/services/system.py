import sys
import subprocess
import os
import webbrowser

# OS-Specific dependencies
if sys.platform == "win32":
    import ctypes
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

class SystemController:
    """
    Cross-Platform System Controller.
    Abstracts OS-specific implementations for common actions.
    """
    
    @staticmethod
    def lock_screen():
        try:
            if sys.platform == "win32":
                ctypes.windll.user32.LockWorkStation()
            elif sys.platform == "darwin":
                subprocess.run("pmset displaysleepnow", shell=True)
            elif sys.platform.startswith("linux"):
                subprocess.run("xdg-screensaver lock", shell=True)
            
            print(f"[System] Locked Screen ({sys.platform})")
            return True
        except Exception as e:
            print(f"[System] Error locking screen: {e}")
            return False

    @staticmethod
    def set_volume_absolute(percent):
        """Set volume to specific percentage (0-100)"""
        try:
            if sys.platform == "win32":
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = interface.QueryInterface(IAudioEndpointVolume)
                
                val = max(0.0, min(1.0, percent / 100.0))
                volume.SetMasterVolumeLevelScalar(val, None)
                print(f"[System] Volume Set: {int(percent)}% (Native)")
                
            elif sys.platform == "darwin":
                # Mac: 0 to 7 usually, or 0 to 100 via osascript
                vol = int(percent)
                subprocess.run(f"osascript -e 'set volume output volume {vol}'", shell=True)
                
            # TODO: Linux (amixer/pactl)
            return True
        except Exception as e:
            print(f"[System] Error setting volume: {e}")
            return False

    @staticmethod
    def change_volume_relative(delta_percent):
        try:
            if sys.platform == "win32":
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = interface.QueryInterface(IAudioEndpointVolume)
                
                current = volume.GetMasterVolumeLevelScalar()
                new_val = max(0.0, min(1.0, current + (delta_percent / 100.0)))
                volume.SetMasterVolumeLevelScalar(new_val, None)
                print(f"[System] Volume Changed: {int(current*100)}% -> {int(new_val*100)}%")
                
            # TODO: Implement relative for Mac/Linux
            return True
        except Exception as e:
            print(f"[System] Error changing volume: {e}")
            return False

    @staticmethod
    def toggle_mute():
        try:
            if sys.platform == "win32":
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = interface.QueryInterface(IAudioEndpointVolume)
                
                is_muted = volume.GetMute()
                volume.SetMute(not is_muted, None)
                print(f"[System] Mute Toggled: {not is_muted}")
            return True
        except Exception as e:
            print(f"[System] Error toggling mute: {e}")
            return False

# --- Public API (Backward Compatible) ---

def execute_cmd(cmd):
    """Entry point: Parses command string and routes to SystemController"""
    cmd_lower = cmd.lower()
    
    # 1. Platform Agnostic Mapping (Legacy Translation)
    if "lockworkstation" in cmd_lower:
        return SystemController.lock_screen()
    
    if "mutesysvolume" in cmd_lower:
        return SystemController.toggle_mute()

    # Legacy: nircmd.exe changesysvolume -5000
    if "changesysvolume" in cmd_lower:
        try:
            # Extract numbers
            parts = [s for s in cmd_lower.split() if s.lstrip('-').isdigit()]
            if parts:
                raw_val = int(parts[0])
                # Convert 65535 scale to percent
                delta = (raw_val / 65535.0) * 100
                return SystemController.change_volume_relative(delta)
        except:
            pass

    # Legacy: nircmd.exe setsysvolume 65535
    if "setsysvolume" in cmd_lower:
        try:
            parts = [s for s in cmd_lower.split() if s.isdigit()]
            if parts:
                raw_val = int(parts[0])
                pct = (raw_val / 65535.0) * 100
                return SystemController.set_volume_absolute(pct)
        except:
            pass

    # Fallback to Shell
    try:
        subprocess.Popen(cmd, shell=True)
        print(f"[System] Shell Executed: {cmd}")
        return True
    except Exception as e:
        print(f"[System] Shell Error: {e}")
        return False

def open_url(url):
    return SystemController.open_url(url) if hasattr(SystemController, 'open_url') else webbrowser.open(url)

# Alias for server.py imports
def set_volume(val):
    SystemController.set_volume_absolute(val)

def toggle_mute():
    SystemController.toggle_mute()
