from getpass import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Crea un usuario del sistema con rol administrador o empleado."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument(
            "--rol", required=True, choices=["administrador", "empleado"]
        )
        parser.add_argument("--nombre", default="")
        parser.add_argument("--apellido", default="")
        parser.add_argument("--email", default="")

    def handle(self, *args, **opciones):
        User = get_user_model()
        username = opciones["username"]
        if User.objects.filter(username=username).exists():
            raise CommandError(f"El usuario «{username}» ya existe.")

        contrasena = getpass("Contraseña: ")
        if contrasena != getpass("Repita la contraseña: "):
            raise CommandError("Las contraseñas no coinciden.")

        usuario = User(
            username=username,
            rol=opciones["rol"],
            first_name=opciones["nombre"],
            last_name=opciones["apellido"],
            email=opciones["email"],
            is_staff=False,
            is_superuser=False,
        )
        try:
            validate_password(contrasena, usuario)
        except ValidationError as error:
            raise CommandError("; ".join(error.messages)) from error

        usuario.set_password(contrasena)
        usuario.save()
        self.stdout.write(self.style.SUCCESS(f"Usuario «{username}» creado."))
