# Checklist de Calidad de la Especificación: Verificación de integración real de M3

**Propósito**: Validar la completitud y calidad de la especificación antes de planificar
**Creado**: 2026-11-01
**Funcionalidad**: [spec.md](../spec.md)

## Calidad del Contenido

- [x] Sin detalles de implementación no requeridos por el objetivo de verificación
- [x] Enfocada en el valor de demostrar el comportamiento de M3
- [x] Escrita para el equipo responsable de M3 y sus integraciones
- [x] Todas las secciones obligatorias completas

## Completitud de Requisitos

- [x] No quedan marcadores [NEEDS CLARIFICATION]
- [x] Los requisitos son comprobables; los detalles de contrato pendientes están identificados expresamente
- [x] Los criterios de éxito son medibles
- [x] Los criterios de éxito describen resultados observables
- [x] Todos los escenarios principales de aceptación están definidos
- [x] Se identifican los casos límite de concurrencia, autorización, transacción, reinicio e integración
- [x] Se identifican los casos límite de estado, vehículo activo, solicitudes vencidas/duplicadas, promedio y ubicación nula/simulada
- [x] Se identifican los roles `servicio` y conductor propio, y el helper de token necesario
- [x] El alcance y las exclusiones están delimitados
- [x] Se identifican los supuestos y dependencias conocidas
- [x] Se documentan los conflictos de planificación (eventos, clientes salientes, dobles, orden y cobertura)

## Preparación de la Funcionalidad

- [x] Todos los requisitos funcionales tienen una condición verificable
- [x] Las historias cubren el flujo completo, concurrencia, infraestructura, módulos vecinos y los 7 endpoints nuevos de la Iteración 2
- [x] Los resultados medibles corresponden a los criterios de éxito solicitados
- [x] No se prescribe una arquitectura de implementación para resolver los requisitos

## Notas

- La publicación de eventos del ciclo de vida completo de conductor y vehículo quedó **bloqueada**: el contrato 1.2.0 no define eventos, el backend de la Iteración 2 no los incluye y FR-013 prohíbe introducir funcionalidades de negocio nuevas. Hay que decidir con la cátedra si va a un spec propio de Backend o se retira la Historia 3/FR-007–FR-009. Mientras tanto, PR 3 no avanza.
- Si se confirma la publicación de eventos, se conservarán y reintentarán los confirmados durante una caída de RabbitMQ, con entrega al menos una vez y tolerancia a duplicados. Esa parte no se implementa en esta feature.
- Se acordó verificar M1, M4 y M5 con dobles de contrato limitados a lo que M3 expone; M6 queda fuera de la Iteración 2. La lista de operaciones y el contrato JWT/roles, incluido el rol `servicio` de solo lectura, están identificados en FR-010 y FR-021.
- Los 7 endpoints nuevos están cubiertos por la Historia 5 y FR-014 a FR-023: contrato de 17 operaciones, `410` en `CODIGOS_POR_ESTADO`, validación con `openapi-core`, casos PostgreSQL de estado/vehículo/solicitudes/concurrencia/promedio/ubicación, roles y helper `servicio`.
- Las pruebas de los 7 endpoints dependen de la migración `0002` y del backend de la Iteración 2. PR 1 y PR 2 usan endpoints existentes y pueden avanzar sin esperar. PR 4 no depende de PR 3 y se limita a lecturas de M4 y solicitudes de M5.
- El umbral vigente de CI es `65 %`; se propone `70 %` para la Iteración 2 y las pruebas nuevas de contrato e integración deben entrar al job `integracion-real-m3`.
- El README confirma que RabbitMQ no está en el Compose actual y que M1/M5 tienen detalles pendientes; no se asumieron contratos más allá de los identificados.
