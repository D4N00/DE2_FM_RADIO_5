from machine import I2C, Pin
from sh1106 import SH1106_I2C
from array import array
import time
import u8text, font_5x7, font_profont12, font_profont29


def drawMainScreen(oled: SH1106_I2C):
    oled.fill(0)
    # preset_bg
    oled.fill_rect(0, 0, 15, 9, 1)
    u8text.text(oled, font_5x7, 2, 7, "P3", 2)
    # stereo
    u8text.text(oled, font_5x7, 19, 7, "STEREO")

    # volume
    u8text.text(oled, font_5x7, 58, 7, "VOL 12")

    # rssi_1
    oled.fill_rect(110, 6, 3, 2, 1)

    # rssi_2
    oled.fill_rect(115, 4, 3, 4, 1)

    # rssi_3
    oled.fill_rect(120, 2, 3, 6, 1)

    # rssi_4
    oled.fill_rect(125, 0, 3, 8, 1)

    # top_sep
    oled.line(0, 11, 127, 11, 1)

    # freq
    u8text.text(oled, font_profont29, 6, 34, "98.20")

    # unit
    u8text.text(oled, font_profont12, 100, 35, "MHz")

    # scale
    oled.line(4, 47, 123, 47, 1)

    # tick_88
    oled.line(7, 44, 7, 47, 1)

    # tick_90
    oled.line(19, 46, 19, 47, 1)

    # tick_92
    oled.line(30, 44, 30, 47, 1)

    # tick_94
    oled.line(42, 46, 42, 47, 1)

    # tick_96
    oled.line(53, 44, 53, 47, 1)

    # tick_98
    oled.line(65, 46, 65, 47, 1)

    # tick_100
    oled.line(77, 44, 77, 47, 1)

    # tick_102
    oled.line(88, 46, 88, 47, 1)

    # tick_104
    oled.line(100, 44, 100, 47, 1)

    # tick_106
    oled.line(111, 46, 111, 47, 1)

    # tick_108
    oled.line(123, 44, 123, 47, 1)

    # marker
    oled.poly(0, 0, array("h", [63, 41, 69, 41, 66, 44]), 1, True)

    # rds_bg
    oled.fill_rect(0, 52, 128, 12, 1)

    # rds
    u8text.text(oled, font_5x7, 3, 60, "RDS: RADIO 1", 2)

    oled.show()


def main():
    i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=100_000)
    oled = SH1106_I2C(128, 64, i2c)

    drawMainScreen(oled)

    print("Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(2)

    except KeyboardInterrupt:
        print("\nProgram stopped. Exiting...")
        oled.fill(0)
        oled.show()
        time.sleep_ms(200)
        oled.poweroff()


if __name__ == "__main__":
    main()
