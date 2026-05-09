import machine, neopixel, time, urandom

# ==== CONFIG ====
LED_PIN = 0              # GPIO pin
NUM_LEDS = 3
BRIGHTNESS = 255         # scale 0–255

# WS2812 / NeoPixel object (RGB)
np = neopixel.NeoPixel(machine.Pin(LED_PIN), NUM_LEDS)

# ==== STATE ====
heat = [0] * NUM_LEDS
target_heat = [0] * NUM_LEDS
last_update = [0] * NUM_LEDS


# --- helpers ---
def random8(low=0, high=255):
    """Return random int in [low, high)."""
    return urandom.getrandbits(8) % (high - low) + low

def scale8(val, scale):
    """Scale 0–255 by scale (0–255)."""
    return (val * scale) >> 8

def qsub8(val, sub):
    """Subtract but clamp to 0."""
    return max(0, val - sub)

def qadd8(val, add):
    """Add but clamp to 255."""
    return min(255, val + add)

def millis():
    """Current time in ms."""
    return time.ticks_ms()

def MyHeatColor(temperature):
    # Slightly scale red strong
    r = scale8(temperature, 240)
    # Strongly limit green
    g = scale8(temperature, 80)
    # Add natural flicker
    r = qsub8(r, random8(0, 20))
    g = qsub8(g, random8(0, 40))
    # Optional: add faint blue for realism
    b = 0
    return (r, g, b)


# ==== SETUP ====
for i in range(NUM_LEDS):
    heat[i] = random8(180, 255)
    target_heat[i] = random8(160, 255)
    last_update[i] = millis()


# ==== LOOP ====
while True:
    now = millis()

    for i in range(NUM_LEDS):
        # Every 100–300 ms, choose a new target heat
        if time.ticks_diff(now, last_update[i]) > random8(100, 300):
            target_heat[i] = random8(160, 255)
            last_update[i] = now

        # Smooth transition toward target
        if heat[i] < target_heat[i]:
            heat[i] = qadd8(heat[i], 1)
        elif heat[i] > target_heat[i]:
            heat[i] = qsub8(heat[i], 1)

        # Apply brightness scaling
        r, g, b = MyHeatColor(heat[i])
        np[i] = (r * BRIGHTNESS // 255,
                 g * BRIGHTNESS // 255,
                 b * BRIGHTNESS // 255)

    np.write()
    time.sleep_ms(30)
