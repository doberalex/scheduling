from __future__ import annotations

import zlib
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any


SLOT_TYPES = {"fri", "sun"}
SLOT_LABELS = {"fri": "пятница", "sun": "воскресенье"}


@dataclass(frozen=True)
class ScheduleResult:
    year: int
    month: int
    slots: dict[int, str]
    slot_dates: dict[int, str]
    schedule: dict[int, list[str]]
    person_slots: dict[str, list[int]]
    resolved_slot_limits: dict[int, int]
    errors: list[str]


def seeded_rank(value: str, seed: int | str) -> int:
    return zlib.crc32(f"{seed}|{value}".encode("utf-8"))


def build_month_slots(year: int, month: int, extra_dates: dict[str, list[str]] | None = None) -> tuple[dict[int, str], dict[int, str]]:
    items: list[tuple[date, str]] = []
    current = date(year, month, 1)

    while current.month == month:
        if current.weekday() == 4:
            items.append((current, "fri"))
        elif current.weekday() == 6:
            items.append((current, "sun"))

        current += timedelta(days=1)

    for slot_type, values in (extra_dates or {}).items():
        if slot_type not in SLOT_TYPES:
            continue

        for value in values:
            parsed = parse_date(value)

            if parsed.year == year and parsed.month == month:
                items.append((parsed, slot_type))

    deduplicated = sorted(set(items), key=lambda item: (item[0], item[1]))
    slots = {index: slot_type for index, (_, slot_type) in enumerate(deduplicated, start=1)}
    slot_dates = {index: item_date.strftime("%d.%m.%Y") for index, (item_date, _) in enumerate(deduplicated, start=1)}

    return slots, slot_dates


def parse_date(value: str) -> date:
    value = value.strip()

    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass

    raise ValueError("Дата должна быть в формате ДД.ММ.ГГГГ")


def valid_interval(slots_list: list[int], new_slot: int) -> bool:
    return all(abs(slot_id - new_slot) >= 3 for slot_id in slots_list)


def get_max_participation(person: str, single_participation: list[str]) -> int:
    return 1 if person in single_participation else 3


def needs_both_slot_types(person: str, single_participation: list[str], only_sunday: list[str]) -> bool:
    return get_max_participation(person, single_participation) > 1 and person not in only_sunday


def get_person_slot_types(slots_list: list[int], slots: dict[int, str]) -> set[str]:
    return {slots[slot_id] for slot_id in slots_list}


def valid_person_slot_types(
    person: str,
    slots_list: list[int],
    slots: dict[int, str],
    single_participation: list[str],
    only_sunday: list[str],
) -> bool:
    if not needs_both_slot_types(person, single_participation, only_sunday):
        return True

    if len(slots_list) < 2:
        return False

    types = get_person_slot_types(slots_list, slots)

    return "fri" in types and "sun" in types


def get_base_slot_limits(slots: dict[int, str], limits: dict[str, int]) -> dict[int, int]:
    return {slot_id: int(limits[slot_type]) for slot_id, slot_type in slots.items()}


def create_empty_schedule(slots: dict[int, str]) -> dict[int, list[str]]:
    return {slot_id: [] for slot_id in slots}


def create_empty_person_slots(people: list[str]) -> dict[str, list[int]]:
    return {person: [] for person in people}


def basic_can_use_slot(person: str, slot_id: int, slots: dict[int, str], blocked_start: list[str], only_sunday: list[str]) -> bool:
    if person in blocked_start and slot_id in [1, 2]:
        return False

    if person in only_sunday and slots[slot_id] != "sun":
        return False

    return True


def get_allowed_slots_for_person(person: str, slots: dict[int, str], blocked_start: list[str], only_sunday: list[str]) -> list[int]:
    return [
        slot_id
        for slot_id in slots
        if basic_can_use_slot(person, slot_id, slots, blocked_start, only_sunday)
    ]


def generate_slot_combinations(allowed_slots: list[int], max_count: int, start_index: int = 0, current: list[int] | None = None) -> list[list[int]]:
    current = current or []
    combinations = []

    if current:
        combinations.append(current)

    if len(current) >= max_count:
        return combinations

    for index in range(start_index, len(allowed_slots)):
        slot_id = allowed_slots[index]

        if not valid_interval(current, slot_id):
            continue

        combinations.extend(
            generate_slot_combinations(
                allowed_slots,
                max_count,
                index + 1,
                [*current, slot_id],
            )
        )

    return combinations


