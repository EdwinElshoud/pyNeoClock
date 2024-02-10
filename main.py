from machine import SoftI2C, Pin

from neopixel import NeoPixel
import time
from machine import RTC
from device import tm1637
from device import ds3231
from device import neoring
import uasyncio as asyncio
from machine import Timer
from device.Button import Button

# Workaround for using enums
def enum(**enums: int):
    return type('Enum', (), enums)


PUSHBUTTON_LEFT_PIN = 32
PUSHBUTTON_RIGHT_PIN = 35
PUSHBUTTON_UP_PIN = 25
PUSHBUTTON_DOWN_PIN = 26  
PUSHBUTTON_SELECT_PIN = 27

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
tim1 = Timer(1)
menu={}

AppState = enum(INIT=0, CLOCK=1, MENU=3, ALARM=4)
NeoState = enum(OFF=0, TIME=1, LIGHT=2)
AlarmMode = enum(NONE=0, MUSIC=1, LIGHT=2, MUSIC_AND_LIGHT=3)

app_context = {
    "state": AppState.INIT,
    "neo": NeoState.TIME,
    "level": 20,
    "alarm": [
        {"hour": 21, "min": 28, "duration": 3, "mode": AlarmMode.LIGHT, "countdown": 0},
        {"hour": 7, "min":0, "duration": 30, "mode": AlarmMode.LIGHT, "countdown": 0}
        ]
    }


def button_action(pin, event):
    if event == Button.PRESSED:
        if pin == PUSHBUTTON_SELECT_PIN:
            if app_context["state"] != AppState.MENU:
                app_context["state"] = AppState.MENU
                display_tm1637.scroll("menu", 200)
            else:
                app_context["state"] = AppState.CLOCK
                update_time()
        
    if app_context["state"] == AppState.MENU:
        if pin == PUSHBUTTON_LEFT_PIN:
            external_rtc.set_time((2024, 2, 10, 20, 25, 0, 1, 1))
    elif event == Button.RELEASED:
        # Not displaying menu.
        if pin == PUSHBUTTON_RIGHT_PIN:
            if app_context["neo"] != NeoState.LIGHT:
                neo.light((64,64,64), app_context["level"])
                app_context["neo"] = NeoState.LIGHT
            else:
                app_context["neo"] = NeoState.TIME
                update_time()
        elif pin == PUSHBUTTON_UP_PIN:
            app_context["level"] = app_context["level"] + 5
            if app_context["level"] > 100:
                app_context["level"] = 100
            display_tm1637.number(app_context["level"])
            neo.light((64,64,64), app_context["level"])
        elif pin == PUSHBUTTON_DOWN_PIN:
            app_context["level"] = app_context["level"] - 5
            if app_context["level"] < 10:
                app_context["level"] = 5
            display_tm1637.number(app_context["level"])
            neo.light((64,64,64), app_context["level"])

def rtc_init():
    """
    Initialize and synchronize the internal RTC with the external RTC.
    """
    print(f"Int. RTC : {internal_rtc.datetime()}")
    timestamp = external_rtc.get_time()
    print(f"Ext.RTC : {timestamp}")
    if timestamp[0] == 2000:
        print("Adjusting external RTC")
        external_rtc.set_time((2024, 1, 22, 10, 55, 0, 1, 1))
        
    timestamp = external_rtc.get_time()
    # update internal timestamp
    internal_rtc.datetime(timestamp)


def check_alarm(alarm, hour, min):
    """
    alarm - alarm entry from app_context
    hour - current hour
    min - current minute
    """
    if alarm["countdown"] > 0:
        alarm["countdown"] = alarm["countdown"] - 1
    elif alarm["hour"] == hour and alarm["min"] == min:
        # Activate the alarm
        alarm["countdown"] = alarm["duration"]
        if alarm["mode"] == AlarmMode.LIGHT:
            neo.light((64,64,64), 20)
            app_context["neo"] = NeoState.LIGHT
            
def has_active_alarm():
    """
    Check if one or more alarms are active
    """
    is_active = False
    for i, alarm in enumerate(app_context["alarm"]):
        print(alarm)
        if alarm["countdown"] > 0:
            is_active = True
            
    return is_active

def update_time(t=None):
    print("Update time display")
    timestamp = external_rtc.get_time()
    print(timestamp)
    
    # Check to trigger alarm(s)
    for i, alarm in enumerate(app_context["alarm"]):
        print("Checking alarm %d", i)
        check_alarm(alarm, timestamp[3], timestamp[4])

    if has_active_alarm():
        app_context["state"] = AppState.ALARM
    else:
        app_context["state"] = AppState.CLOCK
        app_context["neo"] = NeoState.TIME
    
    # Check if we are allowed to display the time in the TM1637
    if app_context["state"] != AppState.MENU: 
        display_tm1637.numbers(timestamp[3], timestamp[4])
        
    # Check if we are allowed to display the time on the Neo Ring
    if app_context["neo"] == NeoState.TIME:
        neo.show_time(timestamp[3], timestamp[4])
        

    
#def create_menu():
#    menu["time"]=MenuItem('Tijd', edit_time, id=1, time_obj=None)
#    menu["alarm1"]=MenuItem('Alarm 1', edit_alarm, id=1, alarm_obj=None)

def main():
    button_list = [
        Button(PUSHBUTTON_LEFT_PIN, callback = button_action),
        Button(PUSHBUTTON_RIGHT_PIN, callback = button_action),
        Button(PUSHBUTTON_DOWN_PIN, callback = button_action),
        Button(PUSHBUTTON_UP_PIN, callback = button_action),
        Button(PUSHBUTTON_SELECT_PIN, callback = button_action),
    ]

    neo.off()
    rtc_init()
    tim0.init(period=60000, mode=Timer.PERIODIC, callback=update_time)
    #tim1.init(period=1000, mode=Timer.PERIODIC, callback=update_second)
    update_time()
    time.sleep(3)
    while True:
        # Check buttons for events.
        for i in button_list:
            i.update()
            
        # Handle/process as per application state 
        if app_context["state"] == AppState.INIT:
            pass
        elif app_context["state"] == AppState.MENU:
            pass
        elif app_context["state"] == AppState.CLOCK:
            pass
        
        #for level in range(0, 100):
            #display_tm1637.number(level)
        #    neo.light((64,16,32), float(level)/100.0)
        #    time.sleep(0.5)
        
        #neo.off()
        time.sleep(0.1)
        
        
if __name__ == "__main__":
    main()