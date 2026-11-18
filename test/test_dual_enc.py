# example for MicroPython rotary encoder
from rotary_irq_rp2 import RotaryIRQ
from gpio_devices import Button
import time


encA = RotaryIRQ(pin_num_clk=14,
              pin_num_dt=13,
              half_step=True)
btnA = Button(12)

encB = RotaryIRQ(pin_num_clk=17,
              pin_num_dt=16,
              half_step=True)
btnB = Button(15)


while True:
    val_new_A = encA.value()
    val_new_B = encB.value()

    if btnA.was_pressed():
        print(f"\rButton A pressed       ")
    if btnB.was_pressed():
        print(f"\rButton B pressed       ")
    
    print('\rA = ', val_new_A, end="  ")
    print(  'B = ', val_new_B, end="     ")
    
    time.sleep_ms(20)
