from __future__ import annotations

from datetime import datetime
from typing import Callable

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.config import ADMIN_IDS
from app.keyboards.main_keyboard import main_keyboard
from app.services.formatters import format_schedule, format_settings
from app.services.scheduler import generate, parse_date
from app.services.settings_store import data_file_path, load_settings, save_settings


router = Router()
pending_actions: dict[int, str] = {}


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def require_admin(message: Message) -> bool:
    return bool(message.from_user and is_admin(message.from_user.id))


async def answer_menu(message: Message, text: str) -> None:
    user_id = message.from_user.id if message.from_user else 0
    await message.answer(text, reply_markup=main_keyboard(is_admin(user_id)))


def normalise_name(value: str) -> str:
    return " ".join(value.strip().split())


def parse_month_args(text: str) -> tuple[int, int]:
    parts = text.split()
    now = datetime.now()

    if len(parts) == 1:
        return now.year, now.month

    if len(parts) == 2 and "." in parts[1]:
        month_text, year_text = parts[1].split(".", 1)
        return int(year_text), int(month_text)

    if len(parts) >= 3:
        return int(parts[2]), int(parts[1])

    return now.year, now.month


async def show_schedule(message: Message, year: int | None = None, month: int | None = None) -> None:
    now = datetime.now()
    settings = load_settings()
    result = generate(settings, year or now.year, month or now.month)

    await message.answer(format_schedule(result))


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    await answer_menu(
        message,
        "Бот управления расписаниями готов.\n\n"
        "Команды:\n"
        "/schedule - расписание на текущий месяц\n"
        "/schedule 7 2026 - расписание на месяц\n"
        "/settings - настройки\n"
        "/help - справка",
    )


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    await answer_menu(
        message,
        "<b>Управление</b>\n\n"
        "Через кнопки можно добавить или удалить участника, изменить списки blockedStart, "
        "singleParticipation, onlySunday, лимиты пятниц/воскресений и дополнительные даты.\n\n"
        "Текстовые команды администратора:\n"
        "/add_name Имя\n"
        "/remove_name Имя\n"
        "/blocked add Имя | /blocked remove Имя\n"
        "/single add Имя | /single remove Имя\n"
        "/only_sunday add Имя | /only_sunday remove Имя\n"
        "/limit fri 3 | /limit sun 5\n"
        "/extra fri add 15.07.2026 | /extra sun remove 19.07.2026",
    )


@router.message(Command("schedule"))
async def schedule_command(message: Message) -> None:
    try:
        year, month = parse_month_args(message.text or "")
        await show_schedule(message, year, month)
    except (ValueError, IndexError):
        await message.answer("Формат: /schedule или /schedule 7 2026")


@router.message(Command("settings"))
async def settings_command(message: Message) -> None:
    await message.answer(format_settings(load_settings()))


@router.message(Command("participants"))
async def participants_command(message: Message) -> None:
    settings = load_settings()
    await message.answer("<b>Участники</b>\n" + "\n".join(f"• {name}" for name in settings["people"]))


def admin_command(handler: Callable[[Message], None]) -> Callable[[Message], None]:
    async def wrapper(message: Message) -> None:
        if not require_admin(message):
            await message.answer("Нет доступа.")
            return

        await handler(message)

    return wrapper


@router.message(Command("add_name"))
@admin_command
async def add_name_command(message: Message) -> None:
    name = normalise_name((message.text or "").replace("/add_name", "", 1))
    await add_person(message, name)


@router.message(Command("remove_name"))
@admin_command
async def remove_name_command(message: Message) -> None:
    name = normalise_name((message.text or "").replace("/remove_name", "", 1))
    await remove_person(message, name)


@router.message(Command("blocked"))
@admin_command
async def blocked_command(message: Message) -> None:
    await update_named_list_from_command(message, "blockedStart", "/blocked")


@router.message(Command("single"))
@admin_command
async def single_command(message: Message) -> None:
    await update_named_list_from_command(message, "singleParticipation", "/single")


@router.message(Command("only_sunday"))
@admin_command
async def only_sunday_command(message: Message) -> None:
    await update_named_list_from_command(message, "onlySunday", "/only_sunday")


@router.message(Command("limit"))
@admin_command
async def limit_command(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=2)

    if len(parts) != 3 or parts[1] not in {"fri", "sun"}:
        await message.answer("Формат: /limit fri 3 или /limit sun 5")
        return

    try:
        value = int(parts[2])
    except ValueError:
        await message.answer("Лимит должен быть числом.")
        return

    if value < 0 or value > 20:
        await message.answer("Лимит должен быть от 0 до 20.")
        return

    settings = load_settings()
    settings["limits"][parts[1]] = value
    save_settings(settings)
    await message.answer("Лимит обновлен.")


@router.message(Command("extra"))
@admin_command
async def extra_command(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=3)

    if len(parts) != 4 or parts[1] not in {"fri", "sun"} or parts[2] not in {"add", "remove"}:
        await message.answer("Формат: /extra fri add 15.07.2026 или /extra sun remove 19.07.2026")
        return

    await update_extra_date(message, parts[1], parts[2], parts[3])


@router.message(F.text == "Расписание")
async def schedule_button(message: Message) -> None:
    await show_schedule(message)


@router.message(F.text == "Настройки")
async def settings_button(message: Message) -> None:
    await message.answer(format_settings(load_settings()))


@router.message(F.text == "Участники")
async def participants_button(message: Message) -> None:
    settings = load_settings()
    await message.answer("<b>Участники</b>\n" + "\n".join(f"• {name}" for name in settings["people"]))


@router.message(F.text == "Помощь")
async def help_button(message: Message) -> None:
    await help_handler(message)


