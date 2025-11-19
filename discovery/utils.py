import six
from django.contrib.auth.tokens import PasswordResetTokenGenerator

import time
import threading


class SimplifiedIDGenerator:
    """
    A simple and robust class to generate 64-bit time-sortable IDs.

    Structure:
    - 41 bits for timestamp (milliseconds since a custom epoch)
    - 22 bits for a sequence number that resets every millisecond
    """

    # Set a custom epoch (in milliseconds).
    # This should be a fixed date in the past.
    # Example: 2024-01-01 00:00:00 UTC
    EPOCH = 1704067200000

    SEQUENCE_BITS = 22

    MAX_SEQUENCE = -1 ^ (-1 << SEQUENCE_BITS)
    TIMESTAMP_SHIFT = SEQUENCE_BITS

    def __init__(self):
        self.sequence = 0
        self.last_timestamp = -1
        # A lock is still essential for thread safety within a single process
        self.lock = threading.Lock()

    def _get_timestamp_ms(self):
        return int(time.time() * 1000)

    def _wait_for_next_ms(self, last_timestamp):
        timestamp = self._get_timestamp_ms()
        while timestamp <= last_timestamp:
            timestamp = self._get_timestamp_ms()
        return timestamp

    def generate_id(self):
        with self.lock:
            timestamp = self._get_timestamp_ms()

            if timestamp < self.last_timestamp:
                # This can happen if the system clock goes backward.
                raise Exception("Clock moved backwards. Refusing to generate ID.")

            if timestamp == self.last_timestamp:
                self.sequence = (self.sequence + 1) & self.MAX_SEQUENCE
                if self.sequence == 0:
                    # Sequence overflowed, wait for the next millisecond
                    timestamp = self._wait_for_next_ms(self.last_timestamp)
            else:
                self.sequence = 0

            self.last_timestamp = timestamp

            # Assemble the final 64-bit ID by combining the timestamp and sequence
            new_id = (
                    ((timestamp - self.EPOCH) << self.TIMESTAMP_SHIFT) |
                    self.sequence
            )
            return new_id


# Create a global instance for your Django project.
# This is now perfectly suited for your BaseModel's save() method.
id_generator = SimplifiedIDGenerator()


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (
            six.text_type(user.pk)
            + six.text_type(timestamp)
            + six.text_type(user.is_active)
        )


account_activation_token = AccountActivationTokenGenerator()
password_reset_token = PasswordResetTokenGenerator()
