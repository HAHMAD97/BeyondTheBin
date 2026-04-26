from gpiozero import DistanceSensor
from time import sleep

# Define pins
# echo=17, trigger=25
sensor = DistanceSensor(echo=20, trigger=21)

print("Starting distance measurement...")

try:
    while True:
        # sensor.distance returns a value in meters
        # we multiply by 100 to get centimeters
        dist = sensor.distance * 100
        print(f"Distance: {dist:.1f} cm")
        sleep(0.1)

except KeyboardInterrupt:
    print("\nMeasurement stopped by user")
