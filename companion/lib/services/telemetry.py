import psutil
import time

class TelemetryService:
    def __init__(self):
        self.last_net_io = psutil.net_io_counters()
        self.last_time = time.time()
        # Prime CPU usage
        psutil.cpu_percent(interval=None)

    def get_stats(self):
        # CPU
        cpu_usage = psutil.cpu_percent(interval=None)
        
        # RAM
        ram = psutil.virtual_memory()
        ram_usage = ram.percent
        
        # Network Speed (Calculated delta)
        current_time = time.time()
        current_net_io = psutil.net_io_counters()
        
        elapsed = current_time - self.last_time
        if elapsed < 1.0: elapsed = 1.0
        
        # Bytes per second (Prevent division by zero implied by elapsed check)
        upload_speed = (current_net_io.bytes_sent - self.last_net_io.bytes_sent) / elapsed
        download_speed = (current_net_io.bytes_recv - self.last_net_io.bytes_recv) / elapsed
        
        # Update last state
        self.last_net_io = current_net_io
        self.last_time = current_time
        
        # Temperature (Best Effort)
        temp = 0
        try:
            # Windows usually returns empty here without OpenHardwareMonitor
            # Linux requires lm-sensors
            temps = psutil.sensors_temperatures() 
            if temps:
                # Get first available temp
                for name, entries in temps.items():
                    if entries:
                        temp = entries[0].current
                        break
        except:
            temp = 0

        return {
            "type": "telemetry",
            "cpu": cpu_usage,
            "ram": ram_usage,
            "temp": temp,
            "net_up": upload_speed,   # Bytes/sec
            "net_down": download_speed # Bytes/sec
        }

telemetry_service = TelemetryService()