def get_person_options(
    person: str,
    slots: dict[int, str],
    blocked_start: list[str],
    single_participation: list[str],
    only_sunday: list[str],
    seed: int,
) -> list[list[int]]:
    max_count = get_max_participation(person, single_participation)
    allowed_slots = get_allowed_slots_for_person(person, slots, blocked_start, only_sunday)
    options = []

    for combination in generate_slot_combinations(allowed_slots, max_count):
        count = len(combination)

        if person in single_participation:
            if count == 1:
                options.append(combination)

            continue

        if person in only_sunday:
            options.append(combination)
            continue

        if count >= 2 and valid_person_slot_types(person, combination, slots, single_participation, only_sunday):
            options.append(combination)

    return sorted(
        options,
        key=lambda option: (
            -len(option),
            seeded_rank(f"{person}:{','.join(map(str, option))}", seed),
        ),
    )


def option_fits_remaining(option: list[int], remaining: dict[int, int]) -> bool:
    used: dict[int, int] = {}

    for slot_id in option:
        used[slot_id] = used.get(slot_id, 0) + 1

        if used[slot_id] > remaining[slot_id]:
            return False

    return True


def subtract_option_from_remaining(option: list[int], remaining: dict[int, int]) -> dict[int, int]:
    result = remaining.copy()

    for slot_id in option:
        result[slot_id] -= 1

    return result


def remaining_total(remaining: dict[int, int]) -> int:
    return sum(remaining.values())


def max_assignable_from_index(people: list[str], options_by_person: dict[str, list[list[int]]], index: int) -> int:
    total = 0

    for person in people[index:]:
        total += max((len(option) for option in options_by_person[person]), default=0)

    return total


def solve_by_person_options(
    people: list[str],
    options_by_person: dict[str, list[list[int]]],
    remaining: dict[int, int],
    person_slots: dict[str, list[int]],
    index: int = 0,
) -> bool:
    if index >= len(people):
        return remaining_total(remaining) == 0

    if remaining_total(remaining) > max_assignable_from_index(people, options_by_person, index):
        return False

    person = people[index]

    for option in options_by_person[person]:
        if not option_fits_remaining(option, remaining):
            continue

        person_slots[person] = option

        if solve_by_person_options(
            people,
            options_by_person,
            subtract_option_from_remaining(option, remaining),
            person_slots,
            index + 1,
        ):
            return True

        person_slots[person] = []

    return False


def build_schedule_from_person_slots(person_slots: dict[str, list[int]], slots: dict[int, str]) -> dict[int, list[str]]:
    schedule = create_empty_schedule(slots)

    for person, person_slot_list in person_slots.items():
        for slot_id in person_slot_list:
            schedule[slot_id].append(person)

    return schedule


def try_build_schedule_by_person_options(
    people: list[str],
    slots: dict[int, str],
    slot_limits: dict[int, int],
    blocked_start: list[str],
    single_participation: list[str],
    only_sunday: list[str],
    seed: int,
) -> tuple[bool, dict[int, list[str]], dict[str, list[int]]]:
    options_by_person = {}

    for person in people:
        options = get_person_options(person, slots, blocked_start, single_participation, only_sunday, seed)

        if not options:
            return False, create_empty_schedule(slots), create_empty_person_slots(people)

        options_by_person[person] = options

    ordered_people = sorted(
        people,
        key=lambda person: (len(options_by_person[person]), seeded_rank(person, seed)),
    )
    person_slots = create_empty_person_slots(people)

    if not solve_by_person_options(ordered_people, options_by_person, slot_limits, person_slots):
        return False, create_empty_schedule(slots), create_empty_person_slots(people)

    return True, build_schedule_from_person_slots(person_slots, slots), person_slots


