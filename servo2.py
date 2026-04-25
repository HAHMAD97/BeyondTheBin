from gpiozero import Servo
from time import sleep

# Most servos use a pulse width between 1ms and 2ms. 
# We define them here to prevent the servo from hitting its physical limits.
my_factory = None # Default factory

# Use GPIO 18 (Pin 12)
servo = Servo(17)

try:
    while True:
        print("Moving to Min")
        servo.angle(15)
        sleep(2)
        
        print("Moving to Mid")
        servo.angle(30)
        sleep(2)
        
        print("Moving to Max")
        servo.max(45)
        sleep(2)

except KeyboardInterrupt:
    print("Program stopped")