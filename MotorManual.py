from gpiozero import OutputDevice
from time import sleep

# Pin Setup
in1 = OutputDevice(22)
in2 = OutputDevice(27)
in3 = OutputDevice(24)
in4 = OutputDevice(23)
step_pins = [in1, in2, in3, in4]

# Half-step sequence
sequence = [
    (1, 0, 0, 0), (1, 1, 0, 0), (0, 1, 0, 0), (0, 1, 1, 0),
    (0, 0, 1, 0), (0, 0, 1, 1), (0, 0, 0, 1), (1, 0, 0, 1)
]

state = {"index": 0}


def move_steps(n=2048, delay=0.0008):
    """
    n: positive for forward, negative for reverse
    delay: speed of rotation
    """
    if n == 0:
        return

    step_dir = 1 if n > 0 else -1
    total_steps = abs(n)

    print(f"Moving {n} steps...")

    for _ in range(total_steps):
        state["index"] = (state["index"] + step_dir) % 8
        step_data = sequence[state["index"]]

        for i, pin in enumerate(step_pins):
            if step_data[i] == 1:
                pin.on()
            else:
                pin.off()

        sleep(delay)

    for pin in step_pins:
        pin.off()


if __name__ == "__main__":
    try:
        while True:
            move_steps(2048)
            sleep(2)

            move_steps(-2048)
            sleep(2)

    except KeyboardInterrupt:
        print("\nScript stopped by user.")

    finally:
        for pin in step_pins:
            pin.off()
        print("Pins cleaned up.")