def can_assign_with_slot_limits(
    person: str,
    slot_id: int,
    person_slots: dict[str, list[int]],
    slots: dict[int, str],
    schedule: dict[int, list[str]],
    slot_limits: dict[int, int],
    blocked_start: list[str],
    single_participation: list[str],
    only_sunday: list[str],
) -> bool:
    if person in blocked_start and slot_id in [1, 2]:
        return False

    if person in only_sunday and slots[slot_id] != "sun":
        return False

    current = person_slots.get(person, [])

    if len(current) >= get_max_participation(person, single_participation):
        return False

    if not valid_interval(current, slot_id):
        return False

    if person in schedule[slot_id]:
        return False

    if len(schedule[slot_id]) >= slot_limits[slot_id]:
        return False

    return True


def compare_candidates(person: str, person_slots: dict[str, list[int]]) -> tuple[int, str]:
    return len(person_slots.get(person, [])), person


def find_next_slot(
    schedule: dict[int, list[str]],
    person_slots: dict[str, list[int]],
    people: list[str],
    slots: dict[int, str],
    slot_limits: dict[int, int],
    blocked_start: list[str],
    single_participation: list[str],
    only_sunday: list[str],
) -> tuple[int | None, list[str]]:
    best_slot_id = None
    best_candidates: list[str] = []

    for slot_id in slots:
        if len(schedule[slot_id]) >= slot_limits[slot_id]:
            continue

        candidates = sorted(
            [
                person
                for person in people
                if can_assign_with_slot_limits(
                    person,
                    slot_id,
                    person_slots,
                    slots,
                    schedule,
                    slot_limits,
                    blocked_start,
                    single_participation,
                    only_sunday,
                )
            ],
            key=lambda person: compare_candidates(person, person_slots),
        )

        if best_slot_id is None or len(candidates) < len(best_candidates):
            best_slot_id = slot_id
            best_candidates = candidates

            if not best_candidates:
                break

    return best_slot_id, best_candidates


def schedule_types_are_possible(
    person_slots: dict[str, list[int]],
    people: list[str],
    slots: dict[int, str],
    single_participation: list[str],
    only_sunday: list[str],
) -> bool:
    for person in people:
        if not needs_both_slot_types(person, single_participation, only_sunday):
            continue

        slots_list = person_slots.get(person, [])
        max_participation = get_max_participation(person, single_participation)

        if len(slots_list) >= max_participation and not valid_person_slot_types(person, slots_list, slots, single_participation, only_sunday):
            return False

    return True


def final_schedule_types_are_valid(
    person_slots: dict[str, list[int]],
    people: list[str],
    slots: dict[int, str],
    single_participation: list[str],
    only_sunday: list[str],
) -> bool:
    for person in people:
        slots_list = person_slots.get(person, [])

        if slots_list and not valid_person_slot_types(person, slots_list, slots, single_participation, only_sunday):
            return False

    return True


def fill_schedule_recursive(
    schedule: dict[int, list[str]],
    person_slots: dict[str, list[int]],
    people: list[str],
    slots: dict[int, str],
    slot_limits: dict[int, int],
    blocked_start: list[str],
    single_participation: list[str],
    only_sunday: list[str],
) -> bool:
    slot_id, candidates = find_next_slot(
        schedule,
        person_slots,
        people,
        slots,
        slot_limits,
        blocked_start,
        single_participation,
        only_sunday,
    )

    if slot_id is None:
        return final_schedule_types_are_valid(person_slots, people, slots, single_participation, only_sunday)

    if not candidates:
        return False

    for person in candidates:
        schedule[slot_id].append(person)
        person_slots[person].append(slot_id)

        if (
            schedule_types_are_possible(person_slots, people, slots, single_participation, only_sunday)
            and fill_schedule_recursive(schedule, person_slots, people, slots, slot_limits, blocked_start, single_participation, only_sunday)
        ):
            return True

        schedule[slot_id].pop()
        person_slots[person].pop()

    return False


