import logging
import os
import threading
import time

import Adafruit_BBIO.GPIO as GPIO
import Adafruit_BBIO.PWM as PWM

LOGGER = logging.getLogger(__name__)
ticks = time.time()
i = 0


# To properly clock LCD I had to use exotic microsecond range sleep function
def usleep(x):
    time.sleep(x/100000.0)  # Can go higher, but will eat up whole CPU on that.


class lcd_driver:
    def __init__(self):
        # IOMAP = [RS, CLK(E), B7, B6, B5, B4]
        self.iomap = ["GPIO1_13", "GPIO1_12", "GPIO0_27", "GPIO1_14",
                      "GPIO1_15", "GPIO0_26"]
        # PWMMAP = [R, G, B]
        self.pwmmap = ["P8_34", "P8_45", "P8_46"]
        self.R = "P8_34"
        self.G = "P8_45"
        self.B = "P8_46"

        self.GPIO = GPIO
        for pin in self.iomap:
            self.GPIO.setup(pin, GPIO.OUT)

        self.PWM = PWM
        for pin in self.pwmmap:
            self.PWM.start(pin, 0)

        LOGGER.debug("Setting Up Screen")

    def setup(self):
        LOGGER.debug("Python HD44780 LCD Driver REV 2")

        self.lcdcommand('0011')  # \
        self.lcdcommand('0011')  # | Initialization Sequence
        self.lcdcommand('0011')  # /
        self.lcdcommand('0010')  # 4BIT Mode

        self.lcdcommand('00000001')  # Reset
        self.lcdcommand('00001100')  # Dispaly On

        # Shift Reference
        # 10000000  Moves cursor to first address on the left of LINE 1
        # 11000000  Moves cursor to first address on the left of LINE 2
        # 10010100  Moves cursor to first address on the left of LINE 3
        # 11010100  Moves cursor to first address on the left of LINE 4

        LOGGER.debug("Transferring LCD Control to main loop")
        LOGGER.debug("Process PID: %s", os.getpid())

    # LCD instruction mode
    # For some reason my LCD takes longer to ACK that mode, hence longer delays
    def lcdcommand(self, string):
        self.GPIO.output(self.iomap[1], 1)
        usleep(500)
        self.GPIO.output(self.iomap[0], 0)
        iteration = 0
        for idr in string:
            self.GPIO.output(self.iomap[iteration+2], int(idr))
            iteration = iteration + 1
            if iteration == 4:
                iteration = 0
                usleep(100)
                self.GPIO.output(self.iomap[1], 0)
                usleep(100)
                self.GPIO.output(self.iomap[1], 1)
                usleep(500)
        return

    # LCD Data mode
    def lcdprint(self, string):
        for char in string:
            # Binary character value
            bitmap = bin(ord(char))[2:].zfill(8)
            self.GPIO.output(self.iomap[1], 1)
            usleep(20)
            self.GPIO.output(self.iomap[0], 1)
            iteration = 0
            for idr in bitmap:
                self.GPIO.output(self.iomap[iteration+2], int(idr))
                iteration = iteration + 1
                if iteration == 4:
                    iteration = 0
                    usleep(20)
                    self.GPIO.output(self.iomap[1], 0)
                    usleep(20)
                    self.GPIO.output(self.iomap[1], 1)
                    usleep(20)
        return

    def set_red(self):
        self.PWM.start(self.R, 0)  # R P8_34
        self.PWM.start(self.G, 100)  # G P8_45
        self.PWM.start(self.B, 100)  # B P8_46

    def set_orange(self):
        self.PWM.start(self.R, 0)  # R P8_34
        self.PWM.start(self.G, 50)  # G P8_45
        self.PWM.start(self.B, 100)  # B P8_46

    def set_yellow(self):
        self.PWM.start(self.R, 0)  # R P8_34
        self.PWM.start(self.G, 0)  # G P8_45
        self.PWM.start(self.B, 100)  # B P8_46

    def set_green(self):
        self.PWM.start(self.R, 100)  # R P8_34
        self.PWM.start(self.G, 0)  # G P8_45
        self.PWM.start(self.B, 100)  # B P8_46

    def set_cyan(self):
        self.PWM.start(self.R, 100)  # R P8_34
        self.PWM.start(self.G, 0)  # G P8_45
        self.PWM.start(self.B, 0)  # B P8_46

    def set_blue(self):
        self.PWM.start(self.R, 100)  # R P8_34
        self.PWM.start(self.G, 100)  # G P8_45
        self.PWM.start(self.B, 0)  # B P8_46

    def set_purple(self):
        self.PWM.start(self.R, 50)  # R P8_34
        self.PWM.start(self.G, 100)  # G P8_45
        self.PWM.start(self.B, 0)  # B P8_46

    def set_violet(self):
        self.PWM.start(self.R, 0)  # R P8_34
        self.PWM.start(self.G, 100)  # G P8_45
        self.PWM.start(self.B, 0)  # B P8_46

    def set_black(self):
        self.PWM.start(self.R, 100)  # R P8_34
        self.PWM.start(self.G, 100)  # G P8_45
        self.PWM.start(self.B, 100)  # B P8_46

    def set_gray(self):
        self.PWM.start(self.R, 50)  # R P8_34
        self.PWM.start(self.G, 50)  # G P8_45
        self.PWM.start(self.B, 50)  # B P8_46

    def set_white(self):
        self.PWM.start(self.R, 0)  # R P8_34
        self.PWM.start(self.G, 0)  # G P8_45
        self.PWM.start(self.B, 0)  # B P8_46


class LCDWriter:
    def __init__(self):
        self.lock = threading.Lock()

        self.line1 = ""
        self.line2 = ""

        self.small = 0
        self.large = 0
        self.update_air_time = None

        self.queue_size = 0
        self.update_queue_time = None

        try:
            self.lcd = lcd_driver()
            self.lcd.setup()
        except Exception as e:
            LOGGER.error("Error occurred while setting up LCD screen: %s ", e)
            LOGGER.error("Probably means it is not connected.")
            self.lcd = None

    def display_data(self):
        update_air_time = "" if self.update_air_time is None else \
                          self.update_air_time.strftime("%H:%M")
        update_queue_time = "" if self.update_queue_time is None else \
                            self.update_queue_time.strftime("%H:%M")

        line1 = "{: >5} {: >4} {}".format(self.small,
                                          self.large,
                                          update_air_time)
        line2 = "{: >10} {}".format(self.queue_size, update_queue_time)

        self.display(line1=line1, line2=line2)

    def display(self, line1=None, line2=None):
        with self.lock:
            if line1 is not None:
                self.line1 = line1

            if line2 is not None:
                self.line2 = line2

            LOGGER.debug("Line 1: %s", self.line1)
            LOGGER.debug("Line 2: %s", self.line2)

            if self.lcd is None:
                LOGGER.warning("LCD is not connected")
            else:
                try:
                    self.lcd.lcdcommand('00000001')  # Reset
                    self.lcd.lcdprint(self.line1)
                    self.lcd.lcdcommand('11000000')  # Move cursor down
                    self.lcd.lcdprint(self.line2)
                    self.lcd.lcdcommand('10000000')  # Move cursor to beginning
                except Exception as e:
                    LOGGER.error(
                        "An exception occurred while writing to LCD: %s", e)
