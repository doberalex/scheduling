import unittest
from copy import deepcopy

from app.services.scheduler import generate, validate_schedule
from app.handlers import validate_saved_schedule
from app.services.settings_store import DEFAULT_SETTINGS


class MinisterScheduleTests(unittest.TestCase):
    def setUp(self):
        self.settings = deepcopy(DEFAULT_SETTINGS)
        self.settings["blockedStart"] = []
        self.settings["previousParticipationCounts"] = {}

    def test_one_minister_keeps_regular_assignments(self):
        minister = "Алексей Б."
        self.settings["ministers"] = [minister]
        result = generate(self.settings, 2026, 9)

        self.assertEqual([], result.errors)
        self.assertGreaterEqual(len(result.person_slots[minister]), 2)
        self.assertLessEqual(len(result.person_slots[minister]), 3)
        for slot_id, slot_type in result.slots.items():
            names = result.schedule[slot_id]
            if slot_type == "sun":
                self.assertEqual(6, len(names))
                self.assertEqual(1, names.count(minister))
                self.assertEqual(minister, result.minister_assignments[slot_id])
                self.assertNotIn(slot_id, result.person_slots[minister])
            else:
                self.assertEqual(3, len(names))

    def test_ministers_rotate_across_months(self):
        ministers = ["Алексей Б.", "Андрей К."]
        self.settings["ministers"] = ministers
        assigned = []
        regular_counts = {name: 0 for name in ministers}

        for month in (10, 11):
            result = generate(self.settings, 2026, month)
            self.assertEqual([], result.errors)
            for name in ministers:
                regular_counts[name] = len(result.person_slots[name])
                self.assertIn(regular_counts[name], (2, 3))
            for slot_id, slot_type in result.slots.items():
                self.assertEqual(3 if slot_type == "fri" else 6, len(result.schedule[slot_id]))
                if slot_type == "sun":
                    self.assertNotIn(slot_id, result.person_slots[result.minister_assignments[slot_id]])
            assigned.extend(
                result.minister_assignments[slot_id]
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
            result.minister_assignments,
        )
        self.assertTrue(any("служитель" in error for error in errors))

    def test_saved_assignments_keep_regular_and_special_counts_separate(self):
        self.settings["ministers"] = ["Алексей Б.", "Андрей К."]
        result = generate(self.settings, 2026, 11)
        saved = {
            "slots": [
                {
                    "slot_no": slot_id,
                    "slot_type": slot_type,
                    "participants": [
                        {
                            "name": name,
                            "is_scheduled": True,
                            "is_minister_assignment": result.minister_assignments.get(slot_id) == name,
                        }
                        for name in result.schedule[slot_id]
                    ],
                }
                for slot_id, slot_type in result.slots.items()
            ],
        }
        self.assertEqual([], validate_saved_schedule(saved, self.settings))


if __name__ == "__main__":
    unittest.main()
