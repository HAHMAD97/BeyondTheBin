from gpiozero import OutputDevice
from time import sleep

# Mapping based on your physical wiring:
in1 = OutputDevice(22)
in2 = OutputDevice(27)
in3 = OutputDevice(24)
in4 = OutputDevice(23)

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

def move_motor(steps, direction="forward", delay=0.0015):
    """
    steps: Total number of half-steps to move
    direction: "forward" or "reverse"
    delay: Time between steps (0.001 to 0.002 is usually ideal)
    """
    # Use the sequence as is for forward, or reversed for reverse
    current_sequence = sequence if direction == "forward" else sequence[::-1]
    
    print(f"Moving {steps} steps {direction}...")
    
    for i in range(steps):
        # We use modulo (%) to loop through the 8 stages of the sequence
        step_data = current_sequence[i % 8]
        
        for pin_index in range(4):
            if step_data[pin_index] == 1:
                step_pins[pin_index].on()
            else:
                step_pins[pin_index].off()
        
        sleep(delay)

try:
    # 4096 steps is approximately one full rotation for 28BYJ-48 motors
    
    # Move forward 2000 steps
    move_motor(2048, direction="forward", delay=0.0008)
    
    sleep(1) # Pause for a second
    
    # Move backward 1000 steps
    move_motor(2048, direction="reverse", delay=0.0008)

finally:
    # Always turn pins off at the end to prevent overheating
    for pin in step_pins:
        pin.off()
    print("Pins cleaned up.")
