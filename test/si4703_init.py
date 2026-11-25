# =====================================================================
#  Si4703 – inicializácia v MicroPythone (2-wire / I2C, kryštál 32,768 kHz)
#  Busmode Select Method 1  (SEN=1, SDIO=0, GPIO3=0 pri nábežnej hrane RST)
#  Podľa: Si4702/03-C19 datasheet (kap. 4.9) a AN230 (kap. 2.1, 3.2)
#
#  Zapojenie (Raspberry Pi Pico – piny si môžeš zmeniť nižšie):
#     modul 3.3V  -> Pico 3V3(OUT)  (fyzický pin 36)
#     modul GND   -> Pico GND
#     modul SDIO  -> GP4  (I2C0 SDA)
#     modul SCLK  -> GP5  (I2C0 SCL)
#     modul RST   -> GP6
#     modul GPIO2 -> GP7  (prerušenie STC – "ladenie hotové")
#     modul SEN   -> 3.3V (ak je vyvedený; na väčšine modulov je už na doske HIGH)
# =====================================================================

from machine import Pin, I2C
import time

SDA_PIN = 4
SCL_PIN = 5
RST_PIN = 6
INT_PIN = 7          # GPIO2 modulu; ak ho nezapojíš, daj None

I2C_ID = 0           # GP4/GP5 patria pod I2C0
ADDR   = 0x10        # pevná 7-bitová adresa Si4703 (0010000b)

# ---------------------------------------------------------------------
#  Tieňová kópia registrov
#  Si4703 má 16 registrov po 16 bitoch (00h..0Fh). Nedá sa čítať ani
#  zapisovať jeden konkrétny register – čip vždy:
#    * pri ČÍTANÍ začne od 0Ah, ide po 0Fh a potom pokračuje 00h..09h
#    * pri ZÁPISE začne od 02h a ide ďalej (02h, 03h, ... 07h)
#  Preto si držíme v RAM kópiu všetkých 16 registrov, meníme ju
#  a celú ju posielame späť (read-modify-write).
# ---------------------------------------------------------------------
regs = [0] * 16

# mená registrov (len pre čitateľnosť)
DEVICEID   = 0x00
CHIPID     = 0x01
POWERCFG   = 0x02
CHANNEL    = 0x03
SYSCONFIG1 = 0x04
SYSCONFIG2 = 0x05
SYSCONFIG3 = 0x06
TEST1      = 0x07
STATUSRSSI = 0x0A
READCHAN   = 0x0B


def show(name, value):
    """Vypíše register binárne po štvoriciach bitov: 15..12 11..8 7..4 3..0"""
    b = '{:016b}'.format(value)
    print('{:<11} 0x{:04X}  {} {} {} {}'.format(name, value, b[0:4], b[4:8], b[8:12], b[12:16]))


def read_regs(i2c):
    """Prečíta všetkých 16 registrov (32 bajtov) do tieňovej kópie."""
    data = i2c.readfrom(ADDR, 32)
    # prvé 2 bajty sú register 0Ah, ďalšie 0Bh, ..., potom 0Fh, 00h, 01h, ...
    for i in range(16):
        reg = (0x0A + i) % 16                         # 0A,0B,...,0F,00,01,...,09
        regs[reg] = (data[2 * i] << 8) | data[2 * i + 1]   # horný bajt prvý


def write_regs(i2c):
    """Zapíše registre 02h..07h (6 registrov = 12 bajtov).
    08h a 09h sú rezervované a 0Ah..0Fh sú len na čítanie, tie neposielame."""
    buf = bytearray(12)
    for i in range(6):
        value = regs[POWERCFG + i]
        buf[2 * i]     = value >> 8        # horný bajt
        buf[2 * i + 1] = value & 0xFF      # dolný bajt
    i2c.writeto(ADDR, buf)


