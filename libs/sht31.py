# sht31.py
class SHT31:
    def __init__(self, i2c, addr=0x44):
        self.i2c = i2c
        self.addr = addr

    def get_temp_humi(self):
        return (25.0, 40.0)
