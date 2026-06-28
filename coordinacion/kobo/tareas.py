from __future__ import annotations

from django_q.models import Schedule
from django_q.tasks import schedule

from coordinacion.kobo.servicio import ingestar_todo_kobo


def ingesta_periodica_kobo() -> dict:
    return ingestar_todo_kobo()


def programar_ingesta_kobo(minutos: int = 10) -> Schedule:
    """Crea o actualiza la tarea periódica de ingesta KoBo."""
    existente = Schedule.objects.filter(name="ingesta-kobo").first()
    if existente:
        existente.minutes = minutos
        existente.func = "coordinacion.kobo.tareas.ingesta_periodica_kobo"
        existente.schedule_type = Schedule.MINUTES
        existente.repeats = -1
        existente.save(update_fields=["minutes", "func", "schedule_type", "repeats"])
        return existente

    return schedule(
        "coordinacion.kobo.tareas.ingesta_periodica_kobo",
        name="ingesta-kobo",
        schedule_type=Schedule.MINUTES,
        minutes=minutos,
        repeats=-1,
    )