# =====================================================================
#  KROK 1 – hardvérový reset a výber zbernice (Busmode Method 1)
# =====================================================================
def hw_reset():
    # 1a) RST = 0 -> čip je v resete, jeho zbernica je VYPNUTÁ a nič nepočúva.
    #     Zároveň sa registre vrátia na predvolené hodnoty (aj RDSD = 0,
    #     čím je splnená errata Si4703-C19 "Solution 1").
    rst = Pin(RST_PIN, Pin.OUT, value=0)

    # 1b) SCLK = 1. Datasheet: pri 2-wire musí byť SCLK HIGH počas
    #     nábežnej hrany RST a ostať HIGH až do prvého I2C STARTu.
    scl = Pin(SCL_PIN, Pin.OUT, value=1)

    # 1c) SDIO = 0. Tu dočasne berieme pin SDA ako obyčajný GPIO výstup.
    #     Pokles SDIO pri SCLK=1 je formálne I2C START, ale čip je v resete,
    #     takže ho ignoruje.
    sda = Pin(SDA_PIN, Pin.OUT, value=0)

    # 1d) Čakáme. RST musí byť LOW aspoň 100 µs (GPIO3 nikto nedrží,
    #     interný 1 MΩ pulldown ho musí stihnúť vybiť na 0) a medzi poklesom
    #     SDIO a hranou RST musí byť > 300 ns. 1 ms je s rezervou.
    time.sleep_ms(1)

    # 1e) RST = 1  <-- TOTO je ten okamih. Čip si teraz prečíta:
    #        GPIO3 = 0  -> Busmode Select Method 1
    #        SDIO  = 0  -> (patrí k metóde 1)
    #        SEN   = 1  -> 2-wire (I2C)
    rst.value(1)

    # 1f) Hold čas (min. 30 ns) – 1 ms s rezervou.
    time.sleep_ms(1)

    # 1g) Vrátime piny do I2C režimu. Vytvorenie objektu I2C prepne GP4/GP5
    #     späť na hardvérové I2C, SDIO sa uvoľní a pull-up ho vytiahne na 1.
    #     (Nábeh SDIO pri SCLK=1 vyzerá ako STOP – to čipu neprekáža.)
    #     Prvý skutočný START príde až s prvou transakciou nižšie.
    i2c = I2C(I2C_ID, sda=Pin(SDA_PIN), scl=Pin(SCL_PIN), freq=100_000)
    return i2c