def build_schedule(
    people: list[str],
    slots: dict[int, str],
    limits: dict[str, int],
    blocked_start: list[str],
    single_participation: list[str],
    only_sunday: list[str],
    seed: int,
) -> tuple[dict[int, list[str]], dict[str, list[int]], dict[int, int]]:
    base_slot_limits = get_base_slot_limits(slots, limits)
    variants = [base_slot_limits]

    for slot_id, value in base_slot_limits.items():
        if value <= 0:
            continue

        variant = base_slot_limits.copy()
        variant[slot_id] -= 1
        variants.append(variant)

    for slot_limits in variants:
        success, schedule, person_slots = try_build_schedule_by_person_options(
            people,
            slots,
            slot_limits,
            blocked_start,
            single_participation,
            only_sunday,
            seed,
        )

        if success:
            return schedule, person_slots, slot_limits

        schedule = create_empty_schedule(slots)
        person_slots = create_empty_person_slots(people)

        if fill_schedule_recursive(
            schedule,
            person_slots,
            people,
            slots,
            slot_limits,
            blocked_start,
            single_participation,
            only_sunday,
        ):
            return schedule, person_slots, slot_limits

    return create_empty_schedule(slots), create_empty_person_slots(people), base_slot_limits


def validate_schedule(
    schedule: dict[int, list[str]],
    person_slots: dict[str, list[int]],
    slots: dict[int, str],
    limits: dict[str, int],
    blocked_start: list[str],
    single_participation: list[str],
    only_sunday: list[str],
) -> list[str]:
    errors = []

    for slot_id, people in schedule.items():
        slot_type = slots[slot_id]
        expected = int(limits[slot_type])

        if len(people) != expected:
            errors.append(f"Слот {slot_id}: назначено {len(people)} из {expected}")

        if len(people) != len(set(people)):
            errors.append(f"Слот {slot_id}: есть повтор участника")

        for person in people:
            if person in blocked_start and slot_id in [1, 2]:
                errors.append(f"{person}: запрещен слот {slot_id}")

            if person in only_sunday and slot_type != "sun":
                errors.append(f"{person}: разрешено только воскресенье, найден слот {slot_id}")

    for person, slots_list in person_slots.items():
        sorted_slots = sorted(slots_list)
        max_participation = get_max_participation(person, single_participation)

        if len(sorted_slots) > max_participation:
            errors.append(f"{person}: больше {max_participation} участий")

        if sorted_slots and not valid_person_slot_types(person, sorted_slots, slots, single_participation, only_sunday):
            errors.append(f"{person}: должны быть участия и в пятницу, и в воскресенье")

        for first_index, first_slot in enumerate(sorted_slots):
            for second_slot in sorted_slots[first_index + 1 :]:
                if abs(first_slot - second_slot) < 3:
                    errors.append(f"{person}: нарушен интервал между слотами {first_slot} и {second_slot}")

    return errors


def get_start_capacity_error(people: list[str], slots: dict[int, str], limits: dict[str, int], blocked_start: list[str], only_sunday: list[str]) -> str | None:
    if 1 not in slots or 2 not in slots:
        return None

    needed = int(limits[slots[1]]) + int(limits[slots[2]])
    available = []

    for person in people:
        can_use_start = False

        for slot_id in [1, 2]:
            if person in blocked_start and slot_id in [1, 2]:
                continue

            if person in only_sunday and slots[slot_id] != "sun":
                continue

            can_use_start = True

        if can_use_start:
            available.append(person)

    if len(available) >= needed:
        return None

    return f"Слоты 1 и 2 требуют {needed} разных участников, доступно только {len(available)}: {', '.join(available)}"


def generate(settings: dict[str, Any], year: int, month: int) -> ScheduleResult:
    slots, slot_dates = build_month_slots(year, month, settings.get("extraDates", {}))
    seed = zlib.crc32(f"{year:04d}-{month:02d}".encode("utf-8"))
    schedule, person_slots, resolved_slot_limits = build_schedule(
        settings["people"],
        slots,
        settings["limits"],
        settings["blockedStart"],
        settings["singleParticipation"],
        settings["onlySunday"],
        seed,
    )
    errors = validate_schedule(
        schedule,
        person_slots,
        slots,
        settings["limits"],
        settings["blockedStart"],
        settings["singleParticipation"],
        settings["onlySunday"],
    )
    start_capacity_error = get_start_capacity_error(
        settings["people"],
        slots,
        settings["limits"],
        settings["blockedStart"],
        settings["onlySunday"],
    )

    if start_capacity_error:
        errors.append(start_capacity_error)

    return ScheduleResult(
        year=year,
        month=month,
        slots=slots,
        slot_dates=slot_dates,
        schedule=schedule,
        person_slots=person_slots,
        resolved_slot_limits=resolved_slot_limits,
        errors=errors,
    )

