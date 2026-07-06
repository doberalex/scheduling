from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Any

import aiomysql

from app.config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER
from app.services.scheduler import ScheduleResult


DEFAULT_SETTINGS: dict[str, Any] = {
    "people": [
        "Александр Б.",
        "Алексей Б.",
        "Андрей К.",
        "Вадим Б.",
        "Владимир П.",
        "Давид С.",
        "Давид Х.",
        "Дмитрий К.",
        "Махмуд Х.",
        "Петр С.",
        "Рустам М.",
        "Рустем Х.",
        "Александр Т.",
        "Самир Х.",
        "Наиль",
        "Артур Б.",
        "Тимур Х.",
    ],
    "limits": {
        "fri": 3,
        "sun": 5,
    },
    "blockedStart": [
        "Алексей Б.",
        "Андрей К.",
        "Вадим Б.",
        "Владимир П.",
        "Махмуд Х.",
        "Рустам М.",
        "Наиль",
    ],
    "singleParticipation": [
        "Петр С.",
        "Тимур Х.",
    ],
    "onlySunday": [
        "Наиль",
        "Артур Б.",
        "Александр Б.",
    ],
    "extraDates": {
        "fri": [],
        "sun": [],
    },
}

LIST_KEYS = {
    "blockedStart",
    "singleParticipation",
    "onlySunday",
}
SLOT_TYPES = {"fri", "sun"}
SCHEDULE_STATUSES = {"published", "unpublished"}
ATTENDANCE_STATUSES = {"planned", "attended", "missed"}

pool: aiomysql.Pool | None = None


