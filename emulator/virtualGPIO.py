######################################################################
#  virtualGPIO allows programming with the same GPIO code as always
#  to test your code on a desktop environment
#
#  Original author: @EnteroPositivo (Twitter, Gmail, GitHub)
#  Source: https://github.com/enteropositivo/seedsigner-emulator
#
#  Code adapted from: https://roderickvella.wordpress.com/2016/06/28/raspberry-pi-gpio-emulator/
#
#  Adapted for Cardano SeedSigner project
######################################################################

import time

dictionaryPins = {}
raisedPin = ""


class GPIO:
    # Constants
    LOW = 0
    HIGH = 1
    OUT = 2
    IN = 3
    PUD_OFF = 4
    PUD_DOWN = 5
    PUD_UP = 6
    BCM = 7
    BOARD = 101

    SLEEP_TIME_S = 0.1
    SLEEP_TIME_L = 1.5

    risecallback = None

    # GPIO LIBRARY Functions
    @staticmethod
    def setmode(mode):
        time.sleep(GPIO.SLEEP_TIME_L)

    @staticmethod
    def setwarnings(flag):
        pass

    @staticmethod
    def setup(channel, state, initial=-1, pull_up_down=-1):
        global dictionaryPins

        # Check if channel is already setup
        if str(channel) in dictionaryPins:
            raise Exception('GPIO is already setup')

        if state == GPIO.OUT:
            # GPIO is set as output, default OUT 0
            objTemp = PIN("OUT")
            if initial == GPIO.HIGH:
                objTemp.Out = "1"
            dictionaryPins[str(channel)] = objTemp

        elif state == GPIO.IN:
            # Set input
            objTemp = PIN("IN")
            if pull_up_down == -1:
                objTemp.pull_up_down = "PUD_DOWN"  # by default pud_down
                objTemp.In = "0"
            elif pull_up_down == GPIO.PUD_DOWN:
                objTemp.pull_up_down = "PUD_DOWN"
                objTemp.In = "0"
            elif pull_up_down == GPIO.PUD_UP:
                objTemp.pull_up_down = "PUD_UP"
                objTemp.In = "1"

            dictionaryPins[str(channel)] = objTemp

    @staticmethod
    def output(channel, outmode):
        global dictionaryPins
        channel = str(channel)

        if channel not in dictionaryPins:
            raise Exception('GPIO must be setup before used')
        else:
            objPin = dictionaryPins[channel]
            if objPin.SetMode == "IN":
                raise Exception('GPIO must be setup as OUT')

        if outmode != GPIO.LOW and outmode != GPIO.HIGH:
            raise Exception('Output must be set to HIGH/LOW')

        objPin = dictionaryPins[channel]
        if outmode == GPIO.LOW:
            objPin.Out = "0"
        elif outmode == GPIO.HIGH:
            objPin.Out = "1"

    @staticmethod
    def input(channel):
        global dictionaryPins, raisedPin

        channel = str(channel)

        if channel not in dictionaryPins:
            raise Exception('GPIO must be setup before used')
        else:
            objPin = dictionaryPins[channel]
            if objPin.SetMode == "OUT":
                raise Exception('GPIO must be setup as IN')

        if channel == raisedPin:
            raisedPin = ""
            return GPIO.LOW
        else:
            return GPIO.HIGH

    @staticmethod
    def cleanup():
        pass

    @staticmethod
    def add_event_detect(channel, edge, callback):
        GPIO.risecallback = callback

    @staticmethod
    def set_input(gpioID, state):
        global raisedPin

        if state == GPIO.HIGH:
            raisedPin = str(gpioID)
            if GPIO.risecallback:
                GPIO.risecallback(gpioID)
        else:
            raisedPin = ""


class PIN:
    SetMode = "None"  # IN/OUT/NONE
    Out = "0"
    pull_up_down = "PUD_OFF"  # PUD_UP/PUD_DOWN/PUD_OFF
    In = "1"

    def __init__(self, SetMode):
        self.SetMode = SetMode
        self.Out = "0"