# =====================================================================
#  KROK 2 + 3 – zapnutie kryštálového oscilátora a zapnutie čipu
# =====================================================================
def power_up(i2c):
    # 2a) Načítame registre (čip je teraz v stave "powerdown", ale registre
    #     sa dajú čítať aj zapisovať).
    read_regs(i2c)
    show('DEVICEID', regs[DEVICEID])
    show('CHIPID', regs[CHIPID])

    # 2b) TEST1 (07h) – zapnutie kryštálového oscilátora.
    #     bit 15    XOSCEN = 1  -> zapni interný oscilátor s kryštálom
    #     bit 14    AHIZEN = 0
    #     bity 13:0 musia byť v powerdown 0x0100 (rezervované, AN230 3.2.2)
    #
    #                      XOSCEN
    #                      |AHIZEN
    #                      ||  rezervované = 0x0100
    regs[TEST1] =        0b1000_0001_0000_0000      # = 0x8100
    write_regs(i2c)      # posiela 02h..07h; 02h..06h ostávajú, ako sme ich prečítali

    # 2c) Kryštál sa musí rozkmitať: aspoň 500 ms PRED nastavením ENABLE.
    time.sleep_ms(500)

    # 3a) Znova načítame registre (čip mohol niečo zmeniť) a nastavíme konfiguráciu.
    read_regs(i2c)

    # SYSCONFIG1 (04h)
    #   bit 15    RDSIEN  = 0   prerušenie pri RDS dátach – nechceme
    #   bit 14    STCIEN  = 1   prerušenie na GPIO2, keď je ladenie/seek hotové
    #   bit 13    -       = 0
    #   bit 12    RDS     = 1   zapni RDS (názov stanice, text)
    #   bit 11    DE      = 1   deemfáza 50 µs (Európa); 0 = 75 µs (USA)
    #   bit 10    AGCD    = 0   AGC zapnuté
    #   bity 9:8  -       = 00
    #   bity 7:6  BLNDADJ = 00  prah stereo/mono – predvolený
    #   bity 5:4  GPIO3   = 00  (pri XOSCEN=1 sa ignoruje, GPIO3 patrí kryštálu)
    #   bity 3:2  GPIO2   = 01  GPIO2 = výstup prerušenia (STC)
    #   bity 1:0  GPIO1   = 00  nepoužité
    #
    #                        RDSIEN,STCIEN,-,RDS | DE,AGCD,-,- | BLNDADJ,GPIO3 | GPIO2,GPIO1
    regs[SYSCONFIG1] =     0b0101_1000_0000_0100      # = 0x5804

    # SYSCONFIG2 (05h)
    #   bity 15:8 SEEKTH = 0001_1001 (25)  prah RSSI pre seek (odporúčané v AN230/AN284)
    #   bity 7:6  BAND   = 00   87,5–108 MHz (Európa/USA)
    #   bity 5:4  SPACE  = 01   rozostup kanálov 100 kHz (Európa); 00 = 200 kHz (USA)
    #   bity 3:0  VOLUME = 0001 hlasitosť 1 z 15 (0 = stlmené)
    #
    #                        SEEKTH ...........  BAND,SPACE  VOLUME
    regs[SYSCONFIG2] =     0b0001_1001_0001_0001      # = 0x1911

    # SYSCONFIG3 (06h)
    #   bity 15:14 SMUTER = 00, bity 13:12 SMUTEA = 00 (softmute – predvolené)
    #   bity 11:9  -      = 000
    #   bit 8      VOLEXT = 0   (1 = hlasitosť o 30 dB tichšia, jemnejší rozsah)
    #   bity 7:4   SKSNR  = 0100  min. SNR pre seek
    #   bity 3:0   SKCNT  = 1000  max. počet FM impulzov pre seek
    #
    #                        SMUTER,SMUTEA,-,- | -,-,-,VOLEXT | SKSNR | SKCNT
    regs[SYSCONFIG3] =     0b0000_0000_0100_1000      # = 0x0048

    # 3b) POWERCFG (02h) – samotné zapnutie čipu
    #   bit 15    DSMUTE  = 0   softmute zapnutý (tlmí šum pri slabom signáli)
    #   bit 14    DMUTE   = 1   1 = ZRUŠ stlmenie (pozor, je to obrátené!)
    #   bit 13    MONO    = 0   stereo povolené
    #   bit 12    -       = 0
    #   bit 11    RDSM    = 0   RDS standard mode
    #   bit 10    SKMODE  = 0   seek na konci pásma pokračuje od začiatku
    #   bit 9     SEEKUP  = 0
    #   bit 8     SEEK    = 0   teraz nehľadáme
    #   bit 7     -       = 0
    #   bit 6     DISABLE = 0   } ENABLE=1 + DISABLE=0 = ZAPNI
    #   bity 5:1  -       = 0   }
    #   bit 0     ENABLE  = 1   }
    #
    #                      DSMUTE,DMUTE,MONO,- | RDSM,SKMODE,SEEKUP,SEEK | -,DISABLE,-,- | -,-,-,ENABLE
    regs[POWERCFG] =     0b0100_0000_0000_0001      # = 0x4001

    write_regs(i2c)      # pošle 02h..07h naraz – konfiguráciu aj ENABLE

    # 3c) Čakanie na nábeh čipu (Powerup Time v datasheete, max. ~110 ms).
    time.sleep_ms(110)

    # 3d) Odteraz VŽDY najprv read_regs(), až potom zápis!
    #     Po zapnutí čip sám zmení TEST1 bity 13:0 na 0x3C04 a tie sa
    #     musia zachovať. Keby sme poslali staré 0x8100, rozbijeme to.
    read_regs(i2c)
    print('Po zapnutí:')
    for name, r in (('POWERCFG', POWERCFG), ('SYSCONFIG1', SYSCONFIG1),
                     ('SYSCONFIG2', SYSCONFIG2), ('TEST1', TEST1)):
        show(name, regs[r])


