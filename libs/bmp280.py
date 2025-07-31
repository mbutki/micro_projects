# bmp280.py
class BMP280:
    def __init__(self, i2c, addr=0x77):
        self.i2c = i2c
        self.addr = addr

    def get_temp(self):
        return 24.3

    def get_press(self):
        return 101325