def _normalise(settings: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(DEFAULT_SETTINGS)
    result.update(settings)

    result["limits"] = {**DEFAULT_SETTINGS["limits"], **settings.get("limits", {})}
    result["extraDates"] = {
        **DEFAULT_SETTINGS["extraDates"],
        **settings.get("extraDates", {}),
    }

    for key in ["people", "blockedStart", "singleParticipation", "onlySunday"]:
        result[key] = list(dict.fromkeys(result.get(key, [])))

    for key in ["fri", "sun"]:
        result["extraDates"][key] = sorted(set(result["extraDates"].get(key, [])))

    return result


async def connect_db() -> aiomysql.Pool:
    global pool

    if pool is None:
        pool = await aiomysql.create_pool(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            db=DB_NAME,
            charset="utf8mb4",
            autocommit=True,
        )

    return pool


async def close_db() -> None:
    global pool

    if pool is None:
        return

    pool.close()
    await pool.wait_closed()
    pool = None


async def init_db() -> None:
    db_pool = await connect_db()

    async with db_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SET sql_notes=0")
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS schedule_participants (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
                    name VARCHAR(255) NOT NULL,
                    is_active TINYINT NOT NULL DEFAULT 1,
                    sort_order INT NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    UNIQUE KEY uniq_schedule_participants_name (name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS schedule_limits (
                    slot_type VARCHAR(16) NOT NULL,
                    limit_value INT NOT NULL,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (slot_type)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS schedule_participant_lists (
                    list_key VARCHAR(64) NOT NULL,
                    participant_id INT UNSIGNED NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (list_key, participant_id),
                    CONSTRAINT fk_schedule_lists_participant
                        FOREIGN KEY (participant_id)
                        REFERENCES schedule_participants (id)
                        ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS schedule_extra_dates (
                    slot_type VARCHAR(16) NOT NULL,
                    date_value DATE NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (slot_type, date_value)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS schedule_months (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
                    year_value INT NOT NULL,
                    month_value INT NOT NULL,
                    status VARCHAR(32) NOT NULL DEFAULT 'unpublished',
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    UNIQUE KEY uniq_schedule_month (year_value, month_value)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS schedule_slots (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
                    schedule_id INT UNSIGNED NOT NULL,
                    slot_no INT NOT NULL,
                    slot_type VARCHAR(16) NOT NULL,
                    date_value DATE NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    UNIQUE KEY uniq_schedule_slot (schedule_id, slot_no),
                    CONSTRAINT fk_schedule_slots_month
                        FOREIGN KEY (schedule_id)
                        REFERENCES schedule_months (id)
                        ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS schedule_slot_participants (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
                    slot_id INT UNSIGNED NOT NULL,
                    participant_id INT UNSIGNED NOT NULL,
                    is_scheduled TINYINT NOT NULL DEFAULT 1,
                    attendance_status VARCHAR(32) NOT NULL DEFAULT 'planned',
                    sort_order INT NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    UNIQUE KEY uniq_slot_participant (slot_id, participant_id),
                    CONSTRAINT fk_slot_participants_slot
                        FOREIGN KEY (slot_id)
                        REFERENCES schedule_slots (id)
                        ON DELETE CASCADE,
                    CONSTRAINT fk_slot_participants_person
                        FOREIGN KEY (participant_id)
                        REFERENCES schedule_participants (id)
                        ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            await cursor.execute("SET sql_notes=1")
            await cursor.execute("SELECT COUNT(*) FROM schedule_participants")
            row = await cursor.fetchone()

    if row and row[0] == 0:
        await save_settings(DEFAULT_SETTINGS)


async def _participant_id(cursor: aiomysql.Cursor, name: str) -> int:
    await cursor.execute("SELECT id FROM schedule_participants WHERE name=%s", (name,))
    row = await cursor.fetchone()

    if row:
        return int(row[0])

    await cursor.execute(
        "INSERT INTO schedule_participants (name, is_active) VALUES (%s, 1)",
        (name,),
    )
    return int(cursor.lastrowid)


async def _schedule_id(cursor: aiomysql.Cursor, year: int, month: int) -> int | None:
    await cursor.execute(
        "SELECT id FROM schedule_months WHERE year_value=%s AND month_value=%s",
        (year, month),
    )
    row = await cursor.fetchone()
    return int(row[0]) if row else None


async def _slot_id(cursor: aiomysql.Cursor, schedule_id: int, slot_no: int) -> int | None:
    await cursor.execute(
        "SELECT id FROM schedule_slots WHERE schedule_id=%s AND slot_no=%s",
        (schedule_id, slot_no),
    )
    row = await cursor.fetchone()
    return int(row[0]) if row else None


def _parse_date_text(value: str) -> date:
    day, month, year = value.split(".")
    return date(int(year), int(month), int(day))


async def load_settings() -> dict[str, Any]:
    await init_db()
    db_pool = await connect_db()
    settings = {
        "people": [],
        "limits": {},
        "blockedStart": [],
        "singleParticipation": [],
        "onlySunday": [],
        "extraDates": {"fri": [], "sun": []},
    }

    async with db_pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(
                """
                SELECT name
                FROM schedule_participants
                WHERE is_active=1
                ORDER BY sort_order, id
                """
            )
            settings["people"] = [row["name"] for row in await cursor.fetchall()]

            await cursor.execute("SELECT slot_type, limit_value FROM schedule_limits")
            settings["limits"] = {
                row["slot_type"]: int(row["limit_value"])
                for row in await cursor.fetchall()
                if row["slot_type"] in SLOT_TYPES
            }

            await cursor.execute(
                """
                SELECT l.list_key, p.name
                FROM schedule_participant_lists l
                INNER JOIN schedule_participants p ON p.id = l.participant_id
                WHERE p.is_active=1
                ORDER BY p.sort_order, p.id
                """
            )

            for row in await cursor.fetchall():
                if row["list_key"] in LIST_KEYS:
                    settings[row["list_key"]].append(row["name"])

            await cursor.execute(
                """
                SELECT slot_type, DATE_FORMAT(date_value, '%%d.%%m.%%Y') AS date_text
                FROM schedule_extra_dates
                ORDER BY date_value, slot_type
                """
            )

            for row in await cursor.fetchall():
                if row["slot_type"] in SLOT_TYPES:
                    settings["extraDates"][row["slot_type"]].append(row["date_text"])

    return _normalise(settings)


async def save_settings(settings: dict[str, Any]) -> None:
    settings = _normalise(settings)
    db_pool = await connect_db()

    async with db_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("UPDATE schedule_participants SET is_active=0")

            for index, name in enumerate(settings["people"], start=1):
                await cursor.execute(
                    """
                    INSERT INTO schedule_participants (name, is_active, sort_order)
                    VALUES (%s, 1, %s)
                    ON DUPLICATE KEY UPDATE
                        is_active=1,
                        sort_order=VALUES(sort_order)
                    """,
                    (name, index),
                )

            await cursor.execute("DELETE FROM schedule_participant_lists")

            for list_key in LIST_KEYS:
                for name in settings[list_key]:
                    if name not in settings["people"]:
                        continue

                    participant_id = await _participant_id(cursor, name)
                    await cursor.execute(
                        """
                        INSERT IGNORE INTO schedule_participant_lists (list_key, participant_id)
                        VALUES (%s, %s)
                        """,
                        (list_key, participant_id),
                    )

            await cursor.execute("DELETE FROM schedule_limits")

            for slot_type, value in settings["limits"].items():
                if slot_type not in SLOT_TYPES:
                    continue

                await cursor.execute(
                    """
                    INSERT INTO schedule_limits (slot_type, limit_value)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE limit_value=VALUES(limit_value)
                    """,
                    (slot_type, int(value)),
                )

            await cursor.execute("DELETE FROM schedule_extra_dates")

            for slot_type in SLOT_TYPES:
                for date_text in settings["extraDates"][slot_type]:
                    await cursor.execute(
                        """
                        INSERT IGNORE INTO schedule_extra_dates (slot_type, date_value)
                        VALUES (%s, STR_TO_DATE(%s, '%%d.%%m.%%Y'))
                        """,
                        (slot_type, date_text),
                    )


async def save_schedule_result(result: ScheduleResult) -> None:
    await init_db()
    db_pool = await connect_db()

    async with db_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO schedule_months (year_value, month_value, status)
                VALUES (%s, %s, 'unpublished')
                ON DUPLICATE KEY UPDATE updated_at=CURRENT_TIMESTAMP
                """,
                (result.year, result.month),
            )
            schedule_id = await _schedule_id(cursor, result.year, result.month)
            if schedule_id is None:
                return

            await cursor.execute("DELETE FROM schedule_slots WHERE schedule_id=%s", (schedule_id,))

            for slot_no, slot_type in result.slots.items():
                await cursor.execute(
                    """
                    INSERT INTO schedule_slots (schedule_id, slot_no, slot_type, date_value)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (schedule_id, slot_no, slot_type, _parse_date_text(result.slot_dates[slot_no])),
                )
                slot_id = int(cursor.lastrowid)

                for sort_order, name in enumerate(result.schedule.get(slot_no, []), start=1):
                    participant_id = await _participant_id(cursor, name)
                    await cursor.execute(
                        """
                        INSERT INTO schedule_slot_participants
                            (slot_id, participant_id, is_scheduled, attendance_status, sort_order)
                        VALUES (%s, %s, 1, 'planned', %s)
                        """,
                        (slot_id, participant_id, sort_order),
                    )


async def get_saved_schedule(year: int, month: int) -> dict[str, Any] | None:
    await init_db()
    db_pool = await connect_db()

    async with db_pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(
                """
                SELECT id, status
                FROM schedule_months
                WHERE year_value=%s AND month_value=%s
                """,
                (year, month),
            )
            schedule = await cursor.fetchone()

            if not schedule:
                return None

            await cursor.execute(
                """
                SELECT
                    s.id AS slot_id,
                    s.slot_no,
                    s.slot_type,
                    DATE_FORMAT(s.date_value, '%%d.%%m.%%Y') AS date_text,
                    p.name,
                    sp.is_scheduled,
                    sp.attendance_status,
                    sp.sort_order
                FROM schedule_slots s
                LEFT JOIN schedule_slot_participants sp ON sp.slot_id = s.id
                LEFT JOIN schedule_participants p ON p.id = sp.participant_id
                WHERE s.schedule_id=%s
                ORDER BY s.slot_no, sp.is_scheduled DESC, sp.sort_order, p.name
                """,
                (schedule["id"],),
            )
            rows = await cursor.fetchall()

    slots: dict[int, dict[str, Any]] = {}

    for row in rows:
        slot_no = int(row["slot_no"])
        slots.setdefault(
            slot_no,
            {
                "slot_no": slot_no,
                "slot_type": row["slot_type"],
                "date": row["date_text"],
                "participants": [],
            },
        )

        if row["name"]:
            slots[slot_no]["participants"].append(
                {
                    "name": row["name"],
                    "is_scheduled": bool(row["is_scheduled"]),
                    "attendance_status": row["attendance_status"],
                }
            )

    return {
        "id": int(schedule["id"]),
        "year": year,
        "month": month,
        "status": schedule["status"],
        "slots": [slots[key] for key in sorted(slots)],
    }


async def set_schedule_status(year: int, month: int, status: str) -> bool:
    if status not in SCHEDULE_STATUSES:
        return False

    await init_db()
    db_pool = await connect_db()

    async with db_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            schedule_id = await _schedule_id(cursor, year, month)
            if schedule_id is None:
                return False

            await cursor.execute(
                "UPDATE schedule_months SET status=%s WHERE id=%s",
                (status, schedule_id),
            )

    return True


async def replace_slot_participants(year: int, month: int, slot_no: int, names: list[str]) -> bool:
    await init_db()
    names = list(dict.fromkeys(names))
    db_pool = await connect_db()

    async with db_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            schedule_id = await _schedule_id(cursor, year, month)
            if schedule_id is None:
                return False

            slot_id = await _slot_id(cursor, schedule_id, slot_no)
            if slot_id is None:
                return False

            await cursor.execute(
                "DELETE FROM schedule_slot_participants WHERE slot_id=%s AND is_scheduled=1",
                (slot_id,),
            )

            for sort_order, name in enumerate(names, start=1):
                participant_id = await _participant_id(cursor, name)
                await cursor.execute(
                    """
                    INSERT INTO schedule_slot_participants
                        (slot_id, participant_id, is_scheduled, attendance_status, sort_order)
                    VALUES (%s, %s, 1, 'planned', %s)
                    ON DUPLICATE KEY UPDATE
                        is_scheduled=1,
                        attendance_status='planned',
                        sort_order=VALUES(sort_order)
                    """,
                    (slot_id, participant_id, sort_order),
                )

    return True


async def set_slot_participant_attendance(
    year: int,
    month: int,
    slot_no: int,
    name: str,
    status: str,
) -> bool:
    if status not in ATTENDANCE_STATUSES:
        return False

    await init_db()
    db_pool = await connect_db()

    async with db_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            schedule_id = await _schedule_id(cursor, year, month)
            if schedule_id is None:
                return False

            slot_id = await _slot_id(cursor, schedule_id, slot_no)
            if slot_id is None:
                return False

            await cursor.execute(
                """
                UPDATE schedule_slot_participants sp
                INNER JOIN schedule_participants p ON p.id = sp.participant_id
                SET sp.attendance_status=%s
                WHERE sp.slot_id=%s AND p.name=%s
                """,
                (status, slot_id, name),
            )

    return True


async def add_extra_slot_participant(year: int, month: int, slot_no: int, name: str) -> bool:
    await init_db()
    db_pool = await connect_db()

    async with db_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            schedule_id = await _schedule_id(cursor, year, month)
            if schedule_id is None:
                return False

            slot_id = await _slot_id(cursor, schedule_id, slot_no)
            if slot_id is None:
                return False

            participant_id = await _participant_id(cursor, name)
            await cursor.execute(
                "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM schedule_slot_participants WHERE slot_id=%s",
                (slot_id,),
            )
            row = await cursor.fetchone()
            sort_order = int(row[0] or 1)

            await cursor.execute(
                """
                INSERT INTO schedule_slot_participants
                    (slot_id, participant_id, is_scheduled, attendance_status, sort_order)
                VALUES (%s, %s, 0, 'attended', %s)
                ON DUPLICATE KEY UPDATE
                    is_scheduled=0,
                    attendance_status='attended',
                    sort_order=VALUES(sort_order)
                """,
                (slot_id, participant_id, sort_order),
            )

    return True


async def previous_month_blocked_start(year: int, month: int) -> list[str]:
    previous_year = year
    previous_month = month - 1

    if previous_month == 0:
        previous_month = 12
        previous_year -= 1

    saved = await get_saved_schedule(previous_year, previous_month)

    if not saved:
        return []

    blocked = []

    for slot in saved["slots"][-2:]:
        for participant in slot["participants"]:
            if participant["attendance_status"] == "attended":
                blocked.append(participant["name"])

    return list(dict.fromkeys(blocked))


async def init_db_if_needed() -> None:
    db_pool = await connect_db()

    async with db_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema=%s
                    AND table_name='schedule_participants'
                """,
                (DB_NAME,),
            )
            row = await cursor.fetchone()

    if not row or row[0] == 0:
        await init_db()