# =====================================================================
#  Čakanie na STC (Seek/Tune Complete)
# =====================================================================
def wait_stc(i2c, int_pin, timeout_ms=3000):
    """Počká, kým je ladenie/seek hotové.
    S int_pin: čakáme, kým čip stiahne GPIO2 na 0 (impulz ~5 ms) – I2C je
    počas ladenia v kľude (errata kryštálu: aktivita na SDIO spôsobuje jitter).
    Bez int_pin: pýtame sa po I2C (polling) – funguje, ale môže zhoršiť ladenie."""
    start = time.ticks_ms()
    if int_pin is not None:
        while int_pin.value() == 1:
            if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
                print('Timeout STC')
                return
        return
    while True:
        time.sleep_ms(40)
        read_regs(i2c)
        if regs[STATUSRSSI] & (1 << 14):      # bit 14 = STC
            return
        if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
            print('Timeout STC')
            return


# =====================================================================
#  Ladenie na frekvenciu
# =====================================================================
def set_frequency(i2c, mhz, int_pin=None):
    # Pre BAND=00 a SPACE=100 kHz:  f = 87,5 MHz + CHAN × 0,1 MHz
    chan = round((mhz - 87.5) * 10)           # napr. 97,3 MHz -> 98

    # CHANNEL (03h)
    #   bit 15    TUNE = 1   spusti ladenie
    #   bity 14:10 -   = 0
    #   bity 9:0  CHAN = číslo kanála
    #     napr. 98 = 0b00_0110_0010  ->  0b1000_0000_0110_0010
    read_regs(i2c)
    regs[CHANNEL] = (1 << 15) | chan
    show('CHANNEL', regs[CHANNEL])
    write_regs(i2c)

    wait_stc(i2c, int_pin)

    # Po STC musíme TUNE vynulovať (bit 15 -> 0), inak čip nevynuluje STC
    # a ďalšie ladenie sa nespustí.
    read_regs(i2c)
    regs[CHANNEL] &= 0b0111_1111_1111_1111
    write_regs(i2c)

    # Počkáme, kým čip zhodí STC späť na 0.
    while True:
        read_regs(i2c)
        if not regs[STATUSRSSI] & (1 << 14):
            break


