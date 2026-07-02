# Estado de sincronizacion siempre visible

La PWA Nexo muestra un componente persistente de sincronizacion en el header principal. El bloque queda visible en todas las vistas autenticadas y no autenticadas porque forma parte del layout superior de `frontend/src/pages/index.astro`.

## Que muestra

El componente informa siempre:

- estado de conexion: `En linea` o `Modo avion / sin señal`;
- numero de eventos pendientes del outbox;
- numero de fotos pendientes;
- ultimo intento de sincronizacion;
- ultimo sync exitoso;
- estado actual: `Sincronizando`, `Al dia`, `Pendiente` o `Error`;
- resumen corto del ultimo error, cuando existe.

Si el navegador esta offline, aparece el mensaje operativo:

> Modo avion/sin señal: se guardara localmente.

Este aviso no bloquea la captura. Las necesidades, donaciones, claims, entregas y fotos siguen guardandose localmente en IndexedDB/Dexie.

## Persistencia en Dexie

Los valores de sincronizacion se guardan en la tabla `ajustes` de Dexie:

- `ultimoSyncOk`: fecha ISO del ultimo ciclo exitoso;
- `ultimoIntentoSync`: fecha ISO del ultimo intento iniciado;
- `ultimoErrorSync`: resumen corto del ultimo error, o `null` si no hay error activo;
- `estadoSyncActual`: `sincronizando`, `al_dia`, `pendiente` o `error`.

La funcion `obtenerEstadoSync()` consolida esos ajustes con el resumen de cola para que la UI no dependa de recargar la pagina.

## Actualizacion automatica

Las funciones de sincronizacion emiten el evento de navegador `nexo-sync-cambio` al modificar el estado persistido. La app escucha ese evento y refresca el badge sin recargar:

- `sincronizarTodo()` marca inicio, ejecuta push + pull y persiste resultado final;
- `sincronizarOutbox()` registra intento, sube eventos pendientes y luego fotos pendientes;
- `sincronizarDeltas()` registra intento y descarga solo cambios por cursor;
- `encolarEvento()` y `guardarFotoPendiente()` actualizan el estado a `pendiente` cuando se crea trabajo local nuevo.

## Boton rapido

El boton `Sincronizar ahora` esta en el componente persistente y se puede tocar desde cualquier vista con una mano. Si hay conexion, ejecuta `sincronizarTodo()`. Si no hay conexion, no bloquea ni lanza error modal: muestra el aviso de modo avion y mantiene el trabajo local.

## Manejo de errores

Los errores se resumen en `ultimoErrorSync` y se muestran dentro del badge. No bloquean la captura offline. En particular:

- un error de API o red deja el estado en `Error` y conserva la cola para reintento;
- un error al subir fotos mantiene las fotos como pendientes y muestra un resumen corto;
- la captura local continua disponible aunque falle la sincronizacion.

## Criterios operativos cubiertos

- El usuario siempre sabe si esta online/offline.
- El usuario siempre ve si tiene eventos o fotos pendientes.
- El usuario puede iniciar una sincronizacion manual desde cualquier vista.
- Los errores no bloquean trabajo offline.
- El badge se actualiza por evento local sin recargar la app.
