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
from device.dfplayermini import Mp3Player

from menu.menu import *
import helpers

DFPLAYER_SERIALPORT = 2

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
mp3player = Mp3Player(DFPLAYER_SERIALPORT,17,16)
#d = dht.DHT22(DHT_PIN)
display_tm1637 = tm1637.TM1637(PIN_TM1637_CLK, PIN_TM1637_DATA)
np = NeoPixel(NEO_PIXEL_PIN, NEO_PIXEL_COUNT)   # create NeoPixel driver on GPIO33 for N pixels
neo = neoring.NeoRing(np, NEO_PIXEL_COUNT)

tim0 = Timer(0)
tim1 = Timer(1)
menu = Menu()

AppState = helpers.enum(INIT=0, CLOCK=1, MENU=3, ALARM=4)
NeoState = helpers.enum(OFF=0, TIME=1, LIGHT=2)
AlarmMode = helpers.enum(NONE=0, MUSIC=1, LIGHT=2, MUSIC_AND_LIGHT=3)
Button_LUT = {
    PUSHBUTTON_SELECT_PIN: ButtonCode.ESCAPE,
    PUSHBUTTON_LEFT_PIN: ButtonCode.LEFT,
    PUSHBUTTON_RIGHT_PIN: ButtonCode.RIGHT,
    PUSHBUTTON_UP_PIN: ButtonCode.UP,
    PUSHBUTTON_DOWN_PIN: ButtonCode.DOWN
}

app_context = {
    "state": AppState.INIT,
    "neo": NeoState.TIME,
    "level": 20,
    "edit_time": 0,
    "blink": {
        "enable": False,
        "value0": 0,
        "blink0": False,
        "value1": 0,
        "blink1": False,
        "counter": 0,
    },
    "alarm": [
        {"hour": 21, "min": 28, "duration": 3, "mode": AlarmMode.LIGHT, "countdown": 0},
        {"hour": 7, "min":0, "duration": 30, "mode": AlarmMode.LIGHT, "countdown": 0}
        ]
    }

def menu_button_action(button, button_event):
    res = menu.button_event(button, button_event)
    print("res(menu.button_event): ",  res)
        
    if res == MenuState.IN_MENU:
        app_context["blink"]["enable"] = False
        print("In menu: ", menu.menu_text())
        menu_text = menu.menu_text()
        if menu_text:
            print("Menu text : ", menu_text)
            display_tm1637.show(menu_text)
    elif res == MenuState.IN_CALLBACK:
        print("In callback")
    elif res == MenuState.EXIT:
        print("exit menu")
        return AppState.CLOCK
    
    return AppState.MENU

def clock_button_action(button_code, event):
    print(app_context["state"])
    if app_context["state"] == AppState.CLOCK:
        print("state = clock")
        if event == Button.LONGPRESS:
            if button_code == ButtonCode.LEFT:
                # Start/stop the MP3 player
                if mp3player.is_playing():
                    mp3player.stop()
                else:
                    #mp3player.set_playback_mode(Mp3Player.PLAYBACK_MODE_RANDOM)
                    mp3player.play_random()
                    time.sleep(0.5)
                    mp3player.set_volume(3)
                    
            elif button_code == ButtonCode.RIGHT:
                # Toggle the light on/off
                if app_context["neo"] != NeoState.LIGHT:
                    neo.light((32,32,32), app_context["level"])
                    app_context["neo"] = NeoState.LIGHT
                else:
                    app_context["neo"] = NeoState.TIME
                    update_time()
                    
        elif event == Button.RELEASED:
           # Not displaying menu.
           print("Button released")
           if button_code == ButtonCode.RIGHT:
               print("Button right")
               if mp3player.is_playing():
                    mp3player.play_next()    
               #elif app_context["neo"] != NeoState.LIGHT:
               #    neo.light((32,32,32), app_context["level"])
               #    app_context["neo"] = NeoState.LIGHT
               #else:
               #    app_context["neo"] = NeoState.TIME
               #    update_time()
           elif button_code == ButtonCode.LEFT:
               print("Button left")
               mp3player.play_previous()
           elif button_code == ButtonCode.UP:
               mp3player.volume_up()
           elif button_code == ButtonCode.DOWN:
               mp3player.volume_down()
