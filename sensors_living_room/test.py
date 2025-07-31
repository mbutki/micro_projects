from machine import I2C, Pin

i2c0 = I2C(0, scl=Pin(17), sda=Pin(16))
i2c1 = I2C(1, scl=Pin(15), sda=Pin(14))

print("I2C0 Scan:", i2c0.scan())  # Check for BMP280 here?
print("I2C1 Scan:", i2c1.scan())
