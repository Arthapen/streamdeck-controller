import json
import os
from pathlib import Path
from ..config import PROFILES_DIR

class ProfileManager:
    def __init__(self):
        os.makedirs(PROFILES_DIR, exist_ok=True)
        self.default_profile = os.path.join(PROFILES_DIR, "default.json")

    def get_profile_path(self, device_id):
        clean_id = "".join(x for x in device_id if x.isalnum() or x in "_-")
        return Path(os.path.join(PROFILES_DIR, f"profile_{clean_id}.json"))

    def load_profile(self, device_id):
        path = self.get_profile_path(device_id)
        if not path.exists():
            # Return empty default struct
            return {"rootPage": "home", "pages": {"home": []}}
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self._migrate(data, path)
        except Exception as e:
            print(f"[Profile] Error loading {device_id}: {e}")
            return {"rootPage": "home", "pages": {"home": []}}

    def _migrate(self, data, path):
        # V1 -> V2 Migration
        if "layout" in data and "pages" not in data:
            print(f"[Profile] Migrating {path} to V2")
            data["pages"] = { "home": data.pop("layout") }
            data["rootPage"] = "home"
            self.save_raw_profile(path, data)
        return data

    def save_layout_change(self, device_id, page_id, new_layout):
        path = self.get_profile_path(device_id)
        data = self.load_profile(device_id)
        
        # Ensure structure
        if "pages" not in data: data["pages"] = {"home": []}
        if page_id not in data["pages"]: data["pages"][page_id] = []
        
        # Merge logic (Update positions AND allow new items)
        current_page = data["pages"][page_id]
        item_map = {item["id"]: item for item in current_page}
        
        final_page = []
        for item in new_layout:
            if item["id"] in item_map:
                # Merge existing (preserve backend props if any)
                w = item_map[item["id"]]
                w["x"] = item.get("x")
                w["y"] = item.get("y")
                w["w"] = item.get("w")
                w["h"] = item.get("h")
                final_page.append(w)
            else:
                # New item
                final_page.append(item)
        
        data["pages"][page_id] = final_page
        self.save_raw_profile(path, data)

    def save_raw_profile(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

profile_manager = ProfileManager()