@router.message(F.text.in_({"Добавить участника", "Удалить участника", "Списки ограничений", "Лимиты", "Доп. даты"}))
async def admin_button(message: Message) -> None:
    if not require_admin(message):
        await message.answer("Нет доступа.")
        return

    prompts = {
        "Добавить участника": ("add_person", "Введите имя участника."),
        "Удалить участника": ("remove_person", "Введите имя участника для удаления."),
        "Списки ограничений": (
            "list_update",
            "Введите действие в формате:\n"
            "blocked add Имя\n"
            "blocked remove Имя\n"
            "single add Имя\n"
            "only_sunday add Имя",
        ),
        "Лимиты": ("limit_update", "Введите лимит в формате: fri 3 или sun 5."),
        "Доп. даты": ("extra_update", "Введите дату в формате: fri add 15.07.2026 или sun remove 19.07.2026."),
    }
    action, prompt = prompts[message.text]
    pending_actions[message.from_user.id] = action
    await message.answer(prompt)


@router.message(F.text == "Отмена")
async def cancel_button(message: Message) -> None:
    if message.from_user:
        pending_actions.pop(message.from_user.id, None)

    await answer_menu(message, "Действие отменено.")


@router.message()
async def text_handler(message: Message) -> None:
    if not message.from_user:
        return

    action = pending_actions.pop(message.from_user.id, None)

    if not action:
        await answer_menu(message, "Выберите действие на клавиатуре или используйте /help.")
        return

    if not require_admin(message):
        await message.answer("Нет доступа.")
        return

    text = message.text or ""

    if action == "add_person":
        await add_person(message, normalise_name(text))
    elif action == "remove_person":
        await remove_person(message, normalise_name(text))
    elif action == "list_update":
        await update_list_from_text(message, text)
    elif action == "limit_update":
        await update_limit_from_text(message, text)
    elif action == "extra_update":
        await update_extra_from_text(message, text)


async def add_person(message: Message, name: str) -> None:
    if not name:
        await message.answer("Имя не указано.")
        return

    settings = load_settings()

    if name in settings["people"]:
        await message.answer("Такой участник уже есть.")
        return

    settings["people"].append(name)
    save_settings(settings)
    await message.answer(f"Участник добавлен: {name}")


async def remove_person(message: Message, name: str) -> None:
    settings = load_settings()

    if name not in settings["people"]:
        await message.answer("Такого участника нет.")
        return

    settings["people"].remove(name)

    for key in ["blockedStart", "singleParticipation", "onlySunday"]:
        settings[key] = [value for value in settings[key] if value != name]

    save_settings(settings)
    await message.answer(f"Участник удален: {name}")


async def update_named_list_from_command(message: Message, key: str, command: str) -> None:
    text = (message.text or "").replace(command, "", 1).strip()
    parts = text.split(maxsplit=1)

    if len(parts) != 2 or parts[0] not in {"add", "remove"}:
        await message.answer(f"Формат: {command} add Имя или {command} remove Имя")
        return

    await update_named_list(message, key, parts[0], normalise_name(parts[1]))


async def update_list_from_text(message: Message, text: str) -> None:
    parts = text.split(maxsplit=2)
    key_map = {
        "blocked": "blockedStart",
        "single": "singleParticipation",
        "only_sunday": "onlySunday",
    }

    if len(parts) != 3 or parts[0] not in key_map or parts[1] not in {"add", "remove"}:
        await message.answer("Формат: blocked add Имя, single remove Имя, only_sunday add Имя")
        return

    await update_named_list(message, key_map[parts[0]], parts[1], normalise_name(parts[2]))


async def update_named_list(message: Message, key: str, action: str, name: str) -> None:
    if not name:
        await message.answer("Имя не указано.")
        return

    settings = load_settings()

    if name not in settings["people"]:
        await message.answer("Сначала добавьте участника в общий список.")
        return

    if action == "add":
        if name not in settings[key]:
            settings[key].append(name)
        result = "добавлен"
    else:
        settings[key] = [value for value in settings[key] if value != name]
        result = "удален"

    save_settings(settings)
    await message.answer(f"{name} {result} в {key}.")


async def update_limit_from_text(message: Message, text: str) -> None:
    parts = text.split(maxsplit=1)

    if len(parts) != 2 or parts[0] not in {"fri", "sun"}:
        await message.answer("Формат: fri 3 или sun 5.")
        return

    try:
        value = int(parts[1])
    except ValueError:
        await message.answer("Лимит должен быть числом.")
        return

    settings = load_settings()
    settings["limits"][parts[0]] = value
    save_settings(settings)
    await message.answer("Лимит обновлен.")


async def update_extra_from_text(message: Message, text: str) -> None:
    parts = text.split(maxsplit=2)

    if len(parts) != 3 or parts[0] not in {"fri", "sun"} or parts[1] not in {"add", "remove"}:
        await message.answer("Формат: fri add 15.07.2026 или sun remove 19.07.2026.")
        return

    await update_extra_date(message, parts[0], parts[1], parts[2])


async def update_extra_date(message: Message, slot_type: str, action: str, value: str) -> None:
    try:
        parsed = parse_date(value)
    except ValueError as error:
        await message.answer(str(error))
        return

    date_value = parsed.strftime("%d.%m.%Y")
    settings = load_settings()
    values = settings["extraDates"][slot_type]

    if action == "add":
        if date_value not in values:
            values.append(date_value)
        result = "добавлена"
    else:
        settings["extraDates"][slot_type] = [item for item in values if item != date_value]
        result = "удалена"

    save_settings(settings)
    await message.answer(f"Дата {date_value} {result}.")

