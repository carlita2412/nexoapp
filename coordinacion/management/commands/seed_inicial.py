from __future__ import annotations

import os

from django.core.management.base import BaseCommand, CommandError

from coordinacion.seed import ejecutar_seed_inicial


class Command(BaseCommand):
    help = "Carga organizaciones, catalogos, centros de salud y usuarios base."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sin-usuarios",
            action="store_true",
            help="Carga solo organizaciones, catalogos y centros de salud.",
        )
        parser.add_argument(
            "--password-inicial",
            help=(
                "Password temporal para los usuarios base. "
                "Tambien puede definirse NEXO_SEED_PASSWORD."
            ),
        )
        parser.add_argument(
            "--reset-passwords",
            action="store_true",
            help="Sobrescribe la password de usuarios existentes con la password inicial.",
        )

    def handle(self, *args, **options):
        crear_usuarios = not options["sin_usuarios"]
        password_inicial = options.get("password_inicial") or os.getenv(
            "NEXO_SEED_PASSWORD"
        )
        reset_passwords = bool(options["reset_passwords"])

        if reset_passwords and not password_inicial:
            raise CommandError(
                "--reset-passwords requiere --password-inicial o NEXO_SEED_PASSWORD."
            )

        resultado = ejecutar_seed_inicial(
            crear_usuarios=crear_usuarios,
            password_inicial=password_inicial,
            reset_passwords=reset_passwords,
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Seed inicial aplicado: "
                f"{resultado['organizaciones']} organizaciones, "
                f"{resultado['catalogos']} catalogos, "
                f"{resultado['centros_salud']} centros de salud, "
                f"{resultado['usuarios']} usuarios."
            )
        )

        if crear_usuarios and not password_inicial:
            self.stdout.write(
                self.style.WARNING(
                    "Usuarios creados sin password usable. Define una password con: "
                    "python manage.py seed_inicial --password-inicial '<clave-temporal>' "
                    "--reset-passwords"
                )
            )
        elif crear_usuarios:
            self.stdout.write(
                self.style.WARNING(
                    "Password temporal aplicada solo a usuarios nuevos. "
                    "Usa --reset-passwords si necesitas reemplazar passwords existentes. "
                    "Cambia estas claves despues del primer ingreso."
                )
            )
