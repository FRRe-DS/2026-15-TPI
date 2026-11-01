# Plan de implementación: Verificación de integración real de M3

**Rama**: `001-verificacion-integracion-m3` | **Fecha**: 2026-11-01 | **Spec**: [spec.md](./spec.md)

**Entrada**: Especificación de [verificación de integración real de M3](./spec.md).

## Resumen

Demostrar en CI el flujo de habilitación con tokens reales de Keycloak, la unicidad ante altas concurrentes, la persistencia PostgreSQL tras reiniciar la API, la publicación de eventos a RabbitMQ y los contratos con M1/M4/M5/M6. Los casos de uso escribirán eventos en un outbox de PostgreSQL dentro de la misma unidad de trabajo que el cambio de dominio; un publicador independiente entregará mensajes persistentes a RabbitMQ con publisher confirms y reintentos. Las pruebas de adaptadores usarán PostgreSQL y RabbitMQ reales mediante Testcontainers; las pruebas del flujo HTTP y persistencia golpearán el stack de Docker Compose con Keycloak real. Los cuatro conjuntos de pruebas nuevos se ejecutarán en un único job de GitHub Actions.

La planificación identifica una puerta contractual antes de implementar dobles: la copia común de los contratos de M3, M4 y M5 son OpenAPI vacíos (solo metadata), no existe allí un contrato OpenAPI de M1 y la interfaz M6 común difiere de las rutas externas descritas en el OpenAPI local de M3. Se respetarán los contratos bilaterales aprobados; no se fijarán payloads ni nombres de eventos a partir de borradores incompatibles.

## Contexto técnico

**Lenguaje/versión**: Python 3.12; `uv` y `uv.lock`.

**Dependencias principales**: FastAPI, SQLAlchemy síncrono, Alembic, PyJWT; Pika `1.3.2` en el grupo runtime `api` para AMQP 0-9-1. Testcontainers Python se fijará en `4.15.0` con extras PostgreSQL/RabbitMQ, versión ya resuelta en el lockfile.

**Almacenamiento**: PostgreSQL 17.11, base propia de M3; nueva tabla outbox mediante migración Alembic.

**Mensajería**: RabbitMQ `4.2.3-management-alpine`, etiqueta fija, exchange durable según el contrato que apruebe el equipo; los mensajes publicados serán persistentes y confirmados.

**Pruebas**: pytest + pytest-cov; Testcontainers para PostgreSQL y RabbitMQ; OpenAPI para validación contractual; E2E HTTP contra API y Keycloak levantados por Docker Compose.

**Plataforma objetivo**: Linux en GitHub Actions; Docker disponible en CI y desarrollo.

**Tipo de proyecto**: API REST en capas con dominio/casos de uso, puertos y adaptadores; servicio auxiliar de despacho del outbox.

**Metas de rendimiento**: Sin nueva meta cuantitativa; retry del outbox no bloqueará pedidos HTTP.

**Restricciones**: no publicar si la transacción falla; conservar eventos durante caída de RabbitMQ y reintentar con entrega al menos una vez; deduplicación mediante `event_id`; datos de prueba aislados; secretos exclusivamente por entorno; imágenes con versión fija, nunca `latest`.

**Alcance**: ciclo de vida completo de eventos de conductor y vehículo; concurrencia de alta de DNI; persistencia a través de reinicio de API; contratos M1, M4, M5 y M6; sin cambios de negocio ni pruebas frontend.

## Verificación de constitución

Fuente disponible: [`docs/constitucion.md`](../../docs/constitucion.md), versión declarada 1.0.0. `.specify/memory/constitution.md` conserva la plantilla sin completar; no se encontró en el worktree una enmienda posterior. Se aplica el texto normativo versionado en `docs/constitucion.md`.

| Principio | Decisión de diseño | Resultado |
|---|---|---|
| I. TDD no negociable | Escribir primero pruebas unitarias, del outbox, del adaptador Rabbit, de concurrencia y E2E; ninguna funcionalidad de producción se acepta sin el ciclo Red/Green/Refactor. | Cumple |
| II. Cobertura | Conservar el umbral CI existente de 65 %; ejecutar cobertura sobre el paquete `app` incluyendo la suite nueva. No bajar el umbral. | Cumple |
| III. Pirámide | Unitarios de puertos/casos de uso; integración con Testcontainers PostgreSQL/RabbitMQ; contratos OpenAPI; flujo E2E con Compose y Keycloak real. | Cumple |
| IV. API-first | Mantener el OpenAPI local como contrato de endpoints M3; fijar y comprobar los OpenAPI bilaterales para dobles. Resolver primero el desvío de M6, no adaptar los dobles para ocultarlo. | Cumple con puerta contractual |
| V. Migraciones | La tabla outbox se crea exclusivamente con Alembic; pruebas de migración hacia delante y atrás. | Cumple |
| VI. Sin secretos/versiones | Credenciales efímeras inyectadas por entorno; versiones fijas de imágenes y dependencias; ninguna etiqueta `latest`. | Cumple |
| VII. Código claro | Puertos pequeños, adaptadores explícitos, ruff check/format. El cliente Rabbit síncrono corre en el proceso publicador, fuera de handlers HTTP. | Cumple |
| VIII. Trabajo en paralelo | Contratos compartidos y esquema outbox son puntos de sincronización; dueños de rutas delimitados en la matriz siguiente. | Cumple |
| IX. Documentación breve | Especificación y guías de ejecución bajo `specs/001-verificacion-integracion-m3/`; README se actualiza al implementar. | Cumple |
| X. Propiedad de datos | M3 solo consulta su PostgreSQL; dobles de módulos externos exponen contratos, no sus tablas. | Cumple |
| XI. Concurrencia | Restricción única de DNI permanece como árbitro; dos peticiones HTTP concurrentes verifican un único alta y respuesta perdedora 409. | Cumple |

