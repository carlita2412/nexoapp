from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CampoKobo:
    nombre: str
    requerido: bool = True
    aliases: tuple[str, ...] = ()
    descripcion: str = ""

    @property
    def nombres_aceptados(self) -> tuple[str, ...]:
        return (self.nombre, *self.aliases)


CAMPOS_COMUNES = (
    CampoKobo("_uuid", aliases=("uuid", "submission_uuid"), descripcion="UUID nativo de KoBo."),
    CampoKobo(
        "_submission_time",
        aliases=("submission_time",),
        requerido=False,
        descripcion="Fecha/hora de envío usada como timestamp cliente.",
    ),
)

CAMPOS_NECESIDAD = (
    *CAMPOS_COMUNES,
    CampoKobo("centro_id", aliases=("centro_salud_id", "centro"), descripcion="UUID del centro de salud exportado en CSV."),
    CampoKobo("item_codigo", aliases=("codigo_item", "item"), descripcion="Código del catálogo exportado en CSV."),
    CampoKobo("cantidad_solicitada", aliases=("cantidad",), descripcion="Cantidad requerida; entero mayor a cero."),
    CampoKobo("nivel_triage", aliases=("triage",), descripcion="1_critico, 2_urgente, 3_importante o 4_rutinario."),
    CampoKobo(
        "reportada_por_id",
        aliases=("organizacion_id", "reportada_por"),
        requerido=False,
        descripcion="UUID de organización; alternativa: reportada_por_nombre.",
    ),
    CampoKobo(
        "reportada_por_nombre",
        aliases=("organizacion_nombre", "nombre_organizacion"),
        requerido=False,
        descripcion="Nombre de organización si no se envía UUID.",
    ),
    CampoKobo("requiere_electricidad", requerido=False),
    CampoKobo("requiere_oxigeno", requerido=False),
    CampoKobo("requiere_personal_entrenado", aliases=("requiere_personal_tecnico",), requerido=False),
    CampoKobo("requiere_insumos", requerido=False),
)

CAMPOS_DONACION = (
    *CAMPOS_COMUNES,
    CampoKobo("item_codigo", aliases=("codigo_item", "item"), descripcion="Código del catálogo exportado en CSV."),
    CampoKobo("cantidad", descripcion="Cantidad disponible; entero mayor a cero."),
    CampoKobo("condicion", requerido=False, descripcion="nuevo, usado_funcional, requiere_reparacion o requiere_calibracion."),
    CampoKobo(
        "donante_id",
        aliases=("organizacion_id", "donante"),
        requerido=False,
        descripcion="UUID de organización donante; alternativa: donante_nombre.",
    ),
    CampoKobo(
        "donante_nombre",
        aliases=("organizacion_nombre", "nombre_organizacion"),
        requerido=False,
        descripcion="Nombre del donante si no se envía UUID.",
    ),
    CampoKobo("ubicacion_actual", aliases=("geopoint", "geolocalizacion"), descripcion="Geopoint KoBo: lat lon alt accuracy."),
    CampoKobo("ubicacion_texto", aliases=("direccion",), requerido=False),
    CampoKobo("vencimiento", aliases=("fecha_vencimiento",), requerido=False),
    CampoKobo("certificacion", requerido=False),
)

CONTRATO_KOBO = {
    "necesidad": CAMPOS_NECESIDAD,
    "donacion": CAMPOS_DONACION,
}


def nombres_requeridos(tipo: str) -> set[str]:
    return {campo.nombre for campo in CONTRATO_KOBO[tipo] if campo.requerido}


def nombres_aceptados(tipo: str) -> set[str]:
    nombres: set[str] = set()
    for campo in CONTRATO_KOBO[tipo]:
        nombres.update(campo.nombres_aceptados)
    return nombres
