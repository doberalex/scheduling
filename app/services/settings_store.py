import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from app.config import DATA_FILE


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


def load_settings() -> dict[str, Any]:
    if not DATA_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
        return deepcopy(DEFAULT_SETTINGS)

    with DATA_FILE.open("r", encoding="utf-8") as file:
        return _normalise(json.load(file))


def save_settings(settings: dict[str, Any]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    normalised = _normalise(settings)

    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(normalised, file, ensure_ascii=False, indent=2)
        file.write("\n")


def data_file_path() -> Path:
    return DATA_FILE

