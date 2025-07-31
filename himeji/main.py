import time
import machine
import neopixel
import urandom

# --- Configuration ---
LED_PIN = 0
NUM_PIXELS = 30
MOVE_SPEED = 0.02     # Torch movement speed (adjust slower/faster here)
FALLOFF = 2.0         # How far the torch glow spreads
BRIGHTNESS = 1.0      # Overall brightness scaling

np = neopixel.NeoPixel(machine.Pin(LED_PIN), NUM_PIXELS)

def hsv_to_rgb(h, s, v):
    i = int(h * 6)
    f = h * 6 - i
    i %= 6
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    if i == 0: r, g, b = v, t, p
    elif i == 1: r, g, b = q, v, p
    elif i == 2: r, g, b = p, v, t
    elif i == 3: r, g, b = p, q, v
    elif i == 4: r, g, b = t, p, v
    else:       r, g, b = v, p, q
    return int(r * 255), int(g * 255), int(b * 255)

def translate(value, leftMin, leftMax, rightMin, rightMax):
    spanLeft = leftMax - leftMin
    spanRight = rightMax - rightMin
    valueScaled = float(value - leftMin) / float(spanLeft)
    return rightMin + (valueScaled * spanRight)

def rr(min_val, max_val):
    return urandom.getrandbits(16) % (max_val - min_val) + min_val

class SmoothTorch:
    hRange = [30, 40, 360]
    sRange = [99, 100, 100]
    vRange = [60, 100, 100]

    def __init__(self, pos):
        self.pos = pos
        self.color = (255, 100, 20)

    def update_color(self):
        h = self._gen_val(self.hRange)
        s = self._gen_val(self.sRange)
        v = self._gen_val(self.vRange)
        self.color = hsv_to_rgb(h, s, v)

    def _gen_val(self, valRange):
        val = rr(valRange[0], valRange[1])
        return translate(val, 0, valRange[2], 0, 1)

    def draw(self, buf):
        center = self.pos
        self.update_color()
        for i in range(NUM_PIXELS):
            dist = abs(i - center)
            fade = max(0.0, 1.0 - (dist / FALLOFF))
            fade = fade ** 2
            r = int(self.color[0] * fade * BRIGHTNESS)
            g = int(self.color[1] * fade * BRIGHTNESS)
            b = int(self.color[2] * fade * BRIGHTNESS)
            # Additive blend with clipping
            buf[i][0] = min(255, buf[i][0] + r)
            buf[i][1] = min(255, buf[i][1] + g)
            buf[i][2] = min(255, buf[i][2] + b)

    def walk(self):
        self.pos += MOVE_SPEED
        if self.pos >= NUM_PIXELS:
            self.pos -= NUM_PIXELS

def main():
    # Torch A starts at a random position
    torch_a = SmoothTorch(rr(0, NUM_PIXELS))

    # Helper to generate random distance between 1/3 and 2/3 strip length
    def new_distance():
        return translate(rr(0, 100), 0, 100, NUM_PIXELS // 3, 2 * NUM_PIXELS // 3)

    dist = new_distance()
    torch_b = SmoothTorch((torch_a.pos + dist) % NUM_PIXELS)

    while True:
        # Prepare blank buffer to blend both torches
        buf = [[0, 0, 0] for _ in range(NUM_PIXELS)]

        # Draw both torches onto buffer
        torch_a.draw(buf)
        torch_b.draw(buf)

        # Output blended colors to LEDs
        for i in range(NUM_PIXELS):
            np[i] = tuple(buf[i])
        np.write()

        # Move torches
        torch_a.walk()
        torch_b.walk()

        # Reset torch_b distance after torch_a wraps around
        if torch_a.pos < MOVE_SPEED:
            dist = new_distance()
            torch_b.pos = (torch_a.pos + dist) % NUM_PIXELS

        time.sleep(0.03)

main()
