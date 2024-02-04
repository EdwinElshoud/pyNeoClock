from machine import SoftI2C, Pin

from neopixel import NeoPixel
import time
from machine import RTC
from device import tm1637
from device import ds3231
from device import neoring
import uasyncio as asyncio
from machine import Timer

#import dht

PIN_TM1637_CLK = Pin(15)
PIN_TM1637_DATA = Pin(4)
NEO_PIXEL_COUNT = 40
NEO_PIXEL_PIN = Pin(33, Pin.OUT)
DHT_PIN = Pin(19)
I2C_SCL_PIN = Pin(22, Pin.OPEN_DRAIN, value=1)
I2C_SDA_PIN = Pin(21, Pin.OPEN_DRAIN, value=1)

i2c = SoftI2C(scl=I2C_SCL_PIN, sda=I2C_SDA_PIN)

external_rtc = ds3231.DS3231(i2c)
internal_rtc = RTC()

#d = dht.DHT22(DHT_PIN)
display_tm1637 = tm1637.TM1637(PIN_TM1637_CLK, PIN_TM1637_DATA)
np = NeoPixel(NEO_PIXEL_PIN, NEO_PIXEL_COUNT)   # create NeoPixel driver on GPIO33 for N pixels
neo = neoring.NeoRing(np, NEO_PIXEL_COUNT)

tim0 = Timer(0)

def update_time():
    timestamp = internal_rtc.datetime()
    display_tm1637.numbers(timestamp[3], timestamp[4])


def main():
    neo.off()
    print(f"Int. RTC : {internal_rtc.datetime()}")
    timestamp = external_rtc.get_time()
    print(f"Ext.RTC : {timestamp}")
    if timestamp[0] == 2000:
        external_rtc.set_time((2024, 1, 22, 10, 55, 0, 1, 1))
    display_tm1637.scroll("Goedemorgen", 200)
    tim0.init(period=60000, mode=Timer.PERIODIC, callback=update_time)
    update_time()
    time.sleep(3)

    for level in range(0, 100):
        #display_tm1637.number(level)
        neo.light((64,16,32), float(level)/100.0)
        time.sleep(0.5)
        
    neo.off()        
        
if __name__ == "__main__":
    main()