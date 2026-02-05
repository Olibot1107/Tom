"""
PiOLED - A clean, feature-rich OLED library for Raspberry Pi
Supports: SSD1306 (Monochrome), SSD1331 (Color), and SH1106 displays
"""

from luma.core.interface.serial import i2c, spi
from luma.oled.device import ssd1306, ssd1331, sh1106
from luma.core.render import canvas
from PIL import Image, ImageDraw, ImageFont, ImageSequence, ImageEnhance, ImageFilter
import time
import os
import shutil
import threading
from enum import Enum
from typing import Tuple, Optional, List, Union
import math


class DisplayType(Enum):
    SSD1306 = "ssd1306"  # Monochrome 128x64/128x32 I2C/SPI
    SSD1331 = "ssd1331"  # Color 96x64 SPI
    SH1106 = "sh1106"    # Monochrome 128x64 I2C


class Color:
    """Color palette for OLED displays"""
    # Monochrome
    BLACK = 0
    WHITE = 255
    
    # Color OLED (SSD1331) - RGB565 format
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)
    YELLOW = (255, 255, 0)
    CYAN = (0, 255, 255)
    MAGENTA = (255, 0, 255)
    ORANGE = (255, 165, 0)
    PURPLE = (128, 0, 128)
    PINK = (255, 192, 203)
    
    @staticmethod
    def rgb(r: int, g: int, b: int) -> Tuple[int, int, int]:
        """Create RGB color tuple"""
        return (r, g, b)
    
    @staticmethod
    def hex(hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


class LoadingStyle(Enum):
    SPINNER = "spinner"
    BAR = "bar"
    DOTS = "dots"
    PULSE = "pulse"
    BOUNCE = "bounce"


class PiOLED:
    """
    Clean, intuitive OLED interface with color support and animations
    """
    
    def __init__(
        self,
        display_type: DisplayType = DisplayType.SSD1306,
        interface: str = "i2c",
        port: int = 1,
        address: int = 0x3C,
        gpio_dc: int = 24,
        gpio_rst: int = 25,
        width: int = None,
        height: int = None,
        rotate: int = 0
    ):
        """
        Initialize OLED display
        
        Args:
            display_type: Type of OLED display
            interface: "i2c" or "spi"
            port: I2C bus number or SPI port
            address: I2C address (for I2C mode)
            gpio_dc: GPIO pin for DC (SPI mode)
            gpio_rst: GPIO pin for RST (SPI mode)
            width: Display width (auto-detected if None)
            height: Display height (auto-detected if None)
            rotate: Rotation in degrees (0, 90, 180, 270)
        """
        self.display_type = display_type
        self.interface = interface
        self.is_color = (display_type == DisplayType.SSD1331)
        
        # Initialize serial interface
        if interface == "i2c":
            serial = i2c(port=port, address=address)
        else:
            from luma.core.interface.serial import spi
            serial = spi(
                port=port,
                device=0,
                gpio_DC=gpio_dc,
                gpio_RST=gpio_rst
            )
        
        # Initialize device
        device_class = {
            DisplayType.SSD1306: ssd1306,
            DisplayType.SSD1331: ssd1331,
            DisplayType.SH1106: sh1106
        }[display_type]
        
        self.device = device_class(
            serial,
            width=width,
            height=height,
            rotate=rotate
        )
        
        # Setup buffer
        self.width = self.device.width
        self.height = self.device.height
        self.mode = 'RGB' if self.is_color else '1'
        self.buffer = Image.new(self.mode, (self.width, self.height))
        self.draw = ImageDraw.Draw(self.buffer)
        
        # Font setup
        self.fonts = {}
        self._load_default_fonts()
        
        # Animation state
        self._loading_active = False
        self._loading_thread = None
        self._loading_stop = threading.Event()
        
    def _load_default_fonts(self):
        """Load system fonts with fallbacks"""
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        ]
        
        self.default_font = ImageFont.load_default()
        
        for path in font_paths:
            if os.path.exists(path):
                self.fonts['default'] = path
                break
        else:
            self.fonts['default'] = None
            
    def _get_font(self, size: int = 12, font_path: str = None) -> ImageFont:
        """Get font at specified size"""
        if font_path is None:
            font_path = self.fonts.get('default')
            
        if font_path and os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except:
                pass
        return self.default_font
    
    # ==================== Core Display Methods ====================
    
    def clear(self, color: Union[str, Tuple, int] = None):
        """
        Clear display with optional background color
        
        Args:
            color: Color to fill (default: black)
        """
        if color is None:
            color = Color.BLACK if not self.is_color else (0, 0, 0)
        
        self.buffer = Image.new(self.mode, (self.width, self.height), color)
        self.draw = ImageDraw.Draw(self.buffer)
        
    def show(self):
        """Update the physical display with buffer contents"""
        self.device.display(self.buffer)
        
    def update(self):
        """Alias for show()"""
        self.show()
        
    def fill(self, color: Union[str, Tuple, int]):
        """Fill entire display with color"""
        self.clear(color)
        
    def set_brightness(self, level: float):
        """
        Set display brightness (0.0 to 1.0)
        Note: Only works on some displays
        """
        if hasattr(self.device, 'contrast'):
            self.device.contrast(int(level * 255))
            
    def invert(self, enabled: bool = True):
        """Invert display colors"""
        if hasattr(self.device, 'invert'):
            self.device.invert(enabled)
            
    def sleep(self):
        """Put display to sleep"""
        if hasattr(self.device, 'hide'):
            self.device.hide()
            
    def wake(self):
        """Wake display from sleep"""
        if hasattr(self.device, 'show'):
            self.device.show()
            
    def cleanup(self):
        """Clean up resources"""
        self.stop_loading()
        self.clear()
        self.show()
        
    # ==================== Drawing Primitives ====================
    
    def _parse_color(self, color) -> Union[int, Tuple]:
        """Convert color to display format"""
        if color is None:
            return Color.WHITE if not self.is_color else Color.WHITE
            
        if isinstance(color, str):
            if hasattr(Color, color.upper()):
                return getattr(Color, color.upper())
            if color.startswith('#'):
                return Color.hex(color)
                
        return color
    
    def pixel(self, x: int, y: int, color=None):
        """Draw a single pixel"""
        color = self._parse_color(color)
        self.draw.point((x, y), fill=color)
        
    def line(self, start: Tuple[int, int], end: Tuple[int, int], 
             color=None, width: int = 1):
        """Draw a line"""
        color = self._parse_color(color)
        self.draw.line([start, end], fill=color, width=width)
        
    def rectangle(self, xy: Tuple[int, int, int, int], 
                  outline=None, fill=None, width: int = 1):
        """
        Draw rectangle
        
        Args:
            xy: (x1, y1, x2, y2) coordinates
            outline: Border color
            fill: Fill color
            width: Border width
        """
        outline = self._parse_color(outline) if outline else None
        fill = self._parse_color(fill) if fill else None
        self.draw.rectangle(xy, outline=outline, fill=fill, width=width)
        
    def circle(self, center: Tuple[int, int], radius: int, 
               outline=None, fill=None, width: int = 1):
        """Draw a circle"""
        outline = self._parse_color(outline) if outline else None
        fill = self._parse_color(fill) if fill else None
        x, y = center
        bbox = (x - radius, y - radius, x + radius, y + radius)
        self.draw.ellipse(bbox, outline=outline, fill=fill, width=width)
        
    def ellipse(self, xy: Tuple[int, int, int, int], 
                outline=None, fill=None, width: int = 1):
        """Draw an ellipse"""
        outline = self._parse_color(outline) if outline else None
        fill = self._parse_color(fill) if fill else None
        self.draw.ellipse(xy, outline=outline, fill=fill, width=width)
        
    def arc(self, xy: Tuple[int, int, int, int], 
            start: int, end: int, color=None, width: int = 1):
        """Draw an arc (angles in degrees)"""
        color = self._parse_color(color)
        self.draw.arc(xy, start, end, fill=color, width=width)
        
    def pie(self, xy: Tuple[int, int, int, int], 
            start: int, end: int, fill=None, outline=None):
        """Draw a pie slice"""
        fill = self._parse_color(fill) if fill else None
        outline = self._parse_color(outline) if outline else None
        self.draw.pieslice(xy, start, end, fill=fill, outline=outline)
        
    def polygon(self, points: List[Tuple[int, int]], 
                outline=None, fill=None):
        """Draw a polygon"""
        outline = self._parse_color(outline) if outline else None
        fill = self._parse_color(fill) if fill else None
        self.draw.polygon(points, outline=outline, fill=fill)
        
    def text(self, text: str, position: Tuple[int, int] = (0, 0),
             color=None, font_size: int = 12, font_path: str = None,
             anchor: str = None, spacing: int = 4):
        """
        Draw text
        
        Args:
            text: Text to display
            position: (x, y) coordinates
            color: Text color
            font_size: Font size in pixels
            font_path: Path to custom font
            anchor: PIL anchor (e.g., "mm" for center)
            spacing: Line spacing for multiline
        """
        color = self._parse_color(color)
        font = self._get_font(font_size, font_path)
        
        # Handle multiline text
        lines = text.split('\n')
        x, y = position
        
        for i, line in enumerate(lines):
            line_y = y + (i * (font_size + spacing))
            if anchor:
                self.draw.text((x, line_y), line, font=font, fill=color, anchor=anchor)
            else:
                self.draw.text((x, line_y), line, font=font, fill=color)
                
    def centered_text(self, text: str, y: int = None, 
                      color=None, font_size: int = 12):
        """Draw centered text"""
        if y is None:
            y = self.height // 2
            
        color = self._parse_color(color)
        font = self._get_font(font_size)
        
        # Calculate text size
        bbox = self.draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        x = (self.width - text_width) // 2
        
        self.draw.text((x, y), text, font=font, fill=color)
        
    # ==================== Image Handling ====================
    
    def image(self, img: Union[str, Image.Image], 
              position: Tuple[int, int] = (0, 0),
              size: Tuple[int, int] = None,
              dither: bool = True):
        """
        Display an image
        
        Args:
            img: Image path or PIL Image object
            position: (x, y) position
            size: (width, height) to resize, or None for original
            dither: Apply dithering for monochrome displays
        """
        if isinstance(img, str):
            if not os.path.exists(img):
                raise FileNotFoundError(f"Image not found: {img}")
            img = Image.open(img)
            
        # Convert to appropriate mode
        if self.is_color:
            if img.mode != 'RGB':
                img = img.convert('RGB')
        else:
            if img.mode != '1':
                if dither:
                    img = img.convert('1', dither=Image.FLOYDSTEINBERG)
                else:
                    img = img.convert('1')
                    
        # Resize if needed
        if size:
            img = img.resize(size, Image.LANCZOS)
            
        # Paste onto buffer
        if self.is_color:
            self.buffer.paste(img, position)
        else:
            # For monochrome, handle paste differently
            self.buffer.paste(img, position)
            
    def gif(self, path: str, loops: int = 1, 
            position: Tuple[int, int] = (0, 0),
            background: Union[str, Tuple] = None):
        """
        Play GIF animation (blocking)
        
        Args:
            path: Path to GIF file
            loops: Number of loops (0 for infinite)
            position: Position to display
            background: Background color for transparent GIFs
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"GIF not found: {path}")
            
        gif = Image.open(path)
        frames = []
        
        # Preprocess frames
        for frame in ImageSequence.Iterator(gif):
            duration = frame.info.get('duration', 100) / 1000.0
            
            # Convert frame
            if self.is_color:
                if frame.mode in ('RGBA', 'P'):
                    # Handle transparency
                    bg = Image.new('RGB', frame.size, background or (0, 0, 0))
                    bg.paste(frame, mask=frame.split()[-1] if frame.mode == 'RGBA' else None)
                    frame = bg
                else:
                    frame = frame.convert('RGB')
            else:
                frame = frame.convert('1', dither=Image.FLOYDSTEINBERG)
                
            # Resize to fit if needed
            if frame.size != (self.width, self.height):
                frame = frame.resize((self.width, self.height), Image.LANCZOS)
                
            frames.append((frame, duration))
            
        # Play animation
        loop_count = 0
        while loops == 0 or loop_count < loops:
            for frame, duration in frames:
                self.buffer.paste(frame, position)
                self.show()
                time.sleep(max(0.016, duration))  # Cap at ~60fps
            loop_count += 1
            
    # ==================== Loading Animations ====================
    
    def start_loading(self, style: LoadingStyle = LoadingStyle.SPINNER,
                      text: str = "Loading...", 
                      color=None,
                      speed: float = 0.1):
        """
        Start non-blocking loading animation
        
        Args:
            style: Animation style
            text: Text to display
            color: Animation color
            speed: Animation speed (seconds per frame)
        """
        self.stop_loading()
        self._loading_stop.clear()
        self._loading_active = True
        
        color = self._parse_color(color) if color else Color.WHITE
        
        def animate():
            frame = 0
            while not self._loading_stop.is_set():
                self.clear()
                
                if style == LoadingStyle.SPINNER:
                    self._draw_spinner(frame, color)
                elif style == LoadingStyle.BAR:
                    self._draw_bar(frame, color)
                elif style == LoadingStyle.DOTS:
                    self._draw_dots(frame, color)
                elif style == LoadingStyle.PULSE:
                    self._draw_pulse(frame, color)
                elif style == LoadingStyle.BOUNCE:
                    self._draw_bounce(frame, color)
                    
                if text:
                    self.centered_text(text, y=self.height - 20, 
                                     color=color, font_size=10)
                
                self.show()
                frame += 1
                time.sleep(speed)
                
            self._loading_active = False
            
        self._loading_thread = threading.Thread(target=animate)
        self._loading_thread.daemon = True
        self._loading_thread.start()
        
    def stop_loading(self):
        """Stop loading animation"""
        if self._loading_active:
            self._loading_stop.set()
            if self._loading_thread:
                self._loading_thread.join(timeout=1.0)
            self._loading_active = False
            
    def _draw_spinner(self, frame: int, color):
        """Draw spinner animation"""
        center = (self.width // 2, self.height // 2 - 10)
        radius = 10
        angle = (frame * 30) % 360
        
        for i in range(8):
            a = math.radians(angle + i * 45)
            x = center[0] + int(radius * math.cos(a))
            y = center[1] + int(radius * math.sin(a))
            size = 2 if i == 0 else 1
            self.circle((x, y), size, fill=color)
            
    def _draw_bar(self, frame: int, color):
        """Draw progress bar animation"""
        bar_width = self.width - 20
        bar_height = 8
        x = 10
        y = self.height // 2 - 10
        
        # Background
        self.rectangle((x, y, x + bar_width, y + bar_height), 
                      outline=color, width=1)
        
        # Progress
        progress = (frame * 5) % (bar_width + 20)
        fill_width = min(progress, bar_width)
        self.rectangle((x + 2, y + 2, x + fill_width - 2, y + bar_height - 2),
                      fill=color)
        
    def _draw_dots(self, frame: int, color):
        """Draw bouncing dots"""
        center_x = self.width // 2
        center_y = self.height // 2 - 10
        
        for i in range(3):
            offset = (frame + i * 4) % 16
            y_offset = abs(8 - offset) - 4
            x = center_x + (i - 1) * 12
            y = center_y + y_offset
            self.circle((x, y), 3, fill=color)
            
    def _draw_pulse(self, frame: int, color):
        """Draw pulsing circle"""
        center = (self.width // 2, self.height // 2 - 10)
        max_radius = 15
        pulse = (frame % 20) / 20.0
        radius = int(max_radius * pulse)
        
        if radius > 0:
            self.circle(center, radius, outline=color)
        self.circle(center, 3, fill=color)
        
    def _draw_bounce(self, frame: int, color):
        """Draw bouncing ball"""
        x = (frame * 4) % (self.width - 10)
        y = self.height // 2 - 10
        
        # Bounce physics
        bounce_height = 10
        phase = (frame % 20) / 20.0 * math.pi
        y_offset = int(abs(math.sin(phase)) * bounce_height)
        
        self.circle((x, y - y_offset), 4, fill=color)
        
    # ==================== Utility Methods ====================
    
    def scroll_text(self, text: str, y: int = 0, 
                    color=None, font_size: int = 12, 
                    speed: float = 0.05, direction: str = "left"):
        """
        Scroll text horizontally
        
        Args:
            text: Text to scroll
            y: Y position
            color: Text color
            font_size: Font size
            speed: Scroll speed (seconds per pixel)
            direction: "left" or "right"
        """
        color = self._parse_color(color)
        font = self._get_font(font_size)
        
        # Get text width
        bbox = self.draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        
        # Scroll
        if direction == "left":
            start_x = self.width
            end_x = -text_width
            step = -1
        else:
            start_x = -text_width
            end_x = self.width
            step = 1
            
        for x in range(start_x, end_x, step):
            self.clear()
            self.draw.text((x, y), text, font=font, fill=color)
            self.show()
            time.sleep(speed)
            
    def progress_bar(self, percent: float, x: int = 10, y: int = None,
                     width: int = None, height: int = 8,
                     outline_color=None, fill_color=None, bg_color=None):
        """
        Draw a progress bar
        
        Args:
            percent: 0.0 to 100.0
            x: X position
            y: Y position (centered if None)
            width: Bar width (full width minus margins if None)
            height: Bar height
            outline_color: Border color
            fill_color: Fill color
            bg_color: Background color
        """
        if y is None:
            y = (self.height - height) // 2
        if width is None:
            width = self.width - (x * 2)
            
        outline_color = self._parse_color(outline_color or Color.WHITE)
        fill_color = self._parse_color(fill_color or Color.WHITE)
        bg_color = self._parse_color(bg_color) if bg_color else None
        
        # Background
        if bg_color:
            self.rectangle((x, y, x + width, y + height), fill=bg_color)
            
        # Border
        self.rectangle((x, y, x + width, y + height), outline=outline_color)
        
        # Fill
        fill_width = int((width - 4) * (percent / 100.0))
        if fill_width > 0:
            self.rectangle((x + 2, y + 2, x + 2 + fill_width, y + height - 2),
                          fill=fill_color)
                          
    def draw_grid(self, spacing: int = 10, color=None):
        """Draw a grid pattern"""
        color = self._parse_color(color or Color.WHITE)
        
        for x in range(0, self.width, spacing):
            self.line((x, 0), (x, self.height), color)
        for y in range(0, self.height, spacing):
            self.line((0, y), (self.width, y), color)
            
    def screenshot(self, filename: str = "screenshot.png"):
        """Save current buffer to file"""
        self.buffer.save(filename)
        
    def __enter__(self):
        """Context manager entry"""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()


# ==================== Convenience Functions ====================

def create_ssd1306(bus=1, address=0x3C, **kwargs):
    """Create SSD1306 monochrome display (128x64)"""
    return PiOLED(
        display_type=DisplayType.SSD1306,
        interface="i2c",
        port=bus,
        address=address,
        **kwargs
    )

def create_ssd1331(dc=24, rst=25, **kwargs):
    """Create SSD1331 color display (96x64)"""
    return PiOLED(
        display_type=DisplayType.SSD1331,
        interface="spi",
        gpio_dc=dc,
        gpio_rst=rst,
        **kwargs
    )

def create_sh1106(bus=1, address=0x3C, **kwargs):
    """Create SH1106 monochrome display (128x64)"""
    return PiOLED(
        display_type=DisplayType.SH1106,
        interface="i2c",
        port=bus,
        address=address,
        **kwargs
    )


# ==================== Demo ====================

if __name__ == "__main__":
    print("PiOLED Demo")
    print("=" * 40)
    
    # Create display (change this based on your hardware)
    # For SSD1306 I2C:
    display = create_ssd1306()
    
    # For SSD1331 SPI (Color):
    # display = create_ssd1331()
    
    try:
        # Demo 1: Basic shapes with color support
        print("Demo 1: Shapes & Colors")
        display.clear()
        
        if display.is_color:
            # Color demo
            display.rectangle((0, 0, 95, 63), fill=Color.BLUE)
            display.circle((48, 32), 20, fill=Color.RED, outline=Color.YELLOW)
            display.text("COLOR!", (25, 28), color=Color.WHITE, font_size=14)
        else:
            # Monochrome demo
            display.rectangle((10, 10, 118, 54), outline=Color.WHITE, width=2)
            display.circle((64, 32), 15, outline=Color.WHITE)
            display.line((20, 20), (108, 44), Color.WHITE)
            display.line((20, 44), (108, 20), Color.WHITE)
            
        display.show()
        time.sleep(2)
        
        # Demo 2: Text features
        print("Demo 2: Text Features")
        display.clear()
        display.text("PiOLED Library", (10, 5), font_size=16)
        display.text("Line 1\nLine 2\nLine 3", (10, 25), font_size=12)
        display.show()
        time.sleep(2)
        
        # Demo 3: Loading animations
        print("Demo 3: Loading Animations (5 seconds each)")
        
        for style in LoadingStyle:
            print(f"  Showing {style.value}...")
            display.start_loading(style, text=f"{style.value}...", speed=0.05)
            time.sleep(3)
            display.stop_loading()
            
        # Demo 4: Progress bar
        print("Demo 4: Progress Bar")
        for i in range(101):
            display.clear()
            display.text("Installing...", (35, 10), font_size=12)
            display.progress_bar(i, y=30, width=100)
            display.centered_text(f"{i}%", y=45, font_size=10)
            display.show()
            time.sleep(0.02)
            
        # Demo 5: Scrolling text
        print("Demo 5: Scrolling Text")
        display.scroll_text("This is a scrolling text demo! ", 
                          y=20, speed=0.02)
        
        # Demo 6: Image display (if images exist)
        print("Demo 6: Image Display")
        test_images = ["test.png", "test.jpg", "test.bmp"]
        for img in test_images:
            if os.path.exists(img):
                display.clear()
                display.image(img)
                display.show()
                time.sleep(2)
                
        # Demo 7: GIF (if exists)
        print("Demo 7: GIF Animation")
        if os.path.exists("animation.gif"):
            display.gif("animation.gif", loops=2)
            
        print("Demo complete!")
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        display.cleanup()
        print("Display cleaned up")