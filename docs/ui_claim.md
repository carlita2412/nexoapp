# UI de estados de claim

La PWA de Nexo debe mostrar el estado de cada `Asignacion.estado_claim` de forma visible y consistente en el listado de asignaciones, la cola pendiente, el resultado de sincronización y el detalle de matching/claim.

## Estados visuales

| Estado | Color | Significado operativo | Mensaje obligatorio |
|---|---|---|---|
| `tentativa` | Amarillo | Claim local pendiente de arbitraje del servidor. No se debe tratar como asignación ganada. | “Pendiente de sincronizar. Aún no está confirmado por servidor.” |
| `confirmada` | Verde | El servidor confirmó que la organización ganó la asignación. | “Claim confirmado. Puedes coordinar envío.” |
| `superada` | Rojo | Otra organización cubrió la necesidad antes. Nunca debe parecer éxito. | “Otra organización ya cubre esta necesidad. Revisa candidatos alternativos.” |
| `liberada` | Neutral | El claim fue liberado o vuelve a estar disponible si aplica. | “Claim liberado. La necesidad puede volver a ser reclamada.” |

## Reglas de interacción

1. Al reclamar offline, la app crea una asignación local con `estado_claim = "tentativa"` y encola un evento `asignacion_claim`.
2. Mientras el evento no tenga respuesta del servidor, la UI debe mantener el estado amarillo y mostrar que aún no está confirmado.
3. Al sincronizar, el servidor arbitra el claim y devuelve el resultado por `idempotency_key`.
4. La PWA actualiza tanto el evento del outbox como la tabla local `asignaciones` en IndexedDB con el resultado devuelto por el servidor.
5. Si el servidor devuelve `superada`, la tarjeta debe quedar roja y mostrar el fallback de candidatos alternativos.
6. Si el servidor devuelve `ok`, `duplicado` o un registro con `estado_claim = "confirmada"`, la asignación puede mostrarse verde.
7. La confirmación de entrega debe apoyarse únicamente en asignaciones claramente visibles; una asignación `superada` no debe parecer exitosa.

## Ubicaciones obligatorias en UI

- **Cola pendiente:** cada evento `asignacion_claim` usa badge y mensaje del estado de claim, no solo el estado genérico del outbox.
- **Resultado de sincronización:** después del push, el evento conserva la respuesta completa y el estado local cambia a `confirmada`, `superada`, `tentativa` o `liberada` según corresponda.
- **Detalle de matching/claim:** muestra los claims de la necesidad seleccionada con color, etiqueta y mensaje operativo.
- **Listado de asignaciones:** cada asignación muestra el estado visual y el texto de acción/fallback.

## Principio operativo

Bajo mala red, el operador debe poder distinguir entre “lo guardé localmente” y “el servidor ya confirmó que gané la asignación”. La UI no debe generar falsa confianza: `tentativa` no es éxito y `superada` exige revisar alternativas.
