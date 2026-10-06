from datetime import datetime
from zoneinfo import ZoneInfo
import unittest
from scripts.weekly_release import due_release


class ReleaseScheduleTests(unittest.TestCase):
    calendar = [{'release_date': '2026-10-07', 'release_time': '10:30', 'data_for_date': '2026-10-02'},
                {'release_date': '2026-10-15', 'release_time': '12:00', 'data_for_date': '2026-10-09'}]

    def now(self, value): return datetime.fromisoformat(value).replace(tzinfo=ZoneInfo('America/Chicago'))

    def test_normal_release_starts_at_0931_central(self):
        self.assertIsNone(due_release(self.calendar, self.now('2026-10-07T09:30:59')))
        self.assertEqual(due_release(self.calendar, self.now('2026-10-07T09:31:00'))['data_for_date'], '2026-10-02')

    def test_holiday_waits_until_1101_thursday(self):
        self.assertIsNone(due_release(self.calendar, self.now('2026-10-14T09:31:00')))
        self.assertIsNone(due_release(self.calendar, self.now('2026-10-15T09:31:00')))
        self.assertEqual(due_release(self.calendar, self.now('2026-10-15T11:01:00'))['data_for_date'], '2026-10-09')

    def test_expired_calendar_stops(self):
        with self.assertRaisesRegex(RuntimeError, 'coverage ended'):
            due_release(self.calendar, self.now('2027-01-01T09:31:00'))