**Puerta previa a integrar dobles**: la fuente común `FRRe-DS/2026-TPI` en el commit `69e9481c754063fc054c8d0ecfdec18d71bf48e6` contiene únicamente metadata en `contratos/m3_conductores/openapi.yml`, `contratos/m4_ubicacion/openapi.yml` y `contratos/m5_solicitud/openapi.yml`. El contrato M6 sí tiene operaciones, pero expresa `GET /trips/{id}` y `POST /trips/{id}/complete|cancel`, mientras el OpenAPI local M3 describe `GET /viajes/{id_viaje}` y `POST .../finalizar|cancelar`. La fuente común M6 también declara JWT de M1 con `sub`/`identidad_id` y `role`/`roles`; el contrato local de token M3 exige `realm_access.roles` e `id_operador`. Antes de dar por cubierta una frontera se deberá acordar y versionar un contrato bilateral, actualizar el OpenAPI propio si procede y hacer que el test contractual falle con cualquiera de esas incompatibilidades. La suite no aprobará tests basados solo en los esqueletos.

**Resultado de gate**: principios constitucionales cumplidos. El diseño técnico está resuelto; la implementación de pruebas contractuales M1/M4/M5 y de consumo M6 queda condicionada a publicar la matriz bilateral acordada. Este gate no autoriza a inventar un contrato.

## Estructura del proyecto

### Documentación de esta funcionalidad

```text
specs/001-verificacion-integracion-m3/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── eventos-m3.md
│   └── integraciones-modulos.md
└── checklists/requirements.md
```

### Código fuente previsto

```text
backend/
├── app/
│   ├── aplicacion/
│   │   └── puertos/                 # Puerto para registrar eventos transaccionales
│   ├── infraestructura/
│   │   ├── db/                      # Modelo SQLAlchemy del outbox
│   │   └── repositorios/            # Escritura/claim SQL del outbox
│   └── infraestructura/mensajeria/  # Adaptador RabbitMQ y publicador del outbox
├── tests/
│   ├── contrato/                    # Dobles y validación de contratos bilaterales
│   ├── e2e/                         # API/Keycloak reales del Compose
│   └── integracion/
│       ├── concurrencia/            # Peticiones HTTP paralelas y estado PostgreSQL
│       └── mensajeria/              # Testcontainers PostgreSQL + RabbitMQ
├── pyproject.toml
└── uv.lock

infra/
├── docker-compose.yml                # RabbitMQ y servicio de despacho
└── migraciones/versions/             # Tabla outbox

.github/workflows/ci.yml              # Un job de verificación real M3
docs/contract/openapi.yaml            # Actualización solo tras acuerdo bilateral
```

**Decisión de estructura**: mantener las capas existentes y reutilizar la unidad de trabajo SQL. El adaptador de aplicación escribe el evento en el outbox usando la misma sesión/transacción que guarda entidad e historial. Un proceso independiente reclama pendientes, los publica por un puerto de mensajería implementado con RabbitMQ y los marca publicados solo después de recibir confirmación del broker.

## Estrategia de verificación

1. **Pruebas aisladas con Testcontainers**: fixtures pytest levantan PostgreSQL `17.11-alpine` y RabbitMQ `4.2.3-management-alpine` con etiquetas explícitas. Migraciones aplicadas a la base de prueba. Cada prueba usa identificadores propios; no se truncan datos compartidos en paralelo.
2. **Atomicidad/outbox**: comprobar que la fila de outbox y el cambio de dominio se confirman juntos; rollback elimina ambos. Consumir desde una cola exclusiva temporal ligada al exchange/routing key del contrato. Validar `event_id`, nombre, cabeceras y payload contra el contrato acordado.
3. **Entrega durable**: parar/disponibilizar RabbitMQ durante una creación, comprobar que el API confirma el cambio guardando el outbox y que el publicador reintenta al recuperar el broker. Simular crash tras confirmación antes del marcado de outbox y aceptar duplicado con el mismo `event_id`.
4. **Concurrencia**: generar DNI único por prueba; dos workers con clientes HTTP independientes y barrera de sincronización disparan el mismo `POST /conductores`. Aserciones exactas: respuestas `[201, 409]`, error perdedor `DNI_DUPLICADO`, exactamente una fila y un único evento `ALTA` correspondiente.
5. **E2E Compose**: iniciar PostgreSQL, Keycloak, migraciones, seed, RabbitMQ, publicador y API; conseguir tokens por el endpoint OIDC del realm real de Compose; recorrer alta, licencia, vehículo y aprobaciones; validar roles e historial; confirmar mensaje en cola temporal. Reiniciar solo API/publicador según el escenario y comprobar que la fila sigue en PostgreSQL.
6. **Contratos vecinos**: cada doble se construye a partir del OpenAPI/esquema bilateral aprobado y valida request/response con los mismos documentos versionados. Un documento faltante, vacío, desactualizado o incompatible falla el job antes de considerar completa la historia.
7. **CI**: un job Linux prepara variables de prueba, arranca Compose, verifica salud, corre pytest completo con cobertura (incluyendo Testcontainers y E2E) y siempre ejecuta `docker compose down -v` en `if: always()`. Un fallo de Docker, servicio requerido, test marcado como skip o contrato no disponible hace fallar este job. Los jobs de lint y frontend existentes conservan su independencia.

## Complejidad

La tabla outbox es la complejidad mínima para cumplir simultáneamente atomicidad y recuperación ante caída del broker: publicar directamente desde el caso de uso antes/después del commit deja una ventana de pérdida o evento fantasma. El proceso de despacho usa confirmaciones y reintentos; no se introducen nuevos servicios de negocio ni una plataforma de eventos adicional.