#           elif pin == PUSHBUTTON_UP_PIN:
#             app_context["level"] = app_context["level"] + 5
#             if app_context["level"] > 100:
#                 app_context["level"] = 100
#             display_tm1637.number(app_context["level"])
#             neo.light((64,64,64), app_context["level"])
#         elif pin == PUSHBUTTON_DOWN_PIN:
#             app_context["level"] = app_context["level"] - 5
#             if app_context["level"] < 10:
#                 app_context["level"] = 5
#             display_tm1637.number(app_context["level"])
#             neo.light((64,64,64), app_context["level"])
        

def button_action(button, event):
    print("Button : ", button)
    print("Event  : ", event)
    button_code = Button_LUT[button]
    print("button_code :", button_code)
    
    if event not in [Button.LONGPRESS, Button.LONGPRESS_REPEAT, Button.LONGPRESS_RELEASED, Button.RELEASED]:
        return
    
    if app_context["state"] == AppState.MENU:
        app_context["state"] = menu_button_action(button_code, event)
        if app_context["state"] == AppState.CLOCK:
            update_time()        
    else:
        if button_code == ButtonCode.ESCAPE:
            print("button = escape")
            app_context["state"] = AppState.MENU
            menu.reset()
            display_tm1637.scroll("menu", 160)
            if menu.menu_text() is not None:
                display_tm1637.show(menu.menu_text())
        else:
            print("forward to clock_button_action")
            clock_button_action(button_code, event)

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
        print("Checking alarm : ", i)
        check_alarm(alarm, timestamp[3], timestamp[4])

    if has_active_alarm():
        app_context["state"] = AppState.ALARM
    else:
        app_context["neo"] = NeoState.TIME
    
    # Check if we are allowed to display the time in the TM1637
    if app_context["state"] != AppState.MENU: 
        display_tm1637.numbers(timestamp[3], timestamp[4])
        
    # Check if we are allowed to display the time on the Neo Ring
    if app_context["neo"] == NeoState.TIME:
        neo.show_time(timestamp[3], timestamp[4])


def menu_edit_time(button, event):
    """
    Edit the time

    button: left/right/up/down/escape
    event:  pressed/released/longpress
    """
    is_modified = False
    #print("Edit time")
    #print("Button : ", button) 
    
    timestamp = list(external_rtc.get_time())
    print(timestamp)
    if app_context["edit_time"] is None or app_context["edit_time"] == 0:
        time_index = 3	# index to hour
        time_max = 23
    else:
        time_index = 4	# index to minutes
        time_max = 59
        
    if button == None:
        app_context["edit_time"] = 0
    elif button == ButtonCode.UP:
        if timestamp[time_index] < time_max:
            timestamp[time_index] = timestamp[time_index] + 1
        else:
            timestamp[time_index] = 0
        is_modified = True
    elif button == ButtonCode.DOWN:
        if timestamp[time_index] > 0:
            timestamp[time_index] = timestamp[time_index] - 1
        else:
            timestamp[time_index] = time_max
        is_modified = True
    elif button == ButtonCode.RIGHT:
        app_context["edit_time"] = 1
    elif button == ButtonCode.LEFT:
        app_context["edit_time"] = 0
        
    # Update the RTC when modified
    if is_modified:
        print("Adjusting external RTC")
        external_rtc.set_time(timestamp)
        internal_rtc.datetime(timestamp)
        
    # Display the time setting
    if event == Button.RELEASED:
        # Blink the number that is edited.
        app_context["blink"]["enable"] = True
        app_context["blink"]["value0"] = timestamp[3]
        app_context["blink"]["value1"] = timestamp[4]
        app_context["blink"]["blink0"] = (app_context["edit_time"] == 0)
        app_context["blink"]["blink1"] = (app_context["edit_time"] == 1)
        blink_display()
    elif event in [Button.LONGPRESS, Button.LONGPRESS_REPEAT, Button.LONGPRESS_REPEAT]:
        # Do not blink when the user is doing a longpress
        app_context["blink"]["enable"] = False
        display_tm1637.numbers(timestamp[3], timestamp[4])
    
    
def blink_display(t=None):
    if app_context["blink"]["enable"] == False:
        return
    # get the values that need to be displayed (or not).
    num0 = app_context["blink"]["value0"]
    num1 = app_context["blink"]["value1"]
    #print("num0: ", num0)
    #print("num1: ", num1)
    counter = app_context["blink"]["counter"]
    counter = counter + 1
    app_context["blink"]["counter"] = counter
    
    do_blink = (counter & 1) == 1
    if do_blink:
        if app_context["blink"]["blink0"]:
            num0 = None
        if app_context["blink"]["blink1"]:
            num1 = None
    
    if num0 is None:
        str_num0 = "  "
    else:
        str_num0 = '{:0>2d}'.format(num0)
        
    if num1 is None:
        str_num1 = "  "
    else:
        str_num1 = '{:0>2d}'.format(num1)
        
    text = '{0}{1}'.format(str_num0, str_num1)
    #print("Blink text: ", text)
    display_tm1637.show(text, colon=not do_blink)
    
        
    
def menu_edit_alarm_time(alarm, button, event):
    """

    alarm: id/index of alarm
    button: left/right/up/down/escape
    event:  pressed/released/longpress
    """
    print("Edit alarm time")
    print("Alarm : ", alarm)
    print("Button : ", button)

def menu_edit_alarm_duration(alarm, button, event):
    """

    alarm: id/index of alarm
    button: left/right/up/down/escape
    event:  pressed/released/longpress
    """
    print("Edit alarm duration")
    print(app_context["alarm"][alarm])
    print("Alarm : ", alarm)
    print("Button : ", button)
    if button == ButtonCode.UP:
        app_context["alarm"][alarm]["duration"] += 1
    elif button == ButtonCode.DOWN:
        app_context["alarm"][alarm]["duration"] -= 1
    
    if app_context["alarm"][alarm]["duration"] < 0:
        app_context["alarm"][alarm]["duration"]=0
    if app_context["alarm"][alarm]["duration"] > 59:
        app_context["alarm"][alarm]["duration"] = 59
        
    display_tm1637.number(app_context["alarm"][alarm]["duration"] )

def create_menu():
    menu.add_item(["musc"], menu_edit_time)
    menu.add_item(["lght"], menu_edit_time)
    menu.add_item(["time"], menu_edit_time)
    menu.add_item(["alm1", "time"], menu_edit_alarm_time, {"alarm": 0, })
    menu.add_item(["alm1", "days"], menu_edit_alarm_duration, {"alarm": 0, })
    menu.add_item(["alm1", "dura"], menu_edit_alarm_duration, {"alarm": 0, })
    menu.add_item(["alm2", "time"], menu_edit_alarm_time, {"alarm": 1, })
    menu.add_item(["alm2", "days"], menu_edit_alarm_duration, {"alarm": 1, })
    menu.add_item(["alm2", "dura"], menu_edit_alarm_duration, {"alarm": 1, })
    

def main():
    button_list = [
        Button(PUSHBUTTON_LEFT_PIN, int(ButtonCode.LEFT), callback = button_action, internal_pulldown=True),
        Button(PUSHBUTTON_RIGHT_PIN, int(ButtonCode.RIGHT), callback = button_action, internal_pulldown=True),
        Button(PUSHBUTTON_DOWN_PIN, int(ButtonCode.DOWN), callback = button_action, internal_pulldown=True),
        Button(PUSHBUTTON_UP_PIN, int(ButtonCode.UP), callback = button_action, internal_pulldown=True),
        Button(PUSHBUTTON_SELECT_PIN, int(ButtonCode.ESCAPE), callback = button_action, internal_pulldown=True),
    ]
    create_menu()
    
    neo.off()
    rtc_init()
    tim0.init(period=60000, mode=Timer.PERIODIC, callback=update_time)
    tim1.init(period=750, mode=Timer.PERIODIC, callback=blink_display)
    update_time()
    time.sleep(3)
    app_context["state"] = AppState.CLOCK
    while True:
        # Check buttons for events.
        for i in button_list:
            i.update(250)
            
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