import unittest
from copy import deepcopy

from app.services.scheduler import generate, validate_schedule
from app.services.settings_store import DEFAULT_SETTINGS


class MinisterScheduleTests(unittest.TestCase):
    def setUp(self):
        self.settings = deepcopy(DEFAULT_SETTINGS)
        self.settings["blockedStart"] = []
        self.settings["previousParticipationCounts"] = {}

    def test_one_minister_is_extra_on_every_sunday(self):
        minister = "Алексей Б."
        self.settings["ministers"] = [minister]
        result = generate(self.settings, 2026, 9)

        self.assertEqual([], result.errors)
        for slot_id, slot_type in result.slots.items():
            names = result.schedule[slot_id]
            if slot_type == "sun":
                self.assertEqual(6, len(names))
                self.assertEqual(1, names.count(minister))
            else:
                self.assertEqual(3, len(names))
                self.assertNotIn(minister, names)

    def test_ministers_rotate_across_months(self):
        ministers = ["Алексей Б.", "Андрей К."]
        self.settings["ministers"] = ministers
        assigned = []

        for month in (10, 11):
            result = generate(self.settings, 2026, month)
            self.assertEqual([], result.errors)
            assigned.extend(
                next(name for name in result.schedule[slot_id] if name in ministers)
                for slot_id, slot_type in result.slots.items() if slot_type == "sun"
            )

        self.assertTrue(all(first != second for first, second in zip(assigned, assigned[1:])))
        self.assertLessEqual(abs(assigned.count(ministers[0]) - assigned.count(ministers[1])), 1)

    def test_missing_minister_fails_validation(self):
        self.settings["ministers"] = ["Алексей Б."]
        result = generate(self.settings, 2026, 9)
        sunday = next(slot_id for slot_id, slot_type in result.slots.items() if slot_type == "sun")
        result.schedule[sunday].remove("Алексей Б.")
        errors = validate_schedule(
            result.schedule, result.person_slots, result.slots,
            self.settings["limits"], self.settings["blockedStart"],
            self.settings["singleParticipation"], self.settings["onlySunday"],
            self.settings["previousParticipationCounts"], self.settings["ministers"],
        )
        self.assertTrue(any("служитель" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
