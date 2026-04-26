from gpiozero import Servo
from time import sleep

servo = Servo(17)  # GPIO 17, physical pin 11

while True:
    servo.min()   # one side
    sleep(1)

    servo.mid()   # center
    sleep(1)

    servo.max()   # other side
    sleep(1)
