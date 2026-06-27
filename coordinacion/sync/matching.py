from dataclasses import dataclass

from coordinacion.models import Donacion, Necesidad


@dataclass
class ResultadoMatching:
    donacion: Donacion
    compatible: bool
    motivo: str
    puntaje: int


def centro_cumple_requisitos(necesidad: Necesidad) -> tuple[bool, str]:
    """
    Valida si el centro de salud puede operar el item solicitado.
    Ejemplo: si la necesidad requiere electricidad, el centro debe tener electricidad.
    """
    centro = necesidad.centro
    requisitos = necesidad.requisitos_operacion or {}

    requiere_electricidad = requisitos.get("requiere_electricidad", False)
    requiere_oxigeno = requisitos.get("requiere_oxigeno", False)
    requiere_agua = requisitos.get("requiere_agua", False)
    requiere_personal_entrenado = requisitos.get(
        "requiere_personal_entrenado",
        False,
    )

    if requiere_electricidad and not centro.tiene_electricidad:
        return False, "El centro no tiene electricidad para operar este equipo."

    if requiere_oxigeno and not centro.tiene_oxigeno:
        return False, "El centro no tiene oxígeno disponible."

    if requiere_agua and not centro.tiene_agua:
        return False, "El centro no tiene agua disponible."

    if requiere_personal_entrenado and not centro.tiene_personal_tecnico:
        return False, "El centro no tiene personal técnico entrenado."

    return True, "El centro cumple los requisitos de operación."


def calcular_puntaje(necesidad: Necesidad, donacion: Donacion) -> int:
    """
    Calcula un puntaje simple para ordenar candidatos.
    Mientras más alto, mejor candidato.
    """
    puntaje = 0

    if donacion.item_id == necesidad.item_id:
        puntaje += 50

    cantidad_pendiente = necesidad.cantidad_solicitada - necesidad.cantidad_cubierta

    if donacion.cantidad >= cantidad_pendiente:
        puntaje += 30
    elif donacion.cantidad > 0:
        puntaje += 15

    if donacion.condicion == Donacion.Condicion.NUEVO:
        puntaje += 20
    elif donacion.condicion == Donacion.Condicion.USADO_FUNCIONAL:
        puntaje += 15
    elif donacion.condicion == Donacion.Condicion.REQUIERE_CALIBRACION:
        puntaje += 5

    return puntaje


def evaluar_donacion_para_necesidad(
    necesidad: Necesidad,
    donacion: Donacion,
) -> ResultadoMatching:
    """
    Evalúa si una donación sirve para una necesidad específica.
    """
    if necesidad.estado not in [
        Necesidad.Estado.ABIERTA,
        Necesidad.Estado.PARCIAL,
    ]:
        return ResultadoMatching(
            donacion=donacion,
            compatible=False,
            motivo="La necesidad no está abierta ni parcial.",
            puntaje=0,
        )

    if donacion.estado != Donacion.Estado.DISPONIBLE:
        return ResultadoMatching(
            donacion=donacion,
            compatible=False,
            motivo="La donación no está disponible.",
            puntaje=0,
        )

    if donacion.item_id != necesidad.item_id:
        return ResultadoMatching(
            donacion=donacion,
            compatible=False,
            motivo="El item de la donación no coincide con el item solicitado.",
            puntaje=0,
        )

    cantidad_pendiente = necesidad.cantidad_solicitada - necesidad.cantidad_cubierta

    if cantidad_pendiente <= 0:
        return ResultadoMatching(
            donacion=donacion,
            compatible=False,
            motivo="La necesidad ya está cubierta.",
            puntaje=0,
        )

    if donacion.cantidad <= 0:
        return ResultadoMatching(
            donacion=donacion,
            compatible=False,
            motivo="La donación no tiene cantidad disponible.",
            puntaje=0,
        )

    if donacion.condicion == Donacion.Condicion.REQUIERE_REPARACION:
        return ResultadoMatching(
            donacion=donacion,
            compatible=False,
            motivo="La donación requiere reparación y no debe sugerirse.",
            puntaje=0,
        )

    centro_ok, motivo_centro = centro_cumple_requisitos(necesidad)

    if not centro_ok:
        return ResultadoMatching(
            donacion=donacion,
            compatible=False,
            motivo=motivo_centro,
            puntaje=0,
        )

    puntaje = calcular_puntaje(necesidad, donacion)

    return ResultadoMatching(
        donacion=donacion,
        compatible=True,
        motivo="Donación compatible con la necesidad.",
        puntaje=puntaje,
    )


def obtener_candidatos_para_necesidad(necesidad: Necesidad) -> list[ResultadoMatching]:
    """
    Devuelve las donaciones compatibles para una necesidad,
    ordenadas de mejor a peor.
    """
    donaciones = Donacion.objects.filter(
        item=necesidad.item,
        estado=Donacion.Estado.DISPONIBLE,
    )

    resultados = []

    for donacion in donaciones:
        resultado = evaluar_donacion_para_necesidad(necesidad, donacion)

        if resultado.compatible:
            resultados.append(resultado)

    resultados.sort(key=lambda item: item.puntaje, reverse=True)

    return resultados