from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from coordinacion.kobo.servicio import TIPOS_KOBO, ingestar_tipo_kobo, ingestar_todo_kobo


class Command(BaseCommand):
    help = "Ingiere submissions de KoBoToolbox de forma incremental e idempotente."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tipo",
            choices=sorted(TIPOS_KOBO),
            help="Formulario a ingerir. Si se omite, ingiere necesidades y donaciones.",
        )

    def handle(self, *args, **options):
        tipo = options.get("tipo")
        try:
            if tipo:
                resultado = ingestar_tipo_kobo(tipo)
            else:
                resultado = ingestar_todo_kobo()
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(str(resultado)))
