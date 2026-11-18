# test for dual rotary encoder with buttons in MicroPython 
from rotary_irq_rp2 import RotaryIRQ
from gpio_devices import Button
import time

btnA = Button(12)
encA = RotaryIRQ(pin_num_clk=14,
                 pin_num_dt=13,
                 half_step=True)

btnB = Button(15)
encB = RotaryIRQ(pin_num_clk=17,
                 pin_num_dt=16,
                 half_step=True)

btnA_last_change = time.ticks_ms()
while True:
    val_new_A = encA.value()
    val_new_B = encB.value()
   
    
    if btnA.was_pressed():
        btnA_last_change = time.ticks_ms()
        print(f"\rButton A pressed")
        #print('time',btnA_last_change)
        #if btnA.is_released():
        #    print(f"\rButton A pressed short")
        
    if (btnA.is_pressed() and ((time.ticks_ms() - btnA_last_change) > 1000)):
        #print('time',(time.ticks_ms() - btnA_last_change))
        print(f"\rButton A pressed long")    
        
    if btnB.was_pressed():
        print(f"\rButton B pressed       ")
    
    print('\rA = ', val_new_A, end="  ")
    print(  'B = ', val_new_B, end="     ")
    
    time.sleep_ms(20)
