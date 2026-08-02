from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def _keyboard(rows: list[list[str]]) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=value) for value in row] for row in rows],
        resize_keyboard=True,
    )


def main_keyboard(is_admin: bool) -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(text="📅 График"),
            KeyboardButton(text="⚙️ Настройки"),
        ],
        [
            KeyboardButton(text="👥 Участники"),
            KeyboardButton(text="❓ Помощь"),
        ],
    ]

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def schedule_keyboard(is_admin: bool) -> ReplyKeyboardMarkup:
    rows = [
        ["📆 Показать график"],
        ["⬅️ Прошлый месяц", "➡️ Следующий месяц"],
        ["🏠 Главное меню"],
    ]

    if is_admin:
        rows = [
            ["📆 Показать график", "💾 Сохранить график"],
            ["⬅️ Прошлый месяц", "➡️ Следующий месяц"],
            ["🔄 Пересохранить месяц"],
            ["✏️ Редактировать участие", "✅ Отметить участие"],
            ["➕ Вне графика"],
            ["📣 Опубликовать", "📝 Не публиковать"],
            ["🏠 Главное меню"],
        ]

    return _keyboard(rows)


def participants_menu_keyboard(is_admin: bool) -> ReplyKeyboardMarkup:
    rows = [
        ["📋 Список участников"],
        ["🏠 Главное меню"],
    ]

    if is_admin:
        rows = [
            ["📋 Список участников"],
            ["➕ Добавить участника", "🗑 Удалить участника"],
            ["🏠 Главное меню"],
        ]

    return _keyboard(rows)


def settings_menu_keyboard(is_admin: bool) -> ReplyKeyboardMarkup:
    rows = [
        ["📋 Показать настройки"],
        ["🏠 Главное меню"],
    ]

    if is_admin:
        rows = [
            ["📋 Показать настройки"],
            ["📋 Списки ограничений", "🔢 Лимиты"],
            ["📆 Доп. даты"],
            ["🏠 Главное меню"],
        ]

    return _keyboard(rows)
