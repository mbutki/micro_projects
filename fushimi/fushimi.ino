#include <FastLED.h>

#define LED_PIN     0          // ✅ Your chosen GPIO pin
#define NUM_LEDS    3
#define LED_TYPE    WS2812B
#define COLOR_ORDER GRB
#define BRIGHTNESS  255

CRGB leds[NUM_LEDS];

// Per-LED state
uint8_t heat[NUM_LEDS];           // Current "heat" (0-255)
uint8_t targetHeat[NUM_LEDS];     // Where we’re heading next
unsigned long lastUpdate[NUM_LEDS];

void setup() {
  FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, NUM_LEDS);
  FastLED.setBrightness(BRIGHTNESS);

  // Initialize each LED with random values
  for (int i = 0; i < NUM_LEDS; i++) {
    heat[i] = random(180, 255);
    targetHeat[i] = random(160, 255);
    lastUpdate[i] = millis();
  }
}

void loop() {
  unsigned long now = millis();

  for (int i = 0; i < NUM_LEDS; i++) {
    // Every 100–300 ms, choose a new target "heat"
    if (now - lastUpdate[i] > random(100, 300)) {
      targetHeat[i] = random(160, 255);
      lastUpdate[i] = now;
    }

    // Smooth transition to target
    if (heat[i] < targetHeat[i]) {
      heat[i]++;
    } else if (heat[i] > targetHeat[i]) {
      heat[i]--;
    }

    leds[i] = MyHeatColor(heat[i]);
  }

  FastLED.show();
  delay(30);
}

CRGB MyHeatColor(uint8_t temperature) {
  // Slightly scale red to be strong, but not overpowering
  uint8_t r = scale8(temperature, 240);  // Max out around 240

  // Strongly limit green so we get more red/orange
  uint8_t g = scale8(temperature, 80);   // Lower green for orange tint

  // Add natural flicker: slight randomness to both
  r = qsub8(r, random8(0, 20));          // Randomly dim red a bit
  g = qsub8(g, random8(0, 40));          // Randomly dim green more

  return CRGB(r, g, 0);  // Blue stays off for realistic flame
}
