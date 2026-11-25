# =====================================================================
#  Si4703 power-up test 
#
#  Interface: 2-wire (I2C), address 0x10
#  Bus mode:  Busmode Select Method 1
#             on RST rising edge: GPIO3 = 0, SDIO = 0, SEN = 1 -> 2-wire
#  Clock:     internal oscillator, external 32.768 kHz crystal (XOSCEN = 1)
#  
#  References:
#    Si4702/03-C19 datasheet Rev. 1.1
#      4.9  Reset, Powerup, and Powerdown; Table 4, Fig. 1; Table 9
#      4.11 Initialization Sequence; registers 01h, 07h
#    AN230 Programming Guide Rev. 0.9
#      2.1  Power, Initialization Sequence, and Busmode Selection
#      3.2.2 XOSCEN 
#
#  Wiring: 3.3V -> 3V3(OUT), 
#          GND -> GND, 
#          SDIO -> GP4,
#          SCLK -> GP5,
#          RST -> GP6, 
#          SEN -> 3.3V
#
#  Checks:
#    1. CHIPID after powerup = 0x1253 
#    2. TEST1[13:0] changed 0x0100 -> 0x3C04
#
#   If both checks are cleared device is succesfully powered up
# =====================================================================

from machine import Pin, I2C
import time

SDA_PIN = 4
SCL_PIN = 5
RST_PIN = 6
I2C_ID  = 0
ADDR    = 0x10

CHIPID   = 0x01
POWERCFG = 0x02
TEST1    = 0x07

regs = [0] * 16          # register shadow 00h..0Fh


def show(name, value):
    
    b = '{:016b}'.format(value)
    print('  {:<8} 0x{:04X}  {} {} {} {}'.format(name, value, b[0:4], b[4:8], b[8:12], b[12:16]))


def read_regs(i2c):
    # chip returns 0Ah..0Fh, 00h..09h; high byte first
    data = i2c.readfrom(ADDR, 32)
    for i in range(16):
        reg = (0x0A + i) % 16
        regs[reg] = (data[2 * i] << 8) | data[2 * i + 1]


def write_regs(i2c):
    # write always starts at 02h; send 02h..07h
    buf = bytearray(12)
    for i in range(6):
        value = regs[POWERCFG + i]
        buf[2 * i]     = value >> 8
        buf[2 * i + 1] = value & 0xFF
    i2c.writeto(ADDR, buf)


def hw_reset():
    rst = Pin(RST_PIN, Pin.OUT, value=0)    # hold in reset
    scl = Pin(SCL_PIN, Pin.OUT, value=1)    # SCLK high at RST edge
    sda = Pin(SDA_PIN, Pin.OUT, value=0)    # SDIO low -> Method 1
    time.sleep_ms(1)                        # RST low >= 100 us
    rst.value(1)                            # RST edge: bus mode latched
    time.sleep_ms(1)                        # hold >= 30 ns
    return I2C(I2C_ID, sda=Pin(SDA_PIN), scl=Pin(SCL_PIN), freq=100_000)   # pins back to I2C


def power_up(i2c):
    read_regs(i2c)
    print('Before powerup:')
    show('CHIPID', regs[CHIPID])
    show('TEST1', regs[TEST1])

    #               XOSCEN
    #               |AHIZEN
    #               ||  [13:0] = 0x0100
    regs[TEST1] = 0b1000_0001_0000_0000      
    write_regs(i2c)
    time.sleep_ms(500)                       # crystal startup >= 500 ms

    read_regs(i2c)
    #                  DSMUTE,DMUTE,MONO,- | RDSM,SKMODE,SEEKUP,SEEK | -,DISABLE,-,- | -,-,-,ENABLE
    regs[POWERCFG] = 0b0100_0000_0000_0001   # 0x4001: unmute, ENABLE = 1
    write_regs(i2c)
    time.sleep_ms(110)                       

    read_regs(i2c)
    print('After powerup:')
    show('CHIPID', regs[CHIPID])
    show('TEST1', regs[TEST1])


def main():
    i2c = hw_reset()
    if ADDR not in i2c.scan():
        print('No device at 0x10')
        return None

    power_up(i2c)

    dev = (regs[CHIPID] >> 6) & 0b1111                 # DEV = bits 9:6
    test1_low = regs[TEST1] & 0b0011_1111_1111_1111    # bits 13:0

    ok1 = regs[CHIPID] == 0x1253
    ok2 = test1_low == 0x3C04
    print('[{}] CHIPID = 0x1253 (DEV = {:04b})'.format('OK' if ok1 else 'FAIL', dev))
    print('[{}] TEST1[13:0] = 0x3C04 (read 0x{:04X})'.format('OK' if ok2 else 'FAIL', test1_low))
    print('POWERUP OK' if ok1 and ok2 else 'POWERUP FAILED')
    return i2c


i2c = main()
