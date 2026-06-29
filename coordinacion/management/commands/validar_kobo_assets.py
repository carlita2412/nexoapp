from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from coordinacion.kobo.cliente import ClienteKobo, KoboError
from coordinacion.kobo.mapeadores import MapeoKoboError, mapear_submission
from coordinacion.kobo.servicio import obtener_asset_uid


class Command(BaseCommand):
    help = "Valida assets de KoBo contra los mapeadores Nexo sin guardar datos."

    def add_arguments(self, parser):
        parser.add_argument("--tipo", choices=["necesidad", "donacion", "todos"], default="todos")
        parser.add_argument("--limite", type=int, default=5)

    def handle(self, *args, **options):
        tipos = ["necesidad", "donacion"] if options["tipo"] == "todos" else [options["tipo"]]
        limite = options["limite"]
        cliente = ClienteKobo()
        hubo_error = False

        for tipo in tipos:
            asset_uid = obtener_asset_uid(tipo)
            if not asset_uid:
                raise CommandError(f"Falta configurar asset UID para {tipo}.")

            self.stdout.write(f"Validando KoBo {tipo}: {asset_uid}")

            try:
                submissions = cliente.obtener_submissions(asset_uid=asset_uid)[:limite]
            except KoboError as exc:
                raise CommandError(str(exc)) from exc

            if not submissions:
                self.stdout.write("Sin submissions para validar.")
                continue

            for indice, submission in enumerate(submissions, start=1):
                try:
                    evento = mapear_submission(tipo, submission)
                except MapeoKoboError as exc:
                    hubo_error = True
                    self.stdout.write(
                        self.style.ERROR(
                            f"[{tipo} #{indice}] ERROR uuid={submission.get('_uuid')}: {exc}"
                        )
                    )
                    continue

                payload = evento["payload"]
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[{tipo} #{indice}] OK uuid={submission.get('_uuid')} entity={evento['entity']} id={payload.get('id')}"
                    )
                )

        if hubo_error:
            raise CommandError("La validacion KoBo termino con errores.")

        self.stdout.write(self.style.SUCCESS("Validacion KoBo finalizada sin errores."))
