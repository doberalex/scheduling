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

    def test_one_minister_reports_impossible_rest_rule(self):
        minister = "Алексей Б."
        self.settings["ministers"] = [minister]
        result = generate(self.settings, 2026, 9)

        self.assertTrue(any("обычные участия" in error for error in result.errors))
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
                self.assertIn(regular_counts[name], (1, 2, 3))
            for slot_id, slot_type in result.slots.items():
                self.assertEqual(3 if slot_type == "fri" else 6, len(result.schedule[slot_id]))
                if slot_type == "sun":
                    self.assertNotIn(slot_id, result.person_slots[result.minister_assignments[slot_id]])
            assigned.extend(
                result.minister_assignments[slot_id]
                for slot_id, slot_type in result.slots.items() if slot_type == "sun"
            )

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
        special_slot = next(slot_id for slot_id in result.minister_assignments if slot_id > 1)
        adjacent_slot = saved["slots"][special_slot - 2]
        adjacent_slot["participants"][0]["name"] = result.minister_assignments[special_slot]
        errors = validate_saved_schedule(saved, self.settings)
        self.assertTrue(any("нет отдыха" in error for error in errors))

    def test_saved_sunday_rejects_second_minister(self):
        ministers = ["Алексей Б.", "Андрей К."]
        self.settings["ministers"] = ministers
        result = generate(self.settings, 2026, 10)
        sunday = next(slot_id for slot_id, slot_type in result.slots.items() if slot_type == "sun")
        special = result.minister_assignments[sunday]
        other = next(name for name in ministers if name != special)
        saved = {
            "slots": [
                {
                    "slot_no": slot_id,
                    "slot_type": slot_type,
                    "participants": [
                        {
                            "name": other if slot_id == sunday and index == 0 else name,
                            "is_scheduled": True,
                            "is_minister_assignment": result.minister_assignments.get(slot_id) == name,
                        }
                        for index, name in enumerate(result.schedule[slot_id])
                    ],
                }
                for slot_id, slot_type in result.slots.items()
            ],
        }
        self.assertTrue(any("только один служитель" in error for error in validate_saved_schedule(saved, self.settings)))

    def test_minister_has_a_rest_slot_between_all_appointments(self):
        ministers = ["Алексей Б.", "Андрей К."]
        self.settings["ministers"] = ministers
        result = generate(self.settings, 2026, 10)
        self.assertEqual([], result.errors)
        for minister in ministers:
            all_slots = sorted(
                result.person_slots[minister]
                + [slot_id for slot_id, name in result.minister_assignments.items() if name == minister]
            )
            self.assertGreaterEqual(len(result.person_slots[minister]), 1)
            self.assertTrue(all(second - first >= 2 for first, second in zip(all_slots, all_slots[1:])))
        for slot_id, slot_type in result.slots.items():
            if slot_type == "sun":
                self.assertEqual(1, sum(name in ministers for name in result.schedule[slot_id]))


if __name__ == "__main__":
    unittest.main()
