# Generated manually for Nexo PostGIS real geodata.

import re

from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from django.db import migrations, models

COORD_RE = re.compile(
    r"^\s*(?:POINT\s*\()?\s*"
    r"(?P<a>-?\d+(?:\.\d+)?)"
    r"[\s,;]+"
    r"(?P<b>-?\d+(?:\.\d+)?)"
    r"(?:\s+[-+]?\d+(?:\.\d+)?)?"
    r"\s*\)?\s*$",
    re.IGNORECASE,
)


def _crear_point(latitud, longitud):
    return Point(float(longitud), float(latitud), srid=4326)


def _point_desde_texto(valor):
    if not valor:
        return None
    match = COORD_RE.match(str(valor).strip())
    if not match:
        return None

    a = float(match.group("a"))
    b = float(match.group("b"))

    # KoBo geopoint y capturas de campo suelen llegar como lat lon.
    if -90 <= a <= 90 and -180 <= b <= 180:
        return _crear_point(a, b)

    # Fallback para WKT/concepto lon lat.
    if -180 <= a <= 180 and -90 <= b <= 90:
        return _crear_point(b, a)

    return None


def migrar_texto_a_puntos(apps, schema_editor):
    CentroSalud = apps.get_model("coordinacion", "CentroSalud")
    Donacion = apps.get_model("coordinacion", "Donacion")
    Envio = apps.get_model("coordinacion", "Envio")

    for centro in CentroSalud.objects.all().iterator():
        centro.geolocalizacion_punto = _point_desde_texto(centro.geolocalizacion)
        centro.save(update_fields=["geolocalizacion_punto"])

    for donacion in Donacion.objects.all().iterator():
        punto = _point_desde_texto(donacion.ubicacion_actual)
        donacion.ubicacion_actual_punto = punto
        if donacion.ubicacion_actual and punto is None and not donacion.ubicacion_texto:
            donacion.ubicacion_texto = donacion.ubicacion_actual
            donacion.save(update_fields=["ubicacion_actual_punto", "ubicacion_texto"])
        else:
            donacion.save(update_fields=["ubicacion_actual_punto"])

    for envio in Envio.objects.all().iterator():
        punto = _point_desde_texto(envio.geolocalizacion_entrega)
        envio.geolocalizacion_entrega_punto = punto
        if envio.geolocalizacion_entrega and punto is None:
            envio.geolocalizacion_entrega_texto = envio.geolocalizacion_entrega
            envio.save(update_fields=["geolocalizacion_entrega_punto", "geolocalizacion_entrega_texto"])
        else:
            envio.save(update_fields=["geolocalizacion_entrega_punto"])


class Migration(migrations.Migration):
    dependencies = [
        ("coordinacion", "0004_kobocursor"),
    ]

    operations = [
        migrations.AddField(
            model_name="centrosalud",
            name="geolocalizacion_punto",
            field=gis_models.PointField(blank=True, null=True, srid=4326),
        ),
        migrations.AddField(
            model_name="donacion",
            name="ubicacion_actual_punto",
            field=gis_models.PointField(blank=True, null=True, srid=4326),
        ),
        migrations.AddField(
            model_name="envio",
            name="geolocalizacion_entrega_punto",
            field=gis_models.PointField(blank=True, null=True, srid=4326),
        ),
        migrations.AddField(
            model_name="envio",
            name="geolocalizacion_entrega_texto",
            field=models.CharField(blank=True, default="", max_length=255),
            preserve_default=False,
        ),
        migrations.RunPython(migrar_texto_a_puntos, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="centrosalud",
            name="geolocalizacion",
        ),
        migrations.RenameField(
            model_name="centrosalud",
            old_name="geolocalizacion_punto",
            new_name="geolocalizacion",
        ),
        migrations.RemoveField(
            model_name="donacion",
            name="ubicacion_actual",
        ),
        migrations.RenameField(
            model_name="donacion",
            old_name="ubicacion_actual_punto",
            new_name="ubicacion_actual",
        ),
        migrations.RemoveField(
            model_name="envio",
            name="geolocalizacion_entrega",
        ),
        migrations.RenameField(
            model_name="envio",
            old_name="geolocalizacion_entrega_punto",
            new_name="geolocalizacion_entrega",
        ),
    ]
