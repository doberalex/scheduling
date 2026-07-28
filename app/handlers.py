from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from app.config import ADMIN_IDS
from app.keyboards.main_keyboard import (
    main_keyboard,
    participants_menu_keyboard,
    schedule_keyboard,
    settings_menu_keyboard,
)
from app.services.formatters import format_saved_schedule, format_schedule, format_settings
from app.services.scheduler import generate, parse_date
from app.services.settings_store import (
    add_extra_slot_participant,
    get_saved_schedule,
    load_settings,
    previous_month_blocked_start,
    previous_month_participation_counts,
    replace_slot_participants,
    save_schedule_result,
    save_settings,
    set_schedule_status,
    set_slot_participant_attendance,
)


router = Router()
pending_actions: dict[int, dict[str, Any]] = {}
last_month_by_user: dict[int, tuple[int, int]] = {}


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def require_admin(message: Message) -> bool:
    return bool(message.from_user and is_admin(message.from_user.id))


def normalise_name(value: str) -> str:
    return " ".join(value.strip().split())


def sort_names(values: list[str]) -> list[str]:
    return sorted(values, key=str.casefold)


def now_month() -> tuple[int, int]:
    now = datetime.now()
    return now.year, now.month


def next_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1

    return year, month + 1


def month_label(year: int, month: int) -> str:
    return f"{month:02d}.{year}"


def set_last_month(message: Message, year: int, month: int) -> None:
    if message.from_user:
        last_month_by_user[message.from_user.id] = (year, month)


def get_last_month(message: Message) -> tuple[int, int]:
    if message.from_user and message.from_user.id in last_month_by_user:
        return last_month_by_user[message.from_user.id]

    return now_month()


def simple_keyboard(rows: list[list[str]]) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=value) for value in row] for row in rows],
        resize_keyboard=True,
    )


def month_choice_keyboard() -> ReplyKeyboardMarkup:
    current_year, current_month = now_month()
    next_year, next_month_value = next_month(current_year, current_month)
    return simple_keyboard(
        [
            [f"📍 Текущий месяц {month_label(current_year, current_month)}"],
            [f"➡️ Следующий месяц {month_label(next_year, next_month_value)}"],
            ["🚫 Отмена"],
            ["🏠 Главное меню"],
        ]
    )


async def answer_menu(message: Message, text: str) -> None:
    user_id = message.from_user.id if message.from_user else 0
    await message.answer(text, reply_markup=main_keyboard(is_admin(user_id)))


async def answer_schedule_menu(message: Message, text: str) -> None:
    await message.answer(text, reply_markup=schedule_keyboard(require_admin(message)))


async def answer_participants_menu(message: Message, text: str) -> None:
    await message.answer(text, reply_markup=participants_menu_keyboard(require_admin(message)))


async def answer_settings_menu(message: Message, text: str) -> None:
    await message.answer(text, reply_markup=settings_menu_keyboard(require_admin(message)))


def parse_month_args(text: str) -> tuple[int, int]:
    parts = text.split()

    if len(parts) == 1:
        return now_month()

    if len(parts) == 2 and "." in parts[1]:
        month_text, year_text = parts[1].split(".", 1)
        return int(year_text), int(month_text)

    if len(parts) >= 3:
        return int(parts[2]), int(parts[1])

    return now_month()


async def settings_for_month(year: int, month: int) -> dict:
    settings = await load_settings()
    auto_blocked = await previous_month_blocked_start(year, month)
    previous_counts = await previous_month_participation_counts(year, month)

    if auto_blocked:
        settings["blockedStart"] = auto_blocked

    settings["previousParticipationCounts"] = previous_counts

    return settings


async def generated_schedule(year: int, month: int):
    settings = await settings_for_month(year, month)
    return generate(settings, year, month)


async def ensure_saved_schedule(year: int, month: int) -> tuple[dict[str, Any] | None, bool]:
    saved = await get_saved_schedule(year, month)

    if saved:
        return saved, False

    result = await generated_schedule(year, month)
    await save_schedule_result(result)
    return await get_saved_schedule(year, month), True


async def show_schedule(message: Message, year: int | None = None, month: int | None = None) -> None:
    year = year or now_month()[0]
    month = month or now_month()[1]
    set_last_month(message, year, month)
    saved = await get_saved_schedule(year, month)

    if saved:
        await message.answer(format_saved_schedule(saved), reply_markup=schedule_keyboard(require_admin(message)))
        return

    result = await generated_schedule(year, month)
    await message.answer(format_schedule(result), reply_markup=schedule_keyboard(require_admin(message)))


