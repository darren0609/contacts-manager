import json
from datetime import datetime

class AppState:
    def __init__(self):
        self.cache_ready = False
        self.last_cache_update = None
    
    def check_duplicate_cache_status(self):
        try:
            with open("duplicate_cache_status.json", "r") as f:
                status = json.load(f)
                self.last_cache_update = datetime.fromisoformat(status["last_update"])
                self.cache_ready = status["status"] == "success"
        except (FileNotFoundError, json.JSONDecodeError):
            self.cache_ready = False
            self.last_cache_update = None

app_state = AppState() 