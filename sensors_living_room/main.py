import machine
import time
import network
from umqtt.robust import MQTTClient
from secrets import WIFI_SSID, WIFI_PASSWORD, MQTT_BROKER, MQTT_CLIENT_ID, MQTT_TOPIC
import ujson
from veml7700 import VEML7700
from bmp280 import BMP280
from sht41 import SHT4X
import ntptime
import ucollections

LOCATION = "living_room"
ERROR_TOPIC = 'sensor/error'
VERBOSE = False
SCL = 15
SDA = 14

# I2C sensors
i2c = machine.I2C(1, scl=machine.Pin(SCL), sda=machine.Pin(SDA), freq=10000) # Dropped to 10kHz for stability
veml = VEML7700(i2c=i2c)
bmp = BMP280(i2c, addr=0x77)
sht = SHT4X(i2c=i2c)

# UART PMS5003 setup (pins and baudrate as your hardware)
uart = machine.UART(0, baudrate=9600, tx=machine.Pin(16), rx=machine.Pin(17))

# Sensor sample structure
SensorSample = ucollections.namedtuple('SensorSample', 'lux temp pressure humidity wifi')

SAMPLE_FREQ_HZ = 3           # sensor sample rate per second
PUBLISH_INTERVAL_SEC = 1     # publish every N seconds

SAMPLES_PER_PUBLISH = SAMPLE_FREQ_HZ * PUBLISH_INTERVAL_SEC

samples = []
latest_pm25_raw = None
latest_pm25 = None
client = None

def log_error(error):
    print(f'logged error: {error}')
    payload = {
        "timestamp": time.time(),
        "location": LOCATION,
        "error": error
    }

    try:
        msg = ujson.dumps(payload)
        client.publish(ERROR_TOPIC, msg)
    except Exception as e:
        print("MQTT publish failed:", e)
        
def median(data):
    data = sorted(data)
    n = len(data)
    if n == 0:
        return None
    if n % 2 == 1:
        return data[n // 2]
    else:
        return (data[n//2 -1] + data[n//2]) / 2

def correct_pm25_epa(raw_pm25, humidity):
    """Applies EPA correction for PMS5003 PM2.5 data using local humidity."""
    if raw_pm25 is None or humidity is None:
        return None
    return 0.524 * raw_pm25 - 0.0862 * humidity + 5.75

def pm25_to_aqi(pm25):
    breakpoints = [
        (0.0, 12.0, 0, 50),
        (12.1, 35.4, 51, 100),
        (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200),
        (150.5, 250.4, 201, 300),
        (250.5, 500.4, 301, 500)
    ]
    for c_low, c_high, aqi_low, aqi_high in breakpoints:
        if c_low <= pm25 <= c_high:
            return round(((aqi_high - aqi_low) / (c_high - c_low)) * (pm25 - c_low) + aqi_low)
    return None

def read_pms5003_async():
    """
    Non-blocking read of PMS5003 data from UART.
    Looks for valid 32-byte frames starting with 0x42 0x4D.
    Returns PM2.5 env concentration or None.
    """
    # Clear old data if buffer is too big to avoid stale junk
    if uart.any() > 64:
        uart.read(uart.any())

    buffer = bytearray()

    start_time = time.ticks_ms()
    timeout_ms = 100  # timeout per read attempt (adjustable)

    while time.ticks_diff(time.ticks_ms(), start_time) < timeout_ms:
        if uart.any():
            buffer += uart.read(1)
            # Search for frame header 0x42 0x4D
            if len(buffer) >= 2:
                # Find first header index
                idx = buffer.find(b'\x42\x4D')
                if idx == -1:
                    # No header found, drop first byte
                    buffer = buffer[1:]
                    continue
                # Remove leading bytes before header
                if idx > 0:
                    buffer = buffer[idx:]

                if len(buffer) >= 32:
                    frame = buffer[:32]
                    # Validate frame header
                    if frame[0] == 0x42 and frame[1] == 0x4D:
                        # Calculate checksum
                        checksum = sum(frame[0:30])
                        frame_checksum = frame[30] << 8 | frame[31]
                        if checksum == frame_checksum:
                            # PM2.5 env bytes 12,13 (big endian)
                            pm25_env = (frame[12] << 8) | frame[13]
                            return pm25_env
                        else:
                            log_error("PMS5003 checksum fail")
                    else:
                        log_error("PMS5003 invalid header")
                    # Remove processed frame bytes
                    buffer = buffer[32:]
        else:
            time.sleep_ms(5)
    return None

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    # Disable power management to improve stability
    wlan.config(pm=0xa11140)
    while not wlan.isconnected():
        time.sleep(0.5)
    print("Connected to WiFi:", wlan.ifconfig())

def sync_time():
    try:
        ntptime.settime()
        if VERBOSE:
            print("Time synced from NTP")
    except Exception as e:
        log_error(f'Failed to sync time: {e}')

def reinit_sht4x():
    """Attempts to recover the I2C bus and re-initialize all sensors on the bus."""
    global i2c, sht, veml, bmp
    print("Attempting I2C bus recovery...")
    try:
        # 1. Manual Bus Clear: If a slave is holding SDA low, toggle SCL until it releases.
        # We temporarily treat the pins as standard GPIOs.
        scl_pin = machine.Pin(SCL, machine.Pin.OUT, machine.Pin.PULL_UP)
        sda_pin = machine.Pin(SDA, machine.Pin.IN, machine.Pin.PULL_UP)
        
        # Clock SCL up to 10 times to clear the slave's internal state machine (bus clear)
        for _ in range(10):
            if sda_pin.value() == 1:
                break
            scl_pin.value(0)
            time.sleep_us(20)
            scl_pin.value(1)
            time.sleep_us(20)

        # Let the bus settle
        time.sleep_ms(50)

        # 2. Re-initialize the I2C hardware bus at a lower frequency
        i2c = machine.I2C(1, scl=machine.Pin(SCL), sda=machine.Pin(SDA), freq=10000)

        # 3. Re-instantiate all sensor drivers on this bus
        try:
            i2c.writeto(0x44, b'\x94')  # SHT4x soft reset
            time.sleep_ms(10)
        except:
            pass
        
        # 4. Re-instantiate the sensor driver
        sht = SHT4X(i2c=i2c)
        veml = VEML7700(i2c=i2c)
        bmp = BMP280(i2c, addr=0x77)
        time.sleep_ms(50) # Let it stabilize
        return True
    except Exception as e:
        print(f"I2C re-init failed: {e}")
        return False

def main():
    global client
    
    connect_wifi()
    client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER)
    try:
        client.connect()
        print("Connected to MQTT broker")
    except Exception as e:
        log_error(f'Failed to connect MQTT broker: {e}')

    sync_time()
    last_ntp_sync = time.time()
    ntp_sync_interval = 3600

    next_sample_time = time.ticks_ms()
    sample_interval_ms = 1000 // SAMPLE_FREQ_HZ
    next_publish_time = time.ticks_add(next_sample_time, PUBLISH_INTERVAL_SEC * 1000)

    global latest_pm25_raw
    global latest_pm25

    consecutive_failures = 0
    MAX_FAILURES = 15 # Allow ~5 seconds of retries before resetting

    while True:
        now = time.time()
        if now - last_ntp_sync > ntp_sync_interval:
            sync_time()
            last_ntp_sync = now

        current_ms = time.ticks_ms()

        if time.ticks_diff(current_ms, next_sample_time) >= 0:
            next_sample_time = time.ticks_add(next_sample_time, sample_interval_ms)

            # Read all sensors except PMS5003
            try:
                sht_temp_c, humidity = sht.measurements
                if sht_temp_c is None or humidity is None:
                    raise ValueError(f"Invalid SHT4X values: temp:{sht_temp_c} humid:{humidity}")
                if not (-40 < sht_temp_c < 125):
                    raise ValueError(f"Out-of-range SHT4X values: temp:{sht_temp_c}")
                temp = sht_temp_c * 9 / 5 + 32
                consecutive_failures = 0 # Reset counter on success
            except Exception as e:
                consecutive_failures += 1
                log_error(f'SHT4X Read error ({consecutive_failures}/{MAX_FAILURES}): {e}')
                
                time.sleep_ms(500) # Give transients more time to settle
                
                if consecutive_failures >= MAX_FAILURES:
                    log_error("Max failures reached. Resetting Pico...")
                    time.sleep_ms(1000)
                    machine.reset()
            
                # Attempt soft recovery
                reinit_sht4x()
                temp = None
                humidity = None
                time.sleep_ms(100) # Short breather before next attempt

            try:
                pressure = bmp.pressure
            except:
                pressure = None

            try:
                lux = veml.read_lux()
            except:
                lux = None

            try:
                rssi = network.WLAN(network.STA_IF).status('rssi')
            except:
                rssi = None

            pm25_raw = read_pms5003_async()
            if pm25_raw is not None:
                latest_pm25_raw = pm25_raw
                if humidity is not None:
                    latest_pm25 = correct_pm25_epa(pm25_raw, humidity)
                    if VERBOSE:
                        print("Raw PM2.5:", latest_pm25_raw, "Corrected PM2.5:", latest_pm25)
                    

            # Append sample for median
            samples.append(SensorSample(lux, temp, pressure, humidity, rssi))
            if len(samples) > SAMPLES_PER_PUBLISH:
                samples.pop(0)

        # Publish every PUBLISH_INTERVAL_SEC seconds if we have samples
        if time.ticks_diff(current_ms, next_publish_time) >= 0 and len(samples) > 0:
            next_publish_time = time.ticks_add(next_publish_time, PUBLISH_INTERVAL_SEC * 1000)

            median_lux = median([s.lux for s in samples if s.lux is not None])
            median_temp = median([s.temp for s in samples if s.temp is not None])
            median_pressure = median([s.pressure for s in samples if s.pressure is not None])
            median_humidity = median([s.humidity for s in samples if s.humidity is not None])
            median_wifi = median([s.wifi for s in samples if s.wifi is not None])
            aqi_raw = pm25_to_aqi(latest_pm25_raw) if latest_pm25_raw is not None else None
            aqi = pm25_to_aqi(latest_pm25) if latest_pm25 is not None else None

            payload = {
                "timestamp": time.time(),
                "location": LOCATION,
                "lux": median_lux,
                "temp": median_temp,
                "pressure": median_pressure,
                "humidity": median_humidity,
                "aqi_raw": aqi_raw,
                "aqi": aqi,
                "wifi": median_wifi
            }

            try:
                msg = ujson.dumps(payload)
                if VERBOSE:
                    print("Publishing:", msg)
                client.publish(MQTT_TOPIC, msg)
            except Exception as e:
                log_error(f'MQTT publish failed: {e}')

            samples.clear()

        time.sleep_ms(10)

main()
