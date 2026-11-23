from array import array
import time

import display  # display.create() -> OLED (Pico: I2C, ESP32-S3: SPI)
from sh1106 import SH1106
import u8text
import font_5x7, font_profont12, font_profont29

from rotary_irq_rp2 import RotaryIRQ  # rotary encoder (works on Pico and ESP32)
from rotary import Rotary  # Rotary.RANGE_BOUNDED / RANGE_WRAP / RANGE_UNBOUNDED

# Encoder pins (same on Pico and ESP32-S3): CLK = 17, DT = 16, SW = 15
ENC_CLK = 17
ENC_DT = 16
ENC_SW = 15

def drawMainScreen(oled: SH1106, freq: float = 87.5):

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
    u8text.text(oled, font_profont29, 6, 34, f"{freq:.1f}")

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
    t = (freq - 87.5) / (108.0 - 87.5)
    x_point = round(4 + t * (123 - 4))
    # marker
    for i in range(4):
        oled.hline(x_point - 3 + i, 39 + i, 7 - 2 * i, 1)
    # rds_bg
    oled.fill_rect(0, 52, 128, 12, 1)

    # rds
    u8text.text(oled, font_5x7, 3, 60, "RDS: RADIO 1", 2)

    oled.show()


def main():
    oled = display.create()

    # TODO: set the range you need (min_val, max_val, incr, range_mode=Rotary.RANGE_BOUNDED)
    enc = RotaryIRQ(
        pin_num_clk=ENC_CLK,
        pin_num_dt=ENC_DT,
        half_step=True,
        min_val=875,
        max_val=1080,
        range_mode=Rotary.RANGE_BOUNDED,
    )
    drawMainScreen(oled, enc.value() / 10)
    last = enc.value()
    print("Press Ctrl+C to stop.")

    try:
        while True:
            val = enc.value()
            if val != last:
                last = val
                drawMainScreen(oled, val / 10)

            time.sleep_ms(20)

    except KeyboardInterrupt:
        print("\nProgram stopped. Exiting...")
        oled.fill(0)
        oled.show()
        time.sleep_ms(200)
        oled.poweroff()


if __name__ == "__main__":
    main()
