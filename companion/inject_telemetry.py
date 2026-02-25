import json
import glob
import os

PROFILES_DIR = "d:/Programacion/streamdeck-controller/companion/profiles"

def update_profile(path):
    print(f"Procesando {path}...")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Ensure utilities page exists
        if "pages" not in data: return
        if "utilities" not in data["pages"]:
            data["pages"]["utilities"] = []
            
        page = data["pages"]["utilities"]
        
        # Define Widgets
        widgets = [
            {
                "id": "cpu_gauge",
                "type": "gauge",
                "metric": "cpu",
                "label": "CPU Load",
                "x": 0, "y": 0, "w": 4, "h": 2
            },
            {
                "id": "ram_gauge",
                "type": "gauge",
                "metric": "ram",
                "label": "RAM Usage",
                "x": 4, "y": 0, "w": 4, "h": 2
            },
            {
                "id": "temp_gauge",
                "type": "gauge",
                "metric": "temp",
                "label": "CPU Temp",
                "x": 8, "y": 0, "w": 4, "h": 2
            }
        ]
        
        # Remove existing stats to prevent dups
        data["pages"]["utilities"] = [w for w in page if w.get("type") not in ["gauge", "stat"]]
        
        # Add new widgets
        data["pages"]["utilities"].extend(widgets)
        print("  -> Inyectados 3 widgets en 'utilities'")

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
    except Exception as e:
        print(f"  Error: {e}")

files = glob.glob(os.path.join(PROFILES_DIR, "*.json"))
for p in files:
    update_profile(p)
