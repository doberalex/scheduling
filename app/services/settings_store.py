from __future__ import annotations

from copy import deepcopy
from typing import Any

import aiomysql

from app.config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER


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
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS schedule_participants (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
                    name VARCHAR(255) NOT NULL,
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
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