async def ask_month(message: Message, action: str, prompt: str = "Выберите месяц:") -> None:
    if not message.from_user:
        return

    pending_actions[message.from_user.id] = {"action": "choose_month", "next_action": action}
    await message.answer(prompt, reply_markup=month_choice_keyboard())


def parse_month_choice(text: str) -> tuple[int, int] | None:
    if text.startswith("📍 Текущий месяц"):
        return now_month()

    if text.startswith("➡️ Следующий месяц"):
        current_year, current_month = now_month()
        return next_month(current_year, current_month)

    return None


async def slot_keyboard(year: int, month: int) -> ReplyKeyboardMarkup | None:
    saved = await get_saved_schedule(year, month)

    if not saved:
        return None

    rows = [[f"{slot['slot_no']}. {slot['date']}"] for slot in saved["slots"]]
    rows.append(["🚫 Отмена"])
    return simple_keyboard(rows)


def parse_slot_no(text: str) -> int | None:
    try:
        return int(text.split(".", 1)[0])
    except (ValueError, IndexError):
        return None


def participants_keyboard(people: list[str], include_done: bool = False) -> ReplyKeyboardMarkup:
    rows = [[name] for name in sort_names(people)]

    if include_done:
        rows.append(["✅ Готово"])

    rows.append(["🚫 Отмена"])
    return simple_keyboard(rows)


def limit_type_keyboard() -> ReplyKeyboardMarkup:
    return simple_keyboard(
        [
            ["🍞 Пятница", "☀️ Воскресенье"],
            ["🚫 Отмена"],
            ["🏠 Главное меню"],
        ]
    )


