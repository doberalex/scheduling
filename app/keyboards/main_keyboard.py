from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_keyboard(is_admin: bool) -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(text="Расписание"),
            KeyboardButton(text="Настройки"),
        ],
        [
            KeyboardButton(text="Участники"),
            KeyboardButton(text="Помощь"),
        ],
    ]

    if is_admin:
        keyboard.extend(
            [
                [
                    KeyboardButton(text="Добавить участника"),
                    KeyboardButton(text="Удалить участника"),
                ],
                [
                    KeyboardButton(text="Списки ограничений"),
                    KeyboardButton(text="Лимиты"),
                ],
                [
                    KeyboardButton(text="Доп. даты"),
                    KeyboardButton(text="Отмена"),
                ],
            ]
        )

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

