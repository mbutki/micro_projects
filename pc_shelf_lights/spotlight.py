import machine
import neopixel
import time
import random

# ====== CONFIGURATION ======
NUM_LEDS = 68
PIN = 0  # GPIO0
np = neopixel.NeoPixel(machine.Pin(PIN), NUM_LEDS, bpp=4)  # RGBW strip

ROWS = 4
COLS = 17
BLOCK_SIZE = 3            # LEDs per unit block
MAX_BRIGHTNESS = 255      # Max white-channel brightness
INITIAL_BRIGHTNESS = 0    # Starting brightness for fade-in
FADE_IN_RATE = 1
FADE_OUT_RATE = 1
BLOCK_DELAY = 0.05        # Seconds per update
MAX_ON_TIME = 2.0         # Seconds block stays on
MAX_OFF_TIME = 2.0        # Seconds block stays off
MAX_INITIAL_DELAY = 1.0   # Random desync delay at startup

# ====== OPTIONAL YELLOW TINT ======
USE_YELLOW_TINT = True    # Set False for pure white
YELLOW_TINT = 0.5         # 0.0 = no tint, 1.0 = full yellow

# ====== CREATE BLOCK UNITS ======
def create_units():
    units = []
    for row in range(ROWS):
        col = 0
        while col < COLS:
            remaining = COLS - col
            if remaining > BLOCK_SIZE:
                unit_size = BLOCK_SIZE
            else:
                unit_size = remaining
            # Handle leftover case
            if remaining == 1 and units:
                units[-1].extend([col])  # Merge single leftover into last block
                break
            units.append([(row, c) for c in range(col, col + unit_size)])
            col += unit_size
    return units

# ====== SERPENTINE MAPPING ======
def get_led_index(row, col):
    return row * COLS + (col if row % 2 == 0 else (COLS - 1 - col))

# ====== BLOCK CLASS ======
class Block:
    def __init__(self, coords):
        self.coords = coords
        self.brightness = INITIAL_BRIGHTNESS
        self.on = False
        self.timer = random.uniform(0, MAX_INITIAL_DELAY)  # random startup delay
        self.delay = self.timer
        self.waiting_startup = True

    def update(self):
        if self.waiting_startup:
            self.timer -= BLOCK_DELAY
            if self.timer <= 0:
                self.waiting_startup = False
                self.timer = random.uniform(MAX_OFF_TIME * 0.5, MAX_OFF_TIME)
            return

        self.timer -= BLOCK_DELAY
        if self.timer <= 0:
            self.on = not self.on
            if self.on:
                self.timer = random.uniform(MAX_ON_TIME * 0.5, MAX_ON_TIME)
            else:
                self.timer = random.uniform(MAX_OFF_TIME * 0.5, MAX_OFF_TIME)

        if self.on and self.brightness < MAX_BRIGHTNESS:
            self.brightness = min(MAX_BRIGHTNESS, self.brightness + FADE_IN_RATE)
        elif not self.on and self.brightness > 0:
            self.brightness = max(0, self.brightness - FADE_OUT_RATE)

    def draw(self):
        for r, c in self.coords:
            idx = get_led_index(r, c)
            if USE_YELLOW_TINT:
                r_val = int(self.brightness * YELLOW_TINT)
                g_val = int(self.brightness * YELLOW_TINT * 0.8)
                np[idx] = (r_val, g_val, 0, self.brightness)
            else:
                np[idx] = (0, 0, 0, self.brightness)

def run():
    blocks = [Block(coords) for coords in create_units()]

    while True:
        for block in blocks:
            block.update()
        for block in blocks:
            block.draw()
        np.write()
        time.sleep(BLOCK_DELAY)
