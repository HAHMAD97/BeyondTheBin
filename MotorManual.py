from gpiozero import OutputDevice
from time import sleep

# Pin Setup
in1 = OutputDevice(22)
in2 = OutputDevice(27)
in3 = OutputDevice(24)
in4 = OutputDevice(23)
step_pins = [in1, in2, in3, in4]

# The Half-Step sequence (8 stages)
sequence = [
    (1, 0, 0, 0), (1, 1, 0, 0), (0, 1, 0, 0), (0, 1, 1, 0),
    (0, 0, 1, 0), (0, 0, 1, 1), (0, 0, 0, 1), (1, 0, 0, 1)
]

# Track the current position in the sequence globally
# This prevents jerking when switching directions
state = {"index": 0}

def move_steps(n, delay=0.0008):
    """
    n: positive for forward, negative for reverse
    delay: speed of rotation
    """
    if n == 0:
        return

    # Determine direction
    step_dir = 1 if n > 0 else -1
    total_steps = abs(n)
    
    print(f"Moving {n} steps...")

    for _ in range(total_steps):
        # Update the global sequence index
        state["index"] = (state["index"] + step_dir) % 8
        
        step_data = sequence[state["index"]]
        
        # Apply the step to pins
        for i in range(4):
            if step_data[i] == 1:
                step_pins[i].on()
            else:
                step_pins[i].off()
        
        sleep(delay)
    
    # Optional: Turn pins off after moving to save power/heat
    # Note: Turning them off reduces "holding torque" (the motor can be spun by hand)
    for pin in step_pins:
        pin.off()

try:
    # print("--- Stepper Control Loaded ---")
    # print("Enter a positive number for Forward (e.g. 2000)")
    # print("Enter a negative number for Reverse (e.g. -2000)")
    # print("Press Ctrl+C to exit.")
    # print("Tip: 4096 steps is roughly one full rotation.")

    while True:
        user_input = input("\nSteps to move: ")
        
        try:
            steps = int(user_input)
            move_steps(steps)
        except ValueError:
            print("Please enter a valid whole number (integer).")

# except KeyboardInterrupt:
#     print("\nScript stopped by user.")

finally:
    # Cleanup
    for pin in step_pins:
        pin.off()
    print("Pins cleaned up.")
