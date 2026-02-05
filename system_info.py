import os


def get_system_info():
    try:
        temp_file = "/sys/class/thermal/thermal_zone0/temp"
        if os.path.exists(temp_file):
            with open(temp_file, 'r') as f:
                temp = int(f.read()) / 1000.0
            cpu_temp = f"{temp:.1f}°C"
        else:
            cpu_temp = "N/A"

        mem_info = os.popen('free -m').read().split()
        if len(mem_info) > 10:
            mem_used = int(mem_info[8])
            mem_total = int(mem_info[7])
            mem_percent = (mem_used / mem_total) * 100
            memory = f"{mem_used}/{mem_total} MB ({mem_percent:.0f}%)"
        else:
            memory = "N/A"

        return cpu_temp, memory

    except Exception as e:
        return f"Error: {e}", "N/A"
