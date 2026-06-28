"""
Compresión de fotos de entrega (PROMPT_MAESTRO §2: una foto < 100 KB).

El cliente comprime antes de subir; el servidor vuelve a comprimir de forma
defensiva para *garantizar* el presupuesto, y de paso:
- corrige la orientación según EXIF,
- descarta los metadatos EXIF (privacidad §7: pueden traer GPS/dispositivo),
- normaliza a JPEG.
"""
from io import BytesIO

from PIL import Image, ImageOps

OBJETIVO_BYTES = 100_000          # presupuesto de una foto de entrega
MAX_LADO = 1280                   # px del lado mayor tras redimensionar
CALIDADES = (85, 75, 65, 55, 45, 35)
LADO_MINIMO = 320                 # no encoger por debajo de esto


def comprimir_a_objetivo(
    datos: bytes,
    objetivo_bytes: int = OBJETIVO_BYTES,
    max_lado: int = MAX_LADO,
) -> tuple[bytes, dict]:
    """
    Devuelve (bytes_jpeg, meta) donde meta describe el resultado.
    Garantiza el objetivo salvo imágenes degeneradas muy pequeñas.
    """
    imagen = Image.open(BytesIO(datos))
    imagen = ImageOps.exif_transpose(imagen)        # respeta rotación del móvil
    imagen = imagen.convert("RGB")                  # quita alfa y EXIF
    imagen.thumbnail((max_lado, max_lado))          # nunca agranda

    def _encode(img, calidad):
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=calidad, optimize=True)
        return buf.getvalue()

    # 1) bajar calidad
    salida = _encode(imagen, CALIDADES[0])
    calidad_final = CALIDADES[0]
    for calidad in CALIDADES:
        salida = _encode(imagen, calidad)
        calidad_final = calidad
        if len(salida) <= objetivo_bytes:
            break

    # 2) si aún excede, encoger dimensiones progresivamente
    while len(salida) > objetivo_bytes and min(imagen.size) > LADO_MINIMO:
        nuevo = (int(imagen.width * 0.85), int(imagen.height * 0.85))
        imagen.thumbnail(nuevo)
        salida = _encode(imagen, calidad_final)

    meta = {
        "bytes": len(salida),
        "ancho": imagen.width,
        "alto": imagen.height,
        "calidad": calidad_final,
        "dentro_de_presupuesto": len(salida) <= objetivo_bytes,
    }
    return salida, meta
