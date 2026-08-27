from app.services.scheduler import SLOT_LABELS, ScheduleResult

STATUS_LABELS = {
    "published": "опубликован",
    "unpublished": "не опубликован",
}
ATTENDANCE_LABELS = {
    "planned": "📌",
    "attended": "✅",
    "missed": "❌",
    "reserve": "🟡",
}


def fmt_list(values: list[str]) -> str:
    return "\n".join(f"• {value}" for value in values) if values else "пусто"


def fmt_name_list(values: list[str]) -> str:
    return fmt_list(sorted(values, key=str.casefold))


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


def format_saved_schedule(saved: dict, errors: list[str] | None = None) -> str:
    lines = [
        f"<b>Сохранённый график на {saved['month']:02d}.{saved['year']}</b>",
        f"Статус: <b>{STATUS_LABELS.get(saved['status'], saved['status'])}</b>",
        "",
    ]

    for slot in saved["slots"]:
        label = SLOT_LABELS.get(slot["slot_type"], slot["slot_type"])
        lines.append(f"<b>{slot['slot_no']}. {slot['date']} ({label})</b>")

        if not slot["participants"]:
            lines.append("нет назначений")
        else:
            for participant in slot["participants"]:
                prefix = "•"
                if not participant["is_scheduled"]:
                    prefix = "➕"

                status = ATTENDANCE_LABELS.get(
                    participant["attendance_status"],
                    participant["attendance_status"],
                )
                lines.append(f"{prefix} {participant['name']} — {status}")

        lines.append("")

    if errors:
        lines.append("<b>Проверка:</b>")
        lines.extend(f"• {error}" for error in errors)

    return "\n".join(lines).strip()


def format_settings(settings: dict) -> str:
    return (
        "<b>Настройки расписания</b>\n\n"
        f"<b>Лимиты</b>\n"
        f"• Пятница: {settings['limits']['fri']}\n"
        f"• Воскресенье: {settings['limits']['sun']}\n\n"
        f"<b>Участники</b>\n{fmt_name_list(settings['people'])}\n\n"
        f"<b>blockedStart</b>\n{fmt_name_list(settings['blockedStart'])}\n\n"
        f"<b>singleParticipation</b>\n{fmt_name_list(settings['singleParticipation'])}\n\n"
        f"<b>onlySunday</b>\n{fmt_name_list(settings['onlySunday'])}\n\n"
        f"<b>Доп. пятницы</b>\n{fmt_list(settings['extraDates']['fri'])}\n\n"
        f"<b>Доп. воскресенья</b>\n{fmt_list(settings['extraDates']['sun'])}"
    )
