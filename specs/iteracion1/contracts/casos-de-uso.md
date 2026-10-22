# Contrato interno: casos de uso y puertos

Punto de sincronización entre el **Stack 1** (lógica) y el **Stack 2** (servidor HTTP). El servidor solo llama a estos casos de uso; la lógica nunca importa FastAPI ni SQLAlchemy. Cualquier cambio de firma se acuerda entre ambos stacks y se hace en su propia PR.

Los nombres de los tipos de entrada y salida coinciden con los esquemas de `docs/contract/openapi.yaml`.

## Casos de uso (`backend/src/m3/aplicacion/casos_de_uso/`)

| # | Endpoint | Caso de uso | Entrada | Salida | Errores de dominio |
|---|---|---|---|---|---|
| 1 | `POST /conductores` | `crear_conductor` | `ConductorCreate` | `Conductor` | `DniDuplicado` (409) |
| 2 | `GET /conductores` | `listar_conductores` | `habilitado?`, `disponible?`, `tipo_vehiculo?` | lista de `ConductorConUbicacion` | — |
| 3 | `GET /conductores/{id}` | `obtener_conductor` | `id_conductor` | `Conductor` | `NoEncontrado` (404) |
| 4 | `GET /conductores/{id}/habilitacion` | `consultar_habilitacion_conductor` | `id_conductor` | `HabilitacionResumen` | `NoEncontrado` |
| 5 | `POST /conductores/{id}/habilitacion` | `accionar_habilitacion_conductor` | `id_conductor`, `HabilitacionAccionRequest`, `id_operador` | `HabilitacionEventos` | `NoEncontrado`, `TransicionInvalida` (409), `LicenciaVigenteRequerida` (422) |
| 6 | `POST /conductores/{id}/documentacion` | `registrar_licencia` | `id_conductor`, `DocumentoConductorCreate` | `DocumentoConductor` | `NoEncontrado`, `DatosInvalidos` (422) |
| 7 | `POST /conductores/{id}/vehiculos` | `registrar_vehiculo` | `id_conductor`, `VehiculoCreate` | `Vehiculo` | `NoEncontrado`, `PatenteDuplicada` (409) |
| 8 | `GET /conductores/{id}/vehiculos` | `listar_vehiculos` | `id_conductor`, `tipo?`, `habilitacion?` | lista de `VehiculoResumen` | `NoEncontrado` |
| 9 | `GET /conductores/{id}/vehiculos/{id_vehiculo}` | `obtener_vehiculo` | `id_conductor`, `id_vehiculo` | `Vehiculo` | `NoEncontrado` |
| 10 | `POST /conductores/{id}/vehiculos/{id_vehiculo}/habilitacion` | `accionar_habilitacion_vehiculo` | `id_conductor`, `id_vehiculo`, `HabilitacionAccionRequest`, `id_operador` | `HabilitacionVehiculoEventos` | `NoEncontrado`, `TransicionInvalida` |

Reglas comunes:
- `id_operador` lo entrega el servidor leyéndolo del token; el caso de uso no conoce JWT.
- Un vehículo que no pertenece al conductor indicado se trata como `NoEncontrado`.
- Las acciones de habilitación se ejecutan en una única transacción con bloqueo de fila.

## Puertos (`backend/src/m3/aplicacion/puertos/`)

| Puerto | Responsabilidad |
|---|---|
| `RepositorioConductores` | Guardar y buscar conductores; listar con filtros; buscar con documentos y vehículos |
| `RepositorioVehiculos` | Guardar y buscar vehículos por conductor |
| `RepositorioDocumentos` | Guardar licencias y consultar las del conductor |
| `RepositorioHabilitaciones` | Registrar eventos y leer el historial |
| `UnidadDeTrabajo` | Transacción con bloqueo de fila sobre conductor o vehículo |
| `Reloj` | Fecha y hora actuales (inyectable para tests) |

Los repositorios SQL los implementa el Stack 1 en `infraestructura/repositorios/` sobre los modelos del Stack 3. Para los tests unitarios se usan implementaciones en memoria.

## Errores de dominio (`backend/src/m3/dominio/errores.py`)

`NoEncontrado`, `DniDuplicado`, `PatenteDuplicada`, `TransicionInvalida`, `LicenciaVigenteRequerida` y `DatosInvalidos`. El servidor los traduce a HTTP según [errores.md](./errores.md).
