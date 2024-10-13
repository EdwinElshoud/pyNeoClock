from machine import SoftI2C, Pin, reset
import os
import ugit
import network
import settings
import json

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

from menu.menu2 import *
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

DAY_LUT = ("mon ", "tues", "wed ", "thur", "fri ", "sat ", "sun ")

app_context = {
    "state": AppState.INIT,
    "neo": NeoState.TIME,
    "level": 20,
    "edit_time": {					# for editing time [hh:mm]
        "time": [0, 0],
        "index": 0,
        "is_modified": False,
    },
    "edit_value": {					# for editing integer settings
        "value": 0,
        "is_modified": False,
    },
    "edit_bool": {					# for editing boolean settings
        "state": False,
        "is_modified": False,
    },
    "edit_day": {					# for editing weekdays
        "day": False,
        "is_modified": False,
    },
    "blink": {
        "enable": False,
        "value0": 0,
        "blink0": False,
        "value1": 0,
        "blink1": False,
        "counter": 0,
    },
    "alarm": [
        {"enabled": True,
         "hour": 13,
         "min": 5,
         "duration": 3,
         "mode": AlarmMode.MUSIC_AND_LIGHT,
         "volume": 7,
         "countdown": 0,
         "days" : [True, True, True, True, True, True, True],
         },
        {"enabled": True,
         "hour": 13,
         "min": 15,
         "duration": 5,
         "mode": AlarmMode.MUSIC_AND_LIGHT,
         "volume": 3,
         "countdown": 0,
         "days" : [True, True, True, True, True, True, True],
         },
        ]
    }
def save_settings():
    # Save the dictionary to a JSON file
    with open('settings.json', 'w') as json_file:
        json.dump(app_context["alarm"], json_file)

def load_settings():
    try:
        # Load the dictionary from the JSON file
        with open('settings.json') as json_file:
            app_context["alarm"] = json.load(json_file)
    except:
        pass
    

# --------------------------------------------------------------------
def menu_button_action(button, button_event):
    res = menu.button_event(button, button_event)
    print("res(menu.button_event): ",  res)
        
    if res == MenuState.IN_MENU:
        #app_context["blink"]["enable"] = False
        print("In menu: ", menu.menu_text())
        menu_text = menu.menu_text()
        if menu_text:
            print("Menu text : ", menu_text)
            if len(menu_text) < 4: 
                # Clear the contents before writing new text to prevent old characters to stay visible.
                display_tm1637.show("    ")
            display_tm1637.show(menu_text)
    elif res == MenuState.IN_CALLBACK:
        print("In callback")
    elif res == MenuState.EXIT:
        print("exit menu")
        save_settings()
        return AppState.CLOCK
    
    return AppState.MENU

# --------------------------------------------------------------------
def clock_button_action(button_code, event):
    print(app_context["state"])
    if app_context["state"] == AppState.ALARM:
        # Stop alarm(s) and go back to clock mode
        if mp3player.is_playing():
            mp3player.stop()
        app_context["alarm"][0]["duration"] = 0
        app_context["alarm"][1]["duration"] = 0
        app_context["state"] = AppState.CLOCK
    elif app_context["state"] == AppState.CLOCK:
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
                if mp3player.is_playing():
                    mp3player.play_previous()
            elif button_code == ButtonCode.UP:
                if mp3player.is_playing():
                    mp3player.volume_up()
                else:
                    # Todo: display alarm 1 time for short period (or only do when pressed???) 
                    pass
            elif button_code == ButtonCode.DOWN:
                if mp3player.is_playing():
                    mp3player.volume_down()
                else:
                    # Todo: display alarm 2 time for short period (or only do when pressed???)
                    pass
                   
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
        

# --------------------------------------------------------------------
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
            # menu.reset()
            menu.start()
            #display_tm1637.scroll("menu", 160)
            if menu.menu_text() is not None:
                display_tm1637.show(menu.menu_text())
        else:
            print("forward to clock_button_action")
            clock_button_action(button_code, event)

