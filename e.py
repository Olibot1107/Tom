if __name__ == "__main__":
    import math
    import random

    oled = OLED()
    try:
        print("Starting futuristic OLED demo...")
        
        width, height = oled.device.width, oled.device.height

        # Parameters for animation
        pulse_radius = 5
        max_radius = 30
        angle = 0
        direction = 1

        for frame in range(200):  # Run 200 frames
            oled.clear()

            # 1️⃣ Draw rotating polygon (like a radar)
            num_points = 6
            polygon_points = []
            for i in range(num_points):
                theta = math.radians(angle + i * (360 / num_points))
                x = int(width/2 + math.cos(theta) * 25)
                y = int(height/2 + math.sin(theta) * 25)
                polygon_points.append((x, y))
            oled.draw_polygon(polygon_points, outline="white")

            # 2️⃣ Draw pulsating circle in the center
            pulse_radius += direction
            if pulse_radius >= max_radius or pulse_radius <= 5:
                direction *= -1
            oled.draw_circle((width//2, height//2), pulse_radius, outline="white")

            # 3️⃣ Draw dynamic arcs around center
            for i in range(0, 360, 60):
                start = (angle + i) % 360
                end = start + 30
                oled.draw_arc((10, 10, width-10, height-10), start, end, fill="white", width=1)

            # 4️⃣ Draw random stars/background points
            for _ in range(5):
                x, y = random.randint(0, width-1), random.randint(0, height-1)
                oled.draw_point((x, y), fill="white")

            # 5️⃣ Draw live text
            oled.draw_text(f"HACKER MODE {frame}", position=(2, height-12), font_size=10)

            oled.show()
            angle += 10  # Rotate polygon and arcs
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("Exiting OLED demo...")
    finally:
        oled.clear()
        oled.close()