# =====================================================================
#  Seek – automatické hľadanie stanice
# =====================================================================
def seek(i2c, up=True, wrap=True, int_pin=None):
    """Nájde najbližšiu stanicu od aktuálnej frekvencie.
    up   = True  -> hľadaj nahor (doprava),  False -> nadol (doľava)
    wrap = True  -> na konci pásma pokračuj z druhého konca (SKMODE = 0)
           False -> na konci pásma zastav                  (SKMODE = 1)
    Vracia (nájdené, frekvencia_MHz, rssi)."""

    # 1) Nastavenie bitov v POWERCFG (02h)
    #    bit 10 SKMODE : 0 = wrap (pokračuj dookola), 1 = zastav na konci pásma
    #    bit  9 SEEKUP : 1 = nahor, 0 = nadol
    #    bit  8 SEEK   : 1 = štart
    #
    #    bity 10..8:  SKMODE SEEKUP SEEK
    #    napr. nahor + wrap      -> 0 1 1  (xxxx x011 xxxx xxxx)
    #          nadol + stop      -> 1 0 1  (xxxx x101 xxxx xxxx)
    read_regs(i2c)
    if wrap:
        regs[POWERCFG] &= ~(1 << 10)     # SKMODE = 0
    else:
        regs[POWERCFG] |= (1 << 10)      # SKMODE = 1
    if up:
        regs[POWERCFG] |= (1 << 9)       # SEEKUP = 1
    else:
        regs[POWERCFG] &= ~(1 << 9)      # SEEKUP = 0
    regs[POWERCFG] |= (1 << 8)           # SEEK = 1 -> štart
    show('POWERCFG', regs[POWERCFG])
    write_regs(i2c)

    # 2) Čakanie na koniec. Prechod celým pásmom (205 kanálov) môže trvať
    #    aj ~12 s, preto dlhší timeout. Počas seeku nepollujeme I2C (errata).
    wait_stc(i2c, int_pin, timeout_ms=15000)

    # 3) Výsledok. SF/BL (0Ah, bit 13):
    #    0 = našiel platnú stanicu
    #    1 = wrap:  nič nenašiel, čip sa VRÁTIL na pôvodnú frekvenciu
    #        stop:  narazil na koniec pásma a ostal tam
    read_regs(i2c)
    found = not (regs[STATUSRSSI] & (1 << 13))
    freq  = 87.5 + (regs[READCHAN] & 0b11_1111_1111) * 0.1
    rssi  = regs[STATUSRSSI] & 0xFF

    # 4) Ukončenie handshaku: SEEK = 0, potom počkať, kým čip zhodí STC
    #    (tým sa vynuluje aj SF/BL).
    regs[POWERCFG] &= ~(1 << 8)          # SEEK = 0
    write_regs(i2c)
    start = time.ticks_ms()
    while True:
        read_regs(i2c)
        if not regs[STATUSRSSI] & (1 << 14):
            break
        if time.ticks_diff(time.ticks_ms(), start) > 1000:
            print('Timeout pri nulovaní STC')
            break

    if found:
        print('Stanica: {:.1f} MHz  RSSI {} dBµV'.format(freq, rssi))
    else:
        print('Nič nenájdené (SF/BL = 1), frekvencia ostala {:.1f} MHz'.format(freq))
    return found, freq, rssi


def set_volume(i2c, vol):
    vol = max(0, min(15, vol))
    read_regs(i2c)
    regs[SYSCONFIG2] &= 0b1111_1111_1111_0000   # vynuluj bity 3:0 (VOLUME)
    regs[SYSCONFIG2] |= vol                     # a vlož novú hlasitosť
    write_regs(i2c)


def status(i2c):
    read_regs(i2c)
    s = regs[STATUSRSSI]
    # STATUSRSSI (0Ah): bit 14 STC, bit 13 SF/BL, bit 8 ST (stereo), bity 7:0 RSSI
    freq = 87.5 + (regs[READCHAN] & 0b11_1111_1111) * 0.1
    print('Frekvencia: {:.1f} MHz  RSSI: {} dBµV  Stereo: {}'.format(
        freq, s & 0xFF, 'áno' if s & (1 << 8) else 'nie'))
    show('STATUSRSSI', s)


# =====================================================================
#  Hlavný program
# =====================================================================
def main():
    i2c = hw_reset()                         # KROK 1: reset + výber I2C
    found = i2c.scan()
    print('I2C zariadenia:', [hex(a) for a in found])
    if ADDR not in found:
        # Pozn.: raise SystemExit by v MicroPythone spravil soft reboot,
        # preto len vypíšeme chybu a funkciu ukončíme.
        print('Si4703 sa neozval na 0x10 – skontroluj zapojenie, napájanie, pull-upy, SEN=1 a RST.')
        return None

    power_up(i2c)                            # KROK 2 + 3: oscilátor + ENABLE

    int_pin = Pin(INT_PIN, Pin.IN, Pin.PULL_UP) if INT_PIN is not None else None
    set_volume(i2c, 3)
    set_frequency(i2c, 87.6, int_pin)        # zmeň na svoju stanicu
    status(i2c)

    # Príklady seeku:
    seek(i2c, up=False,  wrap=True,  int_pin=int_pin)   # ďalšia stanica nahor, dookola
    # seek(i2c, up=False, wrap=False, int_pin=int_pin)   # nadol, zastav na 87,5 MHz
    return i2c


i2c = main()