# Contrato interno: casos de uso y puertos (ampliación)

Punto de sincronización entre el **Stack 1** (lógica) y el **Stack 2** (servidor HTTP). Amplía el [contrato de la Iteración 1](../../iteracion1/contracts/casos-de-uso.md), cuyas reglas comunes siguen vigentes: el servidor solo llama a casos de uso, la lógica nunca importa FastAPI ni SQLAlchemy, y un vehículo que no es del conductor indicado se trata como `NoEncontrado`. Cualquier cambio de firma se acuerda entre ambos stacks y se hace en su propia PR.

Los nombres de entrada y salida coinciden con los esquemas de `docs/contract/openapi.yaml`.

## Casos de uso nuevos (`backend/app/aplicacion/casos_de_uso/`)

| # | Endpoint | Caso de uso | Entrada | Salida | Errores de dominio |
|---|---|---|---|---|---|
| 1 | `GET .../vehiculos/{id_vehiculo}/tipos-servicio` | `listar_tipos_servicio_vehiculo` | `id_conductor`, `id_vehiculo` | lista de `TipoServicioHabilitado` | `NoEncontrado` |
| 2 | `POST .../vehiculos/{id_vehiculo}/documentacion` | `registrar_documento_vehiculo` | `id_conductor`, `id_vehiculo`, `DocumentoVehiculoCreate` | `DocumentoVehiculo` | `NoEncontrado`, `DatosInvalidos` (422) |
| 3 | `GET /conductores/{id}/estado` | `obtener_estado_conductor` | `id_conductor` | `EstadoConductor` | `NoEncontrado` |
| 4 | `PATCH /conductores/{id}/estado` | `actualizar_estado_conductor` | `id_conductor`, `EstadoConductorRequest` | `EstadoConductor` | `NoEncontrado`, `DatosInvalidos` (400 al validar la forma), `ConductorNoHabilitado` (422) |
| 5 | `GET /conductores/{id}/ubicacion` | `obtener_ubicacion_conductor` | `id_conductor` | `UbicacionConductor` | `NoEncontrado` |
| 6 | `GET /conductores/{id}/solicitudes` | `listar_solicitudes_conductor` | `id_conductor`, `estado?` | lista de `Solicitud` | `NoEncontrado` |
| 7 | `POST /solicitudes/{id_solicitud}` | `responder_solicitud` | `id_solicitud`, `RespuestaSolicitudRequest`, identidad de quien responde | `Solicitud` | `NoEncontrado`, `AccesoProhibido`, `SolicitudVencida` (410), `SolicitudYaRespondida` (409), `ConductorNoHabilitado` (422) |
| 8 | `PATCH /integraciones/m4/conductores/{id}/disponibilidad` | `actualizar_disponibilidad_desde_m4` | `id_conductor`, `DisponibilidadM4Request` | `EstadoConductor` | `NoEncontrado`, `ConductorNoHabilitado` (422) |
| 9 | `POST /integraciones/m6/viajes/{id_viaje}/finalizacion` | `registrar_viaje_finalizado` | `id_viaje`, `ViajeFinalizadoM6Request` | `ViajeFinalizadoM3Response` | `NoEncontrado`, `ViajeEnConflicto` (409) |

### Reglas de cada caso de uso

- **`actualizar_estado_conductor`**: bloquea al conductor, valida el vehículo activo pedido (`NoEncontrado` si no es suyo), aplica el cambio con las reglas de [research.md](../research.md) (decisión 5), asigna la ubicación simulada si corresponde (decisión 6) y guarda `fecha_ultimo_cambio_estado` solo si algún valor cambió. Si vienen `latitud` y `longitud`, `fecha_act_ubic` es la hora del `Reloj`.
- **`actualizar_disponibilidad_desde_m4`**: bloquea al conductor; si `actualizado` es estrictamente anterior a `fecha_ultimo_cambio_estado`, devuelve el estado vigente sin cambios; si no, aplica solo `disponible` y guarda `actualizado` de M4 como `fecha_ultimo_cambio_estado`. `disponible = false` se acepta siempre. `motivo` no cambia ninguna regla en esta iteración.
- **`registrar_viaje_finalizado`**: bloquea al conductor y registra el viaje con `INSERT ... ON CONFLICT DO NOTHING`. Si insertó, aplica el destino como ubicación (solo si no es anterior a la actual) y, si hay puntaje, suma a `suma_puntajes` y `cantidad_calificaciones`. Si ya existía, compara y devuelve el resultado guardado (`200`) o `ViajeEnConflicto`. Ver decisión 2.
- **`responder_solicitud`**: lee la solicitud, aplica la política de acceso (si responde un conductor, debe ser el dueño), bloquea al conductor y después a la solicitud, y revalida. Estado efectivo `VENCIDA` → `SolicitudVencida`; estado ya respondido → `SolicitudYaRespondida`. Al aceptar, exige que el conductor pueda estar disponible y lo deja no disponible (`actualizado` con la hora del `Reloj`); al rechazar, no toca su disponibilidad.
- **`listar_solicitudes_conductor`**: lee todas las solicitudes del conductor, calcula el estado efectivo con el `Reloj` y aplica el filtro `estado` sobre ese estado.
- **`registrar_documento_vehiculo`**: exige que el vehículo sea del conductor, valida el documento (`DatosInvalidos` si el vencimiento no es posterior a la emisión) y devuelve el estado calculado.
- **`listar_tipos_servicio_vehiculo`**: devuelve cada tipo del vehículo con su `habilitado`.

## Casos de uso existentes que cambian

| Caso de uso | Cambio | Entrada nueva | Salida nueva |
|---|---|---|---|
| `listar_conductores` | filtra por `tipo_servicio`; `latitud` y `longitud` no se pasan (se ignoran en el servidor) | `tipo_servicio?` | los conductores incluyen `puntaje_promedio`, `cantidad_calificaciones` e `id_vehiculo_activo` |
| `obtener_conductor` | sin cambios de firma | — | ídem |
| `obtener_vehiculo` | incluye los documentos del vehículo con estado calculado | — | `Vehiculo` con `documentos` |
| `accionar_habilitacion_vehiculo` | al aprobar, habilita los tipos de servicio; al suspender o rechazar, los deshabilita (decisión 9) | — | — |
| `crear_conductor` y demás de la Iteración 1 | sin cambios | — | — |

## Dominio nuevo (`backend/app/dominio/`)

| Módulo | Contenido |
|---|---|
| `conductor.py` (cambia) | Campos nuevos: `id_vehiculo_activo`, `fecha_ultimo_cambio_estado`, `suma_puntajes`, `cantidad_calificaciones`; propiedad `puntaje_promedio` (decisión 4) y operación para registrar un puntaje |
| `disponibilidad.py` (nuevo) | Regla "puede estar disponible" y función que aplica un cambio de estado (decisión 5) |
| `solicitud.py` (nuevo) | Entidad, enum `EstadoSolicitud`, `estado_efectivo(ahora)` y `responder(...)` |
| `viaje_finalizado.py` (nuevo) | Entidad con destino, puntaje y `ubicacion_aplicada` |
| `documento_vehiculo.py` (nuevo) | Entidad y enum `TipoDocumentoVehiculo` (`SEGURO`, `CEDULA_VERDE`, `VTV`), con las mismas validaciones del documento del conductor |
| `errores.py` (cambia) | `AccesoProhibido`, `RolNoAutorizado`, `SolicitudVencida`, `SolicitudYaRespondida`, `ViajeEnConflicto`, `ConductorNoHabilitado` |

## Puertos (`backend/app/aplicacion/puertos/`)

| Puerto | Responsabilidad | Cambio |
|---|---|---|
| `RepositorioConductores` | `listar` suma `tipo_servicio`; guardar persiste los campos nuevos | cambia |
| `RepositorioSolicitudes` | `obtener`, `listar_por_conductor`, `guardar` | nuevo |
| `RepositorioViajesFinalizados` | `registrar_si_no_existe(viaje) -> bool` y `obtener(id_viaje)` | nuevo |
| `RepositorioDocumentosVehiculo` | `guardar`, `listar_por_vehiculo` y `listar_por_vehiculos` (por lote) | nuevo |
| `UnidadDeTrabajo` | Suma `solicitudes`, `viajes_finalizados`, `documentos_vehiculo` y `bloquear_solicitud(id)` | cambia |
| `Reloj` | Sin cambios | — |

## Política de acceso (`backend/app/aplicacion/politicas/acceso.py`)

Función pura que recibe los roles del token, el `id_conductor` del token, el `id_conductor` del recurso y los roles que la operación admite, y lanza `AccesoProhibido` (id de otro conductor) o `RolNoAutorizado` (rol no admitido). Reglas completas y matriz por endpoint: [token-jwt.md](./token-jwt.md). No importa FastAPI ni JWT.

## Configuración (`backend/app/api/configuracion.py`)

| Variable | Obligatoria | Valor por defecto | Uso |
|---|---|---|---|
| `UBICACION_SIMULADA_LATITUD` | no | `-27.4511` | Ubicación simulada fija (decisión 6) |
| `UBICACION_SIMULADA_LONGITUD` | no | `-58.9867` | ídem |

Se agregan a `infra/.env.example` en la PR de Datos y seguridad que toque ese archivo; no son secretos.

## Servidor (Stack 2)

El servidor entrega a los casos de uso el reloj y la ubicación simulada inyectados, traduce los errores según [errores.md](./errores.md), y aplica las dependencias de acceso de [token-jwt.md](./token-jwt.md). `latitud` y `longitud` del listado se siguen validando en rango y se descartan antes de llamar al caso de uso.
