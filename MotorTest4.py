from gpiozero import OutputDevice
from time import sleep


delay = 0.001
# Mapping based on your current physical wiring:
# IN1 is on GPIO 22
# IN2 is on GPIO 27
# IN3 is on GPIO 24
# IN4 is on GPIO 23
in1 = OutputDevice(22)
in2 = OutputDevice(27)
in3 = OutputDevice(24)
in4 = OutputDevice(23)

# This list MUST follow the IN1, IN2, IN3, IN4 order
step_pins = [in1, in2, in3, in4]


# The Half-Step sequence (8 stages)
sequence = [
    (1, 0, 0, 0), # IN1
    (1, 1, 0, 0), # IN1 & IN2
    (0, 1, 0, 0), # IN2
    (0, 1, 1, 0), # IN2 & IN3
    (0, 0, 1, 0), # IN3
    (0, 0, 1, 1), # IN3 & IN4
    (0, 0, 0, 1), # IN4
    (1, 0, 0, 1)  # IN4 & IN1
]

def rotate_smooth(cycles, delay=0.001):
    for _ in range(cycles):
        for step in sequence:
            for i in range(4):
                if step[i] == 1:
                    step_pins[i].on()
                else:
                    step_pins[i].off()
            sleep(delay)

try:
    print("Rotating smoothly with corrected pin sequence...")
    # 512 cycles of this 8-step sequence is one full rotation
    # A delay of 0.001 to 0.002 is best for half-stepping
    rotate_smooth(512, delay=delay)

finally:
    # Always turn pins off at the end
    for pin in step_pins:
        pin.off()
    print("Pins cleaned up.")