def limit_value_keyboard() -> ReplyKeyboardMarkup:
    return simple_keyboard(
        [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["🚫 Отмена"],
            ["🏠 Главное меню"],
        ]
    )


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    await answer_menu(
        message,
        "Бот управления расписаниями готов.\n\n"
        "Выберите раздел на клавиатуре.",
    )


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    await answer_menu(
        message,
        "<b>Управление</b>\n\n"
        "📅 График — просмотр, сохранение, публикация и отметки участия.\n"
        "👥 Участники — список, добавление и удаление.\n"
        "⚙️ Настройки — ограничения, лимиты и дополнительные даты.\n"
        "🏠 Главное меню — выход из любого раздела.",
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
    await message.answer(format_settings(await load_settings()))


@router.message(Command("participants"))
async def participants_command(message: Message) -> None:
    settings = await load_settings()
    await message.answer("<b>Участники</b>\n" + "\n".join(f"• {name}" for name in sort_names(settings["people"])))


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


@router.message(F.text.in_({"📅 График", "Расписание"}))
async def schedule_menu_button(message: Message) -> None:
    await answer_schedule_menu(message, "Раздел графика.")


@router.message(F.text == "📆 Показать график")
async def schedule_button(message: Message) -> None:
    await ask_month(message, "show_schedule")


@router.message(F.text == "➡️ Следующий месяц")
async def next_month_button(message: Message) -> None:
    year, month = next_month(*now_month())
    await show_schedule(message, year, month)


@router.message(F.text.in_({"⚙️ Настройки", "Настройки"}))
async def settings_menu_button(message: Message) -> None:
    await answer_settings_menu(message, "Раздел настроек.")


@router.message(F.text.in_({"📋 Показать настройки"}))
async def settings_button(message: Message) -> None:
    await message.answer(format_settings(await load_settings()), reply_markup=settings_menu_keyboard(require_admin(message)))


@router.message(F.text.in_({"👥 Участники", "Участники"}))
async def participants_menu_button(message: Message) -> None:
    await answer_participants_menu(message, "Раздел участников.")


@router.message(F.text.in_({"📋 Список участников"}))
async def participants_button(message: Message) -> None:
    settings = await load_settings()
    await message.answer(
        "<b>Участники</b>\n" + "\n".join(f"• {name}" for name in sort_names(settings["people"])),
        reply_markup=participants_menu_keyboard(require_admin(message)),
    )


@router.message(F.text.in_({"❓ Помощь", "Помощь"}))
async def help_button(message: Message) -> None:
    await help_handler(message)


@router.message(F.text == "💾 Сохранить график")
async def save_schedule_button(message: Message) -> None:
    if not require_admin(message):
        await message.answer("Нет доступа.")
        return

    await ask_month(message, "save_schedule", "Какой месяц сохранить?")


@router.message(F.text == "🔄 Пересохранить месяц")
async def resave_schedule_button(message: Message) -> None:
    if not require_admin(message):
        await message.answer("Нет доступа.")
        return

    await ask_month(message, "resave_schedule", "Какой месяц полностью пересохранить?")


async def save_schedule_for_month(message: Message, year: int, month: int, resave: bool = False) -> None:
    result = await generated_schedule(year, month)
    await save_schedule_result(result)
    saved = await get_saved_schedule(year, month)
    set_last_month(message, year, month)
    prefix = "График полностью пересохранён." if resave else "График сохранён."
    await message.answer(
        prefix + "\n\n" + format_saved_schedule(saved),
        reply_markup=schedule_keyboard(True),
    )


@router.message(F.text.in_({"📣 Опубликовать", "📝 Не публиковать"}))
async def publish_button(message: Message) -> None:
    if not require_admin(message):
        await message.answer("Нет доступа.")
        return

    status = "published" if message.text == "📣 Опубликовать" else "unpublished"
    await ask_month(
        message,
        "publish_schedule" if status == "published" else "unpublish_schedule",
        "Для какого месяца изменить статус?",
    )


@router.message(F.text == "✏️ Редактировать участие")
async def edit_slot_button(message: Message) -> None:
    await ask_slot_month(message, "replace_slot", "За какой месяц редактировать участие?")


@router.message(F.text == "✅ Отметить участие")
async def attendance_button(message: Message) -> None:
    await ask_slot_month(message, "attendance_slot", "За какой месяц отметить участие?")


@router.message(F.text == "➕ Вне графика")
async def extra_participant_button(message: Message) -> None:
    await ask_slot_month(message, "extra_slot", "За какой месяц добавить вне графика?")


async def ask_slot_month(message: Message, action: str, prompt: str) -> None:
    if not require_admin(message):
        await message.answer("Нет доступа.")
        return

    await ask_month(message, action, prompt)


async def start_slot_action(message: Message, action: str) -> None:
    if not require_admin(message):
        await message.answer("Нет доступа.")
        return

    year, month = get_last_month(message)
    await start_slot_action_for_month(message, action, year, month)


async def start_slot_action_for_month(message: Message, action: str, year: int, month: int) -> None:
    saved, created = await ensure_saved_schedule(year, month)
    keyboard = await slot_keyboard(year, month)

    if saved is None or keyboard is None:
        await message.answer("Не удалось подготовить график для редактирования.", reply_markup=schedule_keyboard(True))
        return

    set_last_month(message, year, month)
    pending_actions[message.from_user.id] = {"action": action, "year": year, "month": month}
    if created:
        await message.answer(
            f"График на {month_label(year, month)} ещё не был сохранён, поэтому я сохранил расчётный вариант.",
            reply_markup=schedule_keyboard(True),
        )
    await message.answer("Выберите дату:", reply_markup=keyboard)


@router.message(F.text.in_({"➕ Добавить участника", "Добавить участника"}))
async def add_person_button(message: Message) -> None:
    if not require_admin(message):
        await message.answer("Нет доступа.")
        return

    pending_actions[message.from_user.id] = {"action": "add_person"}
    await message.answer("Введите имя участника.", reply_markup=simple_keyboard([["🚫 Отмена"], ["🏠 Главное меню"]]))


@router.message(F.text.in_({"🗑 Удалить участника", "Удалить участника"}))
async def remove_person_button(message: Message) -> None:
    if not require_admin(message):
        await message.answer("Нет доступа.")
        return

    settings = await load_settings()
    pending_actions[message.from_user.id] = {"action": "remove_person"}
    await message.answer("Выберите участника:", reply_markup=participants_keyboard(settings["people"]))


@router.message(F.text.in_({"📋 Списки ограничений", "Списки ограничений"}))
async def lists_button(message: Message) -> None:
    if not require_admin(message):
        await message.answer("Нет доступа.")
        return

    pending_actions[message.from_user.id] = {"action": "choose_list"}
    await message.answer(
        "Выберите список:",
        reply_markup=simple_keyboard([["singleParticipation"], ["onlySunday"], ["blockedStart"], ["🚫 Отмена"]]),
    )


@router.message(F.text.in_({"🔢 Лимиты", "Лимиты"}))
async def limits_button(message: Message) -> None:
    if not require_admin(message):
        await message.answer("Нет доступа.")
        return

    settings = await load_settings()
    pending_actions[message.from_user.id] = {"action": "limit_type"}
    await message.answer(
        "<b>Текущие лимиты</b>\n"
        f"🍞 Пятница: {settings['limits']['fri']}\n"
        f"☀️ Воскресенье: {settings['limits']['sun']}\n\n"
        "Что изменить?",
        reply_markup=limit_type_keyboard(),
    )


@router.message(F.text.in_({"📆 Доп. даты", "Доп. даты"}))
async def extra_dates_button(message: Message) -> None:
    if not require_admin(message):
        await message.answer("Нет доступа.")
        return

    pending_actions[message.from_user.id] = {"action": "extra_update"}
    await message.answer(
        "Введите дату в формате: fri add 15.07.2026 или sun remove 19.07.2026.",
        reply_markup=simple_keyboard([["🚫 Отмена"], ["🏠 Главное меню"]]),
    )


@router.message(F.text.in_({"🚫 Отмена", "Отмена"}))
async def cancel_button(message: Message) -> None:
    if message.from_user:
        pending_actions.pop(message.from_user.id, None)

    await answer_menu(message, "Действие отменено.")


@router.message(F.text.in_({"🏠 Главное меню", "Главное меню"}))
async def main_menu_button(message: Message) -> None:
    if message.from_user:
        pending_actions.pop(message.from_user.id, None)

    await answer_menu(message, "Главное меню.")


@router.message()
async def text_handler(message: Message) -> None:
    if not message.from_user:
        return

    state = pending_actions.get(message.from_user.id)

    if not state:
        await answer_menu(message, "Выберите действие на клавиатуре или используйте /help.")
        return

    if not require_admin(message):
        await message.answer("Нет доступа.")
        return

    text = message.text or ""
    action = state["action"]

    if action == "choose_month":
        await handle_month_choice(message, state, text)
    elif action == "add_person":
        pending_actions.pop(message.from_user.id, None)
        await add_person(message, normalise_name(text))
    elif action == "remove_person":
        pending_actions.pop(message.from_user.id, None)
        await remove_person(message, normalise_name(text))
    elif action in {"replace_slot", "attendance_slot", "extra_slot"}:
        await handle_slot_selection(message, state, text)
    elif action == "replace_people":
        await handle_replace_people(message, state, text)
    elif action == "attendance_person":
        await handle_attendance_person(message, state, text)
    elif action == "attendance_status":
        await handle_attendance_status(message, state, text)
    elif action == "extra_person":
        await handle_extra_person(message, state, text)
    elif action == "choose_list":
        await handle_choose_list(message, text)
    elif action == "list_action":
        await handle_list_action(message, state, text)
    elif action == "list_person":
        await handle_list_person(message, state, text)
    elif action == "limit_type":
        await handle_limit_type(message, text)
    elif action == "limit_value":
        await handle_limit_value(message, state, text)
    elif action == "limit_update":
        pending_actions.pop(message.from_user.id, None)
        await update_limit_from_text(message, text)
    elif action == "extra_update":
        pending_actions.pop(message.from_user.id, None)
        await update_extra_from_text(message, text)


async def handle_month_choice(message: Message, state: dict[str, Any], text: str) -> None:
    selected = parse_month_choice(text)

    if selected is None:
        await message.answer("Выберите месяц кнопкой.")
        return

    year, month = selected
    next_action = state["next_action"]
    pending_actions.pop(message.from_user.id, None)
    set_last_month(message, year, month)

    if next_action == "show_schedule":
        await show_schedule(message, year, month)
    elif next_action == "save_schedule":
        await save_schedule_for_month(message, year, month)
    elif next_action == "resave_schedule":
        await save_schedule_for_month(message, year, month, resave=True)
    elif next_action == "publish_schedule":
        await update_schedule_status_for_month(message, year, month, "published")
    elif next_action == "unpublish_schedule":
        await update_schedule_status_for_month(message, year, month, "unpublished")
    elif next_action in {"replace_slot", "attendance_slot", "extra_slot"}:
        await start_slot_action_for_month(message, next_action, year, month)


async def update_schedule_status_for_month(message: Message, year: int, month: int, status: str) -> None:
    saved, created = await ensure_saved_schedule(year, month)

    if saved is None:
        await message.answer("Не удалось подготовить график.", reply_markup=schedule_keyboard(True))
        return

    if not await set_schedule_status(year, month, status):
        await message.answer("Не удалось изменить статус.", reply_markup=schedule_keyboard(True))
        return

    if created:
        await message.answer(
            f"График на {month_label(year, month)} ещё не был сохранён, поэтому я сохранил расчётный вариант.",
            reply_markup=schedule_keyboard(True),
        )

    await show_schedule(message, year, month)


async def handle_slot_selection(message: Message, state: dict[str, Any], text: str) -> None:
    slot_no = parse_slot_no(text)

    if slot_no is None:
        await message.answer("Выберите дату кнопкой.")
        return

    saved = await get_saved_schedule(state["year"], state["month"])
    slot = next((item for item in saved["slots"] if item["slot_no"] == slot_no), None) if saved else None

    if slot is None:
        await message.answer("Дата не найдена.")
        return

    settings = await load_settings()

    if state["action"] == "replace_slot":
        pending_actions[message.from_user.id] = {
            "action": "replace_people",
            "year": state["year"],
            "month": state["month"],
            "slot_no": slot_no,
            "selected": [],
        }
        await message.answer(
            "Выберите участников. Нажмите ✅ Готово, чтобы заменить список на выбранный.",
            reply_markup=participants_keyboard(settings["people"], include_done=True),
        )
    elif state["action"] == "attendance_slot":
        people = [item["name"] for item in slot["participants"]]
        pending_actions[message.from_user.id] = {
            "action": "attendance_person",
            "year": state["year"],
            "month": state["month"],
            "slot_no": slot_no,
        }
        await message.answer("Выберите участника:", reply_markup=participants_keyboard(people))
    else:
        pending_actions[message.from_user.id] = {
            "action": "extra_person",
            "year": state["year"],
            "month": state["month"],
            "slot_no": slot_no,
        }
        await message.answer("Выберите участника вне графика:", reply_markup=participants_keyboard(settings["people"]))


async def handle_replace_people(message: Message, state: dict[str, Any], text: str) -> None:
    if text == "✅ Готово":
        pending_actions.pop(message.from_user.id, None)
        ok = await replace_slot_participants(
            state["year"],
            state["month"],
            state["slot_no"],
            state["selected"],
        )
        await message.answer("Список заменён." if ok else "Не удалось заменить список.")
        await show_schedule(message, state["year"], state["month"])
        return

    settings = await load_settings()

    if text not in settings["people"]:
        await message.answer("Выберите участника из списка.")
        return

    if text in state["selected"]:
        state["selected"].remove(text)
        marker = "убран"
    else:
        state["selected"].append(text)
        marker = "добавлен"

    await message.answer(f"{text} {marker}. Сейчас выбрано: {', '.join(state['selected']) or 'пусто'}")


async def handle_attendance_person(message: Message, state: dict[str, Any], text: str) -> None:
    saved = await get_saved_schedule(state["year"], state["month"])
    slot = next((item for item in saved["slots"] if item["slot_no"] == state["slot_no"]), None) if saved else None
    people = [item["name"] for item in slot["participants"]] if slot else []

    if text not in people:
        await message.answer("Выберите участника из списка.")
        return

    pending_actions[message.from_user.id] = {**state, "action": "attendance_status", "name": text}
    await message.answer("Отметьте участие:", reply_markup=simple_keyboard([["✅ Был"], ["❌ Пропустил"], ["🚫 Отмена"]]))


async def handle_attendance_status(message: Message, state: dict[str, Any], text: str) -> None:
    status_map = {"✅ Был": "attended", "❌ Пропустил": "missed"}

    if text not in status_map:
        await message.answer("Выберите статус кнопкой.")
        return

    pending_actions.pop(message.from_user.id, None)
    ok = await set_slot_participant_attendance(
        state["year"],
        state["month"],
        state["slot_no"],
        state["name"],
        status_map[text],
    )
    await message.answer("Участие отмечено." if ok else "Не удалось отметить участие.")
    await show_schedule(message, state["year"], state["month"])


async def handle_extra_person(message: Message, state: dict[str, Any], text: str) -> None:
    settings = await load_settings()

    if text not in settings["people"]:
        await message.answer("Выберите участника из списка.")
        return

    pending_actions.pop(message.from_user.id, None)
    ok = await add_extra_slot_participant(state["year"], state["month"], state["slot_no"], text)
    await message.answer("Участник добавлен вне графика." if ok else "Не удалось добавить участника.")
    await show_schedule(message, state["year"], state["month"])


async def handle_choose_list(message: Message, text: str) -> None:
    if text not in {"blockedStart", "singleParticipation", "onlySunday"}:
        await message.answer("Выберите список кнопкой.")
        return

    pending_actions[message.from_user.id] = {"action": "list_action", "list_key": text}
    await message.answer("Выберите действие:", reply_markup=simple_keyboard([["➕ Добавить"], ["➖ Убрать"], ["🚫 Отмена"]]))


async def handle_list_action(message: Message, state: dict[str, Any], text: str) -> None:
    if text not in {"➕ Добавить", "➖ Убрать"}:
        await message.answer("Выберите действие кнопкой.")
        return

    settings = await load_settings()
    pending_actions[message.from_user.id] = {
        "action": "list_person",
        "list_key": state["list_key"],
        "mode": "add" if text == "➕ Добавить" else "remove",
    }
    await message.answer("Выберите участника:", reply_markup=participants_keyboard(settings["people"]))


async def handle_list_person(message: Message, state: dict[str, Any], text: str) -> None:
    pending_actions.pop(message.from_user.id, None)
    await update_named_list(message, state["list_key"], state["mode"], normalise_name(text))


async def handle_limit_type(message: Message, text: str) -> None:
    limit_keys = {
        "🍞 Пятница": "fri",
        "☀️ Воскресенье": "sun",
        "Пятница": "fri",
        "Воскресенье": "sun",
    }

    if text not in limit_keys:
        await message.answer("Выберите день кнопкой.", reply_markup=limit_type_keyboard())
        return

    pending_actions[message.from_user.id] = {"action": "limit_value", "slot_type": limit_keys[text]}
    await message.answer("Выберите новый лимит:", reply_markup=limit_value_keyboard())


async def handle_limit_value(message: Message, state: dict[str, Any], text: str) -> None:
    try:
        value = int(text)
    except ValueError:
        await message.answer("Выберите число кнопкой.", reply_markup=limit_value_keyboard())
        return

    if value < 1 or value > 10:
        await message.answer("Лимит должен быть от 1 до 10.", reply_markup=limit_value_keyboard())
        return

    pending_actions.pop(message.from_user.id, None)
    settings = await load_settings()
    slot_type = state["slot_type"]
    settings["limits"][slot_type] = value
    await save_settings(settings)
    label = "Пятница" if slot_type == "fri" else "Воскресенье"
    await message.answer(f"Лимит обновлён: {label} — {value}.", reply_markup=settings_menu_keyboard(True))


async def add_person(message: Message, name: str) -> None:
    if not name:
        await message.answer("Имя не указано.")
        return

    settings = await load_settings()

    if name in settings["people"]:
        await message.answer("Такой участник уже есть.")
        return

    settings["people"].append(name)
    await save_settings(settings)
    await message.answer(f"Участник добавлен: {name}", reply_markup=participants_menu_keyboard(True))


async def remove_person(message: Message, name: str) -> None:
    settings = await load_settings()

    if name not in settings["people"]:
        await message.answer("Такого участника нет.")
        return

    settings["people"].remove(name)

    for key in ["blockedStart", "singleParticipation", "onlySunday"]:
        settings[key] = [value for value in settings[key] if value != name]

    await save_settings(settings)
    await message.answer(f"Участник удалён: {name}", reply_markup=participants_menu_keyboard(True))


async def update_named_list(message: Message, key: str, action: str, name: str) -> None:
    if not name:
        await message.answer("Имя не указано.")
        return

    settings = await load_settings()

    if name not in settings["people"]:
        await message.answer("Выберите участника из общего списка.")
        return

    if action == "add":
        if name not in settings[key]:
            settings[key].append(name)
        result = "добавлен"
    else:
        settings[key] = [value for value in settings[key] if value != name]
        result = "удалён"

    await save_settings(settings)
    await message.answer(f"{name} {result} в {key}.", reply_markup=settings_menu_keyboard(True))


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

    settings = await load_settings()
    settings["limits"][parts[0]] = value
    await save_settings(settings)
    await message.answer("Лимит обновлён.", reply_markup=settings_menu_keyboard(True))


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
    settings = await load_settings()
    values = settings["extraDates"][slot_type]

    if action == "add":
        if date_value not in values:
            values.append(date_value)
        result = "добавлена"
    else:
        settings["extraDates"][slot_type] = [item for item in values if item != date_value]
        result = "удалена"

    await save_settings(settings)
    await message.answer(f"Дата {date_value} {result}.", reply_markup=settings_menu_keyboard(True))
