import machine
import neopixel
import time
import math

# ====== CONFIGURATION ======
NUM_LEDS = 68
PIN = 0  # GPIO0
np = neopixel.NeoPixel(machine.Pin(PIN), NUM_LEDS, bpp=4)  # RGBW strip

# ====== UTILITY FUNCTIONS ======
def hsv_to_rgb(h, s, v):
    """Convert HSV (0.0–1.0) to RGB (0–255)."""
    i = int(h * 6)
    f = h * 6 - i
    p = int(255 * v * (1 - s))
    q = int(255 * v * (1 - f * s))
    t = int(255 * v * (1 - (1 - f) * s))
    v = int(255 * v)
    i %= 6
    if i == 0: return (v, t, p)
    if i == 1: return (q, v, p)
    if i == 2: return (p, v, t)
    if i == 3: return (p, q, v)
    if i == 4: return (t, p, v)
    if i == 5: return (v, p, q)

def clear_strip():
    for i in range(NUM_LEDS):
        np[i] = (0, 0, 0, 0)
    np.write()

# ====== ANIMATION FUNCTIONS ======

def rainbow_single(delay=0.01):
    """Classic rainbow spin across the whole strip."""
    pos = 0
    while True:
        for i in range(NUM_LEDS):
            hue = ((i / NUM_LEDS) + pos) % 1.0
            r, g, b = hsv_to_rgb(hue, 1.0, 1.0)
            np.fill([0, 0, 0, 0])
            np[i] = (r, g, b, 0)
            np.write()
            time.sleep(delay)
            pos = (pos + 0.01) % 1.0

def rainbow_cycle(delay=0.01):
    """Classic rainbow spin across the whole strip."""
    pos = 0
    while True:
        for i in range(NUM_LEDS):
            hue = ((i / NUM_LEDS) + pos) % 1.0
            r, g, b = hsv_to_rgb(hue, 1.0, 1.0)
            np[i] = (r, g, b, 0)
        np.write()
        time.sleep(delay)
        pos = (pos + 0.01) % 1.0

def rainbow_comet(delay=0.01, tail=8):
    """Rainbow-colored comet with trailing tail."""
    pos = 0
    while True:
        for i in range(NUM_LEDS):
            distance = (i - pos) % NUM_LEDS
            brightness = max(0.0, 1 - (distance / tail))
            hue = (i / NUM_LEDS) % 1.0
            r, g, b = hsv_to_rgb(hue, 1.0, brightness)
            np[i] = (r, g, b, 0)
        np.write()
        time.sleep(delay)
        pos = (pos + 1) % NUM_LEDS

def rainbow_waves(delay=0.01, speed=0.02):
    """Flowing rainbow waves using sine modulation."""
    t = 0.0
    while True:
        for i in range(NUM_LEDS):
            hue = (math.sin(i * 0.3 + t) + 1) / 2  # wave pattern
            r, g, b = hsv_to_rgb(hue, 1.0, 1.0)
            np[i] = (r, g, b, 0)
        np.write()
        time.sleep(delay)
        t += speed

def single_color(r, g, b, w):
    while True:
        np.fill([r, g, b, w])
        np.write()
        time.sleep(10000)
        
def max_power():
    while True:
        np.fill([255, 255, 255, 255])
        np.write()
        time.sleep(10000)
