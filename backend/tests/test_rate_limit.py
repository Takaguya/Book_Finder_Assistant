import unittest

from app.dependencies.rate_limit import Limit, check_limits, human_wait

PER_MINUTE = Limit("minute", 2, 60, "")
PER_DAY = Limit("day", 5, 86_400, "")


class CheckLimitsTest(unittest.TestCase):
    def test_first_request_starts_every_counter(self):
        updates, blocked = check_limits({}, [PER_MINUTE, PER_DAY], now=120.0)
        self.assertIsNone(blocked)
        self.assertEqual(updates, {
            "minute": {"window": 2, "count": 1},
            "day": {"window": 0, "count": 1},
        })

    def test_blocks_at_the_limit_with_seconds_until_the_window_ends(self):
        state = {"minute": {"window": 2, "count": 2}}
        updates, blocked = check_limits(state, [PER_MINUTE], now=130.0)
        self.assertIsNone(updates)
        self.assertEqual(blocked, (PER_MINUTE, 50))

    def test_new_window_resets_the_count(self):
        state = {"minute": {"window": 2, "count": 2}}
        updates, blocked = check_limits(state, [PER_MINUTE], now=180.0)
        self.assertIsNone(blocked)
        self.assertEqual(updates, {"minute": {"window": 3, "count": 1}})

    def test_refused_request_uses_up_no_allowance(self):
        # The day counter has room, but the minute counter is full: nothing may be written.
        state = {"minute": {"window": 2, "count": 2}, "day": {"window": 0, "count": 1}}
        updates, blocked = check_limits(state, [PER_DAY, PER_MINUTE], now=130.0)
        self.assertIsNone(updates)
        self.assertIs(blocked[0], PER_MINUTE)


class HumanWaitTest(unittest.TestCase):
    def test_wording(self):
        self.assertEqual(human_wait(1), "1 second")
        self.assertEqual(human_wait(45), "45 seconds")
        self.assertEqual(human_wait(60), "1 minute")
        self.assertEqual(human_wait(61), "2 minutes")
        self.assertEqual(human_wait(3_600), "1 hour")
        self.assertEqual(human_wait(3_601), "2 hours")


if __name__ == "__main__":
    unittest.main()