# --------------------------------------------------------------------
def rtc_init():
    """
    Initialize and synchronize the internal RTC with the external RTC.
    
    Reading time from:	Tuple:
    Internal RTC 		(year, month, day, weekday, hours, minutes, seconds, subseconds)
    External RTC 		(YY, MM, DD, hh, mm, ss, wday - 1, 0)

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

# --------------------------------------------------------------------
def check_alarm(alarm, hour, min):
    """
    alarm - alarm entry from app_context
    hour - current hour
    min - current minute
    """
    if alarm["countdown"] > 0:
        alarm["countdown"] = alarm["countdown"] - 1
    elif alarm["enabled"] and alarm["hour"] == hour and alarm["min"] == min:
        # Activate the alarm
        alarm["countdown"] = alarm["duration"]
        if alarm["mode"] in [AlarmMode.LIGHT, AlarmMode.MUSIC_AND_LIGHT]:
            neo.light((64,64,64), 20)
            app_context["neo"] = NeoState.LIGHT
            
        if alarm["mode"] in [AlarmMode.MUSIC, AlarmMode.MUSIC_AND_LIGHT]:
            mp3player.reset()
            time.sleep(2)
            mp3player.play_random()
            time.sleep(0.5)
            mp3player.set_volume(alarm["volume"])
            
# --------------------------------------------------------------------
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


# --------------------------------------------------------------------
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
    elif app_context["state"] == AppState.ALARM:
        # No alarm is active and state is still ALARM... go back to CLOCK
        app_context["neo"] = NeoState.TIME
        app_context["state"] = AppState.CLOCK
        mp3player.stop()
    else:
        app_context["neo"] = NeoState.TIME
    
    # Check if we are allowed to display the time in the TM1637
    if app_context["state"] != AppState.MENU: 
        display_tm1637.numbers(timestamp[3], timestamp[4])
        
    # Check if we are allowed to display the time on the Neo Ring
    if app_context["neo"] == NeoState.TIME:
        neo.show_time(timestamp[3], timestamp[4])


# --------------------------------------------------------------------
def menu_edit_time_start(target):
    if target == "system":
        # Prepare to edit the system time
        timestamp = list(external_rtc.get_time())
        #print(timestamp)
        app_context["edit_time"]["time"][0] = timestamp[3]	# hours
        app_context["edit_time"]["time"][1] = timestamp[4]	# minutes
    elif target == "alarm_1":
        # Prepare to edit alarm 1 time
        app_context["edit_time"]["time"][0] = app_context["alarm"][0]["hour"]	# hours
        app_context["edit_time"]["time"][1] = app_context["alarm"][0]["min"] # minutes
    elif target == "alarm_2":
        # Prepare to edit alarm 2 time
        app_context["edit_time"]["time"][0] = app_context["alarm"][1]["hour"] # hours
        app_context["edit_time"]["time"][1] = app_context["alarm"][1]["min"] # minutes
        
    app_context["edit_time"]["index"] = 0
    app_context["edit_time"]["is_modified"] = False
    
    # Show a blinking time on the display
    app_context["blink"]["value0"] = app_context["edit_time"]["time"][0] #timestamp[3]
    app_context["blink"]["value1"] = app_context["edit_time"]["time"][1]  #timestamp[4]
    app_context["blink"]["blink0"] = (app_context["edit_time"]["index"] == 0)
    app_context["blink"]["blink1"] = (app_context["edit_time"]["index"] == 1)
    app_context["blink"]["counter"] = 0
    app_context["blink"]["enable"] = True
    blink_display()


# --------------------------------------------------------------------
def menu_edit_time_store(target):
    if target == "system":
        # Store the edit time into the RTC
        timestamp = list(external_rtc.get_time())
        #print(timestamp)
        timestamp[3] = app_context["edit_time"]["time"][0]	# hours
        timestamp[4] = app_context["edit_time"]["time"][1]	# minutes
        print("Adjusting external RTC")
        external_rtc.set_time(timestamp)
        internal_rtc.datetime(timestamp)
        
    elif target == "alarm_1":
        # Store the edit time into alarm 1
        app_context["alarm"][0]["hour"] = app_context["edit_time"]["time"][0]
        app_context["alarm"][0]["min"] = app_context["edit_time"]["time"][1]
    elif target == "alarm_2":
        # Store the edit time into alarm 2
        app_context["alarm"][1]["hour"] = app_context["edit_time"]["time"][0]
        app_context["alarm"][1]["min"] = app_context["edit_time"]["time"][1]
    
    app_context["blink"]["enable"] = False
        

# --------------------------------------------------------------------
def menu_edit_time(target, button, event):
    """
    Edit the time

    button: left/right/up/down/escape
    event:  pressed/released/longpress
    """
    is_modified = False
    index = app_context["edit_time"]["index"]
    
    if index == 0:
        time_max = 23	# When editing hours
    else:
        time_max = 59	# When editing minutes
    
    edit_value = app_context["edit_time"]["time"][index]
    if button == ButtonCode.UP:
        if edit_value < time_max:
            edit_value = edit_value + 1
        else:
            edit_value = 0
        app_context["edit_time"]["is_modified"] = True
        app_context["edit_time"]["time"][index] = edit_value

    elif button == ButtonCode.DOWN:
        if edit_value > 0:
            edit_value = edit_value - 1
        else:
            edit_value = time_max
        app_context["edit_time"]["is_modified"] = True
        app_context["edit_time"]["time"][index] = edit_value

    elif button == ButtonCode.RIGHT:
        app_context["edit_time"]["index"] = 1

    elif button == ButtonCode.LEFT:
        app_context["edit_time"]["index"] = 0
                
    # Display the time setting
    if event == Button.RELEASED:
        # Blink the number that is edited.
        app_context["blink"]["enable"] = True
        app_context["blink"]["value0"] = app_context["edit_time"]["time"][0] #timestamp[3]
        app_context["blink"]["value1"] = app_context["edit_time"]["time"][1]  #timestamp[4]
        app_context["blink"]["blink0"] = (app_context["edit_time"]["index"] == 0)
        app_context["blink"]["blink1"] = (app_context["edit_time"]["index"] == 1)
        blink_display()
    elif event in [Button.LONGPRESS, Button.LONGPRESS_REPEAT, Button.LONGPRESS_REPEAT]:
        # Do not blink when the user is doing a longpress
        app_context["blink"]["enable"] = False
        display_tm1637.numbers(app_context["edit_time"]["time"][0], app_context["edit_time"]["time"][1])
    
    
# --------------------------------------------------------------------
def blink_display(t=None):
    #print(f"blink={app_context["blink"]["enable"]}")
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
    
# --------------------------------------------------------------------
def menu_edit_value_start(target, name, min_value, max_value):
    if target == "alarm_1":
        app_context["edit_value"]["value"] = app_context["alarm"][0][name]
        
    elif target == "alarm_2":
        app_context["edit_value"]["value"] = app_context["alarm"][1][name]
        
    else:
        print(f"ERROR[menu_edit_value_start]::Unknown target name")
        return
    
    # call menu_edit_value to force display of value
    menu_edit_value(target, name, min_value, max_value, button=None, event=None)
    

# --------------------------------------------------------------------
def menu_edit_value_store(target, name, min_value, max_value):
    if target == "alarm_1":
        app_context["alarm"][0][name] = app_context["edit_value"]["value"]
    elif target == "alarm_2":
        app_context["alarm"][1][name] = app_context["edit_value"]["value"]
    else:
        print(f"ERROR[menu_edit_value_start]::Unknown target name")


# --------------------------------------------------------------------
def menu_edit_value(target, name, min_value, max_value, button, event):
    """
    alarm: id/index of alarm
    button: left/right/up/down/escape
    event:  pressed/released/longpress
    """
    edit_value = app_context["edit_value"]["value"]
    print("Edit value")
    print(edit_value)
    if button == ButtonCode.UP and edit_value < max_value:
        edit_value += 1
    elif button == ButtonCode.DOWN and edit_value > min_value:
        edit_value -= 1
    
    if edit_value < min_value:
        edit_value = min_value
    if edit_value > max_value:
        edit_value = max_value
    
    app_context["edit_value"]["value"] = edit_value   
    display_tm1637.number(edit_value)
    
    
# --------------------------------------------------------------------
def menu_edit_bool_start(target, name):
    alarm = None
    if target == "alarm_1":
        alarm = 0
    elif target == "alarm_2":
        alarm = 1
    else:
        return	# Error condition
    
    if "days" in name:
        day = int(name.split(":")[1])
        print(f"alarm={alarm}, day={day}")
        app_context["edit_bool"]["state"] = app_context["alarm"][alarm]["days"][day]
    else:
        app_context["edit_bool"]["state"] = app_context["alarm"][alarm][name]
        
    menu_edit_bool(target, name, button=None, event=None)
    
    
# --------------------------------------------------------------------
def menu_edit_bool_store(target, name):
    alarm = None
    if target == "alarm_1":
        alarm = 0
    elif target == "alarm_2":
        alarm = 1
    else:
        return	# Error condition

    if "days" in name:
        day = int(name.split(":")[1])
        app_context["alarm"][alarm]["days"][day] = app_context["edit_bool"]["state"]
    else:
        app_context["alarm"][alarm][name] = app_context["edit_bool"]["state"]
    

# --------------------------------------------------------------------
def menu_edit_bool(target, name, button, event):
    edit_value = app_context["edit_bool"]["state"]
    
    if button in [ButtonCode.UP, ButtonCode.DOWN]:
        edit_value = not edit_value

    app_context["edit_bool"]["state"] = edit_value
    if edit_value:
        display_tm1637.show("on  ")
    else:
        display_tm1637.show("off ")
        

    
# --------------------------------------------------------------------
def menu_edit_day_start(target):
    if target == "system":
        timestamp = list(external_rtc.get_time())
        app_context["edit_day"]["day"] = timestamp[6]	# weekday

    menu_edit_day(target, button=None, event=None)
    
    
# --------------------------------------------------------------------
def menu_edit_day_store(target):
    if target == "system":
        timestamp = list(external_rtc.get_time())
        timestamp[6] = app_context["edit_day"]["day"]
        external_rtc.set_time(timestamp)

# --------------------------------------------------------------------
def menu_edit_day(target, button, event):
    edit_value = app_context["edit_day"]["day"]
    # Direction is swapped: DOWN button => mon -> sun (which is increading in number) 
    if button == ButtonCode.DOWN and edit_value < 6:
        edit_value += 1
    elif button == ButtonCode.UP and edit_value > 0:
        edit_value -= 1

    app_context["edit_day"]["day"] = edit_value
    print(f"Weekday = {edit_value} --> {DAY_LUT[edit_value]}")
    display_tm1637.show(DAY_LUT[edit_value])

# --------------------------------------------------------------------
def menu_action_start(target):
    if target == "system":
        display_tm1637.show("Go--")
        #timestamp = list(external_rtc.get_time())
        #app_context["edit_day"]["day"] = timestamp[6]	# weekday

    menu_action(target, button=None, event=None)
 

# --------------------------------------------------------------------
def menu_action(target, button, event):
    #edit_value = app_context["edit_day"]["day"]
    # Direction is swapped: DOWN button => mon -> sun (which is increading in number) 
    if button == ButtonCode.RIGHT:
        with open(settings.UPDATE_FILE, 'w') as f:
            f.write("do:update")
        reset()

    #app_context["edit_day"]["day"] = edit_value
    #print(f"Weekday = {edit_value} --> {DAY_LUT[edit_value]}")
    display_tm1637.show("Go--")

# --------------------------------------------------------------------
def create_time_menu_item(path, kwargs):
    menu.add_menu_item(path,
                       on_enter=menu_edit_time_start,
                       on_process=menu_edit_time,
                       on_exit=menu_edit_time_store,
                       kwargs=kwargs)

# --------------------------------------------------------------------
def create_value_menu_item(path, kwargs):
    menu.add_menu_item(path,
                       on_enter=menu_edit_value_start,
                       on_process=menu_edit_value,
                       on_exit=menu_edit_value_store,
                       kwargs=kwargs)

# --------------------------------------------------------------------
def create_bool_menu_item(path, kwargs):
    menu.add_menu_item(path,
                       on_enter=menu_edit_bool_start,
                       on_process=menu_edit_bool,
                       on_exit=menu_edit_bool_store,
                       kwargs=kwargs)

def create_day_menu_item(path, kwargs):
    menu.add_menu_item(path,
                       on_enter=menu_edit_day_start,
                       on_process=menu_edit_day,
                       on_exit=menu_edit_day_store,
                       kwargs=kwargs)

def create_action_menu_item(path, kwargs):
    menu.add_menu_item(path,
                       on_enter=menu_action_start,
                       on_process=menu_action,
                       on_exit=None,
                       kwargs=kwargs)

# --------------------------------------------------------------------
def create_menu():
    menu.add_menu_item(["musc"], on_process=menu_edit_time)
    menu.add_menu_item(["lght"], on_process=menu_edit_time)
    create_time_menu_item(["syst", "time"], kwargs={"target": "system", })
    create_day_menu_item(["syst", "day"], kwargs={"target": "system", })
    create_action_menu_item(["syst", "updt"], kwargs={"target": "system",})
    # Alarm 1
    create_bool_menu_item(["alm1", "enbl"],
                          kwargs={"target": "alarm_1", "name": "enabled"})
    create_time_menu_item(["alm1", "time"], kwargs={"target": "alarm_1", })
    create_bool_menu_item(["alm1", "days", "mo"], kwargs={"target": "alarm_1", "name": "days:0"})
    create_bool_menu_item(["alm1", "days", "tu"], kwargs={"target": "alarm_1", "name": "days:1"})
    create_bool_menu_item(["alm1", "days", "we"], kwargs={"target": "alarm_1", "name": "days:2"})
    create_bool_menu_item(["alm1", "days", "th"], kwargs={"target": "alarm_1", "name": "days:3"})
    create_bool_menu_item(["alm1", "days", "fr"], kwargs={"target": "alarm_1", "name": "days:4"})
    create_bool_menu_item(["alm1", "days", "sa"], kwargs={"target": "alarm_1", "name": "days:5"})
    create_bool_menu_item(["alm1", "days", "su"], kwargs={"target": "alarm_1", "name": "days:6"})
    create_value_menu_item(["alm1", "dura"],
                           kwargs={"target": "alarm_1",
                                   "name": "duration",
                                   "min_value": 0,
                                   "max_value": 59, })
    create_value_menu_item(["alm1", "vol"],
                           kwargs={"target": "alarm_1",
                                   "name": "volume",
                                   "min_value": 0,
                                   "max_value": 7, })
    # Alarm 2
    create_time_menu_item(["alm2", "time"], kwargs={"target": "alarm_2", })
    create_bool_menu_item(["alm2", "days", "mo"], kwargs={"target": "alarm_2", "name": "days:0"})
    create_bool_menu_item(["alm2", "days", "tu"], kwargs={"target": "alarm_2", "name": "days:1"})
    create_bool_menu_item(["alm2", "days", "we"], kwargs={"target": "alarm_2", "name": "days:2"})
    create_bool_menu_item(["alm2", "days", "th"], kwargs={"target": "alarm_2", "name": "days:3"})
    create_bool_menu_item(["alm2", "days", "fr"], kwargs={"target": "alarm_2", "name": "days:4"})
    create_bool_menu_item(["alm2", "days", "sa"], kwargs={"target": "alarm_2", "name": "days:5"})
    create_bool_menu_item(["alm2", "days", "su"], kwargs={"target": "alarm_2", "name": "days:6"})
    
    
    create_value_menu_item(["alm2", "dura"],
                           kwargs={"target": "alarm_2",
                                   "name": "duration",
                                   "min_value": 0,
                                   "max_value": 59,})
    create_value_menu_item(["alm2", "vol"],
                           kwargs={"target": "alarm_2",
                                   "name": "volume",
                                   "min_value": 0,
                                   "max_value": 7, })


def check_update():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(settings.CONFIG_SSID, settings.CONFIG_PASS)
    counter = 5
    while not wlan.isconnected() and counter > 0:
        print("waiting on connection...")
        time.sleep(1)
        counter -= 1
        
    new_version = None
    try:
        new_version = ugit.find_new_version()
        if not new_version:
            print("At latest version")
    except:
        print("Failed to get commit version")
    wlan.active(False)
    return new_version

    
# --------------------------------------------------------------------
# Main entry point
# --------------------------------------------------------------------
def main():
    new_version = check_update()
    load_settings()
    
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
    if new_version is not None:
        print("new version found")
        display_tm1637.show("UPDT")
        for i in range(1,5):
            neo.light(color=[64,0,0], brightness=0.5)
            time.sleep(0.25)
            neo.light(color=[0,64,0], brightness=0.5)
            time.sleep(0.25)
            neo.light(color=[0,0,64], brightness=0.5)
            time.sleep(0.25)
    neo.off()
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
    #time.sleep(1)
    #print("start main application!")
    main()