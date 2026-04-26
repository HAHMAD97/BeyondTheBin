from gpiozero import DistanceSensor
from time import sleep, monotonic

class trash_distance_sensor:
    def __init__(
        self,
        echo_pin=20,
        trigger_pin=21,
        target_cm=50,
        tolerance_cm=10,
        hold_seconds=2,
    ):
        self.sensor = DistanceSensor(echo=echo_pin, trigger=trigger_pin)
        self.target_cm = target_cm
        self.tolerance_cm = tolerance_cm
        self.hold_seconds = hold_seconds

    def get_distance_cm(self):
        return self.sensor.distance * 100

    def is_in_range(self, distance_cm=None):
        if distance_cm is None:
            distance_cm = self.get_distance_cm()

        return (
            self.target_cm - self.tolerance_cm
            <= distance_cm
            <= self.target_cm + self.tolerance_cm
        )

    def wait_for_item(self, check_interval=0.1, verbose=True):
        in_range_since = None

        while True:
            dist_cm = self.get_distance_cm()

            if verbose:
                print(f"Distance: {dist_cm:.1f} cm")

            if self.is_in_range(dist_cm):
                if in_range_since is None:
                    in_range_since = monotonic()

                if monotonic() - in_range_since >= self.hold_seconds:
                    return dist_cm
            else:
                in_range_since = None

            sleep(check_interval)

    def wait_for_item_removed(self, removed_distance_cm=70, check_interval=0.1):
        while True:
            dist_cm = self.get_distance_cm()

            if dist_cm > removed_distance_cm:
                return dist_cm

            sleep(check_interval)