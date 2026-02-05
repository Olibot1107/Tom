#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Raspberry Pi 5 Ribbon Display - Tim
Combined terminal UI and OLED display with cool animations and system monitoring
"""

import time
import sys
import os
import random
import threading
from datetime import datetime
from small import PiOLED, DisplayType, Color, LoadingStyle, create_ssd1306

# ====================
# Configuration
# ====================
CONFIG = {
    "terminal": {
        "font_size": 24,
        "colors": [
            "\033[91m",  # Red
            "\033[92m",  # Green
            "\033[93m",  # Yellow
            "\033[94m",  # Blue
            "\033[95m",  # Magenta
            "\033[96m",  # Cyan
            "\033[97m",  # White
        ],
        "delay": 0.1,
        "clear_screen": True,
    },
    "oled": {
        "display_type": DisplayType.SSD1306,
        "interface": "i2c",
        "port": 1,
        "address": 0x3C,
        "width": 128,
        "height": 64,
        "rotate": 0,
    },
}

# ====================
# System Information
# ====================
def get_system_info():
    """Get system information"""
    try:
        # Get CPU temperature (Raspberry Pi specific)
        temp_file = "/sys/class/thermal/thermal_zone0/temp"
        if os.path.exists(temp_file):
            with open(temp_file, 'r') as f:
                temp = int(f.read()) / 1000.0
            cpu_temp = f"{temp:.1f}°C"
        else:
            cpu_temp = "N/A"
            
        # Get memory usage
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

# ====================
# Terminal UI Class
# ====================
class TerminalUI:
    """Terminal UI for Raspberry Pi 5 Ribbon Display"""
    
    def __init__(self):
        self.width = 80
        self.height = 24
        self.start_time = time.time()
        
    def clear_screen(self):N
        """Clear the terminal screen"""
        os.system("cls" if os.name == "nt" else "clear")
        
    def center_text(self, text, width=None):
        """Center text horizontally"""
        if width is None:
            width = self.width
        return text.center(width)
        
    def draw_header(self):
        """Draw the main header with cool animation"""
        colors = CONFIG["terminal"]["colors"]
        header_text = "🔥 RASPBERRY PI 5 RIBBON DISPLAY 🔥"
        
        rainbow_text = []
        for i, char in enumerate(header_text):
            color = colors[i % len(colors)]
            rainbow_text.append(f"{color}{char}")
            
        print(f"\033[1m{''.join(rainbow_text)}\033[0m")
        print(f"{colors[3]}=" * self.width)
        
    def draw_time_date(self):
        """Draw big time and date display"""
        colors = CONFIG["terminal"]["colors"]
        
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        date_str = now.strftime("%A, %B %d, %Y")
        
        print(f"\n{colors[2]}\033[1m{self.center_text(time_str, 40)}\033[0m")
        print(f"{colors[4]}\033[1m{self.center_text(date_str)}\033[0m")
        
    def draw_system_info(self):
        """Draw system information"""
        colors = CONFIG["terminal"]["colors"]
        cpu_temp, memory = get_system_info()
        
        info_text = (
            f"{colors[1]}CPU: {cpu_temp} | "
            f"{colors[5]}RAM: {memory} | "
            f"{colors[3]}UP: {self.get_uptime()}"
        )
        
        print(f"\n{colors[6]}=" * self.width)
        print(f"{colors[6]}{self.center_text(info_text)}")
        print(f"{colors[6]}=" * self.width)
        
    def draw_footer(self):
        """Draw footer with status indicators"""
        colors = CONFIG["terminal"]["colors"]
        
        animation = [
            "⚡ RUNNING",
            "🚀 ACTIVE",
            "💾 MONITORING",
            "📊 ANALYZING",
            "🔥 OPTIMIZED",
            "✨ POWERED",
            "🌟 READY"
        ]
        
        random_status = random.choice(animation)
        status_text = f"{colors[random.randint(0, len(colors)-1)]}\033[1m{random_status}\033[0m"
        
        print(f"\n{self.center_text(status_text)}")
        
    def get_uptime(self):
        """Get system uptime"""
        uptime_seconds = int(time.time() - self.start_time)
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
    def draw_loading_bar(self, progress=random.randint(0, 100)):
        """Draw animated loading bar"""
        colors = CONFIG["terminal"]["colors"]
        bar_width = 50
        filled_width = int(bar_width * progress / 100)
        bar = f"{'█' * filled_width}{' ' * (bar_width - filled_width)}"
        
        print(f"\n{colors[0]}{self.center_text(f'LOADING: {progress}%')}")
        print(f"{colors[0]}{self.center_text(f'[{bar}]', bar_width + 2)}")
        
    def draw_all(self):
        """Draw complete display"""
        self.clear_screen()
        self.draw_header()
        self.draw_time_date()
        self.draw_loading_bar()
        self.draw_system_info()
        self.draw_footer()
        
    def start(self):
        """Start the terminal display"""
        print("\033[?25l")  # Hide cursor
        
        try:
            while True:
                self.draw_all()
                time.sleep(CONFIG["terminal"]["delay"])
                
        except KeyboardInterrupt:
            self.stop()
            
    def stop(self):
        """Stop the terminal display"""
        print("\033[?25h")  # Show cursor
        self.clear_screen()
        print("👋 Terminal display stopped!")

# ====================
# OLED Display Class
# ====================
class OLEDDisplay:
    """OLED Display for Raspberry Pi 5 Ribbon Display"""
    
    def __init__(self):
        try:
            self.display = create_ssd1306(
                bus=CONFIG["oled"]["port"],
                address=CONFIG["oled"]["address"]
            )
            self.is_active = True
            print("✅ OLED display initialized successfully")
        except Exception as e:
            self.display = None
            self.is_active = False
            print(f"❌ OLED display initialization failed: {e}")
            print("Continuing with terminal UI only...")
            
        self.start_time = time.time()
        
    def clear(self):
        """Clear the OLED display"""
        if self.is_active:
            self.display.clear()
            
    def show(self):
        """Update the OLED display"""
        if self.is_active:
            self.display.show()
            
    def draw_time_date(self):
        """Draw time and date on OLED"""
        if not self.is_active:
            return
            
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        date_str = now.strftime("%d-%m-%Y")
        
        self.display.text(time_str, (10, 5), font_size=24, color=Color.WHITE)
        self.display.text(date_str, (20, 35), font_size=12, color=Color.WHITE)
        
    def draw_system_info(self):
        """Draw system information on OLED"""
        if not self.is_active:
            return
            
        cpu_temp, memory = get_system_info()
        
        self.display.text(f"CPU: {cpu_temp}", (5, 50), font_size=10, color=Color.WHITE)
        self.display.text(f"RAM: {memory}", (65, 50), font_size=10, color=Color.WHITE)
        
    def draw_uptime(self):
        """Draw system uptime on OLED"""
        if not self.is_active:
            return
            
        uptime = self.get_uptime()
        self.display.text(f"UP: {uptime}", (5, 5), font_size=8, color=Color.WHITE)
        
    def draw_loading_animation(self, frame):
        """Draw loading animation on OLED"""
        if not self.is_active:
            return
            
        x = (frame * 2) % (self.display.width - 10)
        y = self.display.height // 2
        
        self.display.circle((x, y), 3, fill=Color.WHITE)
        
    def get_uptime(self):
        """Get system uptime"""
        uptime_seconds = int(time.time() - self.start_time)
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
    def draw_all(self, frame):
        """Draw complete OLED display"""
        if not self.is_active:
            return
            
        self.clear()
        self.draw_time_date()
        self.draw_system_info()
        self.draw_loading_animation(frame)
        self.show()
        
    def start(self):
        """Start the OLED display animation"""
        if not self.is_active:
            return
            
        try:
            frame = 0
            while True:
                self.draw_all(frame)
                frame += 1
                time.sleep(0.05)
                
        except Exception as e:
            print(f"❌ OLED display error: {e}")
            self.is_active = False
            
    def stop(self):
        """Stop the OLED display"""
        if self.is_active:
            self.display.cleanup()
            
class CombinedDisplay:
    """Combined terminal and OLED display"""
    
    def __init__(self):
        self.terminal_ui = TerminalUI()
        self.oled_display = OLEDDisplay()
        self.running = False
        self.terminal_thread = None
        self.oled_thread = None
        
    def start_terminal(self):
        """Start terminal UI in thread"""
        try:
            self.terminal_ui.start()
        except Exception as e:
            print(f"❌ Terminal UI error: {e}")
            
    def start_oled(self):
        """Start OLED display in thread"""
        self.oled_display.start()
        
    def start(self):
        """Start both displays"""
        self.running = True
        
        print("🚀 Initializing Raspberry Pi 5 Ribbon Display...")
        time.sleep(1)
        
        # Start terminal UI
        self.terminal_thread = threading.Thread(
            target=self.start_terminal,
            daemon=True
        )
        self.terminal_thread.start()
        
        # Start OLED display if active
        if self.oled_display.is_active:
            self.oled_thread = threading.Thread(
                target=self.start_oled,
                daemon=True
            )
            self.oled_thread.start()
            
        try:
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.stop()
            
    def stop(self):
        """Stop all displays"""
        self.running = False
        self.terminal_ui.stop()
        self.oled_display.stop()
        
        if self.oled_thread and self.oled_thread.is_alive():
            self.oled_thread.join(timeout=1)
            
        print("👋 All displays stopped!")

# ====================
# Main Application
# ====================
def main():
    """Application entry point"""
    display = CombinedDisplay()
    
    try:
        display.start()
    except Exception as e:
        print(f"❌ Critical error: {e}")
        display.stop()
        sys.exit(1)

if __name__ == "__main__":
    main()
