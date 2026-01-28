######################################################################
#  Patched buttons.py for desktop emulator
#
#  Original SeedSigner buttons.py modified to use virtualGPIO
#  Emulator by: @EnteroPositivo (Twitter, Gmail, GitHub)
#  Source: https://github.com/enteropositivo/seedsigner-emulator
#
#  Adapted for Cardano SeedSigner project
######################################################################

from typing import List
from seedsigner.emulator.virtualGPIO import GPIO
import time

from seedsigner.models.singleton import Singleton


class HardwareButtons(Singleton):

    KEY_UP_PIN = 6
    KEY_DOWN_PIN = 19
    KEY_LEFT_PIN = 5
    KEY_RIGHT_PIN = 26
    KEY_PRESS_PIN = 13

    KEY1_PIN = 21
    KEY2_PIN = 20
    KEY3_PIN = 16

    @classmethod
    def get_instance(cls):
        # This is the only way to access the one and only instance
        if cls._instance is None:
            cls._instance = cls.__new__(cls)

            # Init GPIO
            GPIO.setmode(GPIO.BOARD)
            GPIO.setup(HardwareButtons.KEY_UP_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(HardwareButtons.KEY_DOWN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(HardwareButtons.KEY_LEFT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(HardwareButtons.KEY_RIGHT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(HardwareButtons.KEY_PRESS_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(HardwareButtons.KEY1_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(HardwareButtons.KEY2_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(HardwareButtons.KEY3_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

            cls._instance.GPIO = GPIO
            cls._instance.override_ind = False

            cls._instance.add_events([
                HardwareButtonsConstants.KEY_UP,
                HardwareButtonsConstants.KEY_DOWN,
                HardwareButtonsConstants.KEY_PRESS,
                HardwareButtonsConstants.KEY_LEFT,
                HardwareButtonsConstants.KEY_RIGHT,
                HardwareButtonsConstants.KEY1,
                HardwareButtonsConstants.KEY2,
                HardwareButtonsConstants.KEY3
            ])

            # Track state over time so we can apply input delays/ignores as needed
            cls._instance.cur_input = None
            cls._instance.cur_input_started = None
            cls._instance.last_input_time = int(time.time() * 1000)
            cls._instance.first_repeat_threshold = 225
            cls._instance.next_repeat_threshold = 250

        return cls._instance

    def wait_for(self, keys=[], check_release=True, release_keys=[]) -> int:
        from seedsigner.controller import Controller
        controller = Controller.get_instance()

        if not release_keys:
            release_keys = keys
        self.override_ind = False

        while True:
            cur_time = int(time.time() * 1000)
            if cur_time - self.last_input_time > controller.screensaver_activation_ms and not controller.is_screensaver_running:
                controller.start_screensaver()
                self.update_last_input_time()
                time.sleep(self.next_repeat_threshold / 1000.0)
                continue

            for key in keys:
                if not check_release or ((check_release and key in release_keys and HardwareButtonsConstants.release_lock) or check_release and key not in release_keys):
                    if self.GPIO.input(key) == GPIO.LOW or self.override_ind:
                        HardwareButtonsConstants.release_lock = False
                        if self.override_ind:
                            self.override_ind = False
                            return HardwareButtonsConstants.OVERRIDE

                        if self.cur_input != key:
                            self.cur_input = key
                            self.cur_input_started = int(time.time() * 1000)
                            self.last_input_time = self.cur_input_started
                            return key
                        else:
                            if cur_time - self.last_input_time > self.next_repeat_threshold:
                                self.cur_input_started = cur_time
                                self.last_input_time = cur_time
                                return key
                            elif cur_time - self.cur_input_started > self.first_repeat_threshold:
                                self.last_input_time = cur_time
                                return key

            time.sleep(0.01)

    def update_last_input_time(self):
        self.last_input_time = int(time.time() * 1000)

    def add_events(self, keys=[]):
        for key in keys:
            GPIO.add_event_detect(0, 0, callback=HardwareButtons.rising_callback)

    @staticmethod
    def rising_callback(channel):
        HardwareButtonsConstants.release_lock = True

    def trigger_override(self, force_release=False) -> bool:
        if force_release:
            HardwareButtonsConstants.release_lock = True
        if not self.override_ind:
            self.override_ind = True
            return True
        return False

    def force_release(self) -> bool:
        HardwareButtonsConstants.release_lock = True
        return True

    def check_for_low(self, key: int = None, keys: List[int] = None) -> bool:
        if key:
            keys = [key]
        for key in keys:
            if self.GPIO.input(key) == self.GPIO.LOW:
                self.update_last_input_time()
                return True
        return False

    def has_any_input(self) -> bool:
        for key in HardwareButtonsConstants.ALL_KEYS:
            if self.GPIO.input(key) == GPIO.LOW:
                return True
        return False


class HardwareButtonsConstants:
    KEY_UP = 6
    KEY_DOWN = 19
    KEY_LEFT = 5
    KEY_RIGHT = 26
    KEY_PRESS = 13

    KEY1 = 21
    KEY2 = 20
    KEY3 = 16

    OVERRIDE = 1000

    ALL_KEYS = [
        KEY_UP,
        KEY_DOWN,
        KEY_LEFT,
        KEY_RIGHT,
        KEY_PRESS,
        KEY1,
        KEY2,
        KEY3,
    ]

    KEYS__LEFT_RIGHT_UP_DOWN = [KEY_LEFT, KEY_RIGHT, KEY_UP, KEY_DOWN]
    KEYS__ANYCLICK = [KEY_PRESS, KEY1, KEY2, KEY3]

    release_lock = True
