from app.services.scheduler import SLOT_LABELS, ScheduleResult


def fmt_list(values: list[str]) -> str:
    return "\n".join(f"• {value}" for value in values) if values else "пусто"


def format_schedule(result: ScheduleResult) -> str:
    lines = [f"<b>Расписание на {result.month:02d}.{result.year}</b>", ""]

    for slot_id, slot_type in result.slots.items():
        people = result.schedule.get(slot_id, [])
        names = ", ".join(people) if people else "нет назначений"
        label = SLOT_LABELS.get(slot_type, slot_type)
        lines.append(f"<b>{slot_id}. {result.slot_dates[slot_id]} ({label})</b>")
        lines.append(names)
        lines.append("")

    if result.errors:
        lines.append("<b>Проверка:</b>")
        lines.extend(f"• {error}" for error in result.errors)

    return "\n".join(lines).strip()


def format_settings(settings: dict) -> str:
    return (
        "<b>Настройки расписания</b>\n\n"
        f"<b>Лимиты</b>\n"
        f"• Пятница: {settings['limits']['fri']}\n"
        f"• Воскресенье: {settings['limits']['sun']}\n\n"
        f"<b>Участники</b>\n{fmt_list(settings['people'])}\n\n"
        f"<b>blockedStart</b>\n{fmt_list(settings['blockedStart'])}\n\n"
        f"<b>singleParticipation</b>\n{fmt_list(settings['singleParticipation'])}\n\n"
        f"<b>onlySunday</b>\n{fmt_list(settings['onlySunday'])}\n\n"
        f"<b>Доп. пятницы</b>\n{fmt_list(settings['extraDates']['fri'])}\n\n"
        f"<b>Доп. воскресенья</b>\n{fmt_list(settings['extraDates']['sun'])}"
    )

