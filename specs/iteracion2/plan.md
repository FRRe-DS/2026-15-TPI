# Plan de Implementación: Iteración 2 — Plataforma y Seguridad

**Rama**: `docs/planificacion-iteracion2` | **Fecha**: 2026-11-03

**Entrada**: alcance operativo de la Iteración 1, README del módulo y definición de la plataforma M3.

## Resumen

La Iteración 2 cierra la parte de la plataforma, seguridad y operación del servicio M3 que quedó pendiente en la Iteración 1. El objetivo principal es completar el ciclo funcional del módulo en producción local y en entorno de validación: actualización de estado y ubicación, consumo de solicitudes y despachos, integración con viajes y calificación, y cierre de la capa de seguridad y CI de la plataforma.

La planificación se organiza en tres líneas paralelas:

1. Plataforma y entorno: Docker Compose, variables de entorno, seed, Keycloak y soporte operativo del módulo.
2. Seguridad y autorización: validación JWT real, roles, políticas por endpoint y control de integración con módulos externos.
3. Integración y calidad: pruebas de contrato, concurrencia, smoke de Compose y cierre de la cobertura de la API.

---

## Objetivos de la Iteración 2

### 1) Completar la plataforma de M3

- Dejar operativa la parte funcional pendiente del servicio: estado, ubicación, solicitudes y viajes.
- Mantener el arranque con un único comando de Docker Compose, con contenedores reproducibles y configurables por variables de entorno.
- Alinear el entorno local con el contrato OpenAPI y con las reglas de negocio del módulo.

### 2) Cerrar la capa de seguridad

- Verificar el JWT emitido por Keycloak y validar issuer, audiencia, firma y expiración.
- Mantener el manejo de usuarios y roles (`operador` y `conductor`) en dependencias compartidas y centralizadas.
- Proteger todos los endpoints del módulo con la política de acceso definida en el contrato y en la especificación.
- Evitar secretos en el repositorio y mantener la configuración de infraestructura por variables de entorno.

### 3) Preparar la operación a nivel de calidad

- Automatizar pruebas de API y de integración contra infraestructura real.
- Cubrir el comportamiento de concurrencia, errores y casos de borde de seguridad.
- Verificar la protección de ramas y la calidad del CI antes del cierre de la iteración.

---

## Alcance funcional planificado

### Plataforma / entorno

- Ajustes del `docker-compose.yml` para levantar correctamente API, PostgreSQL y Keycloak.
- Consolidación de variables de entorno y `.env.example` con parámetros seguros y reproducibles.
- Seeds de datos de prueba necesarios para validación de conductores, vehículos, estados y roles.
- Validación de flujo local completo con la API real y la autenticación del realm.
- Smoke tests de Compose para verificar que la plataforma puede levantarse sin intervención manual.

### Seguridad

- Validación del token JWT con `PyJWT` y caché de JWKS.
- Control por rol (`requerir_usuario`, `requerir_operador`) en los endpoints sensibles.
- Verificación de error de autenticación: token ausente, mal formado, expirado, con firma inválida o de otro emisor.
- Restricción de acciones de habilitación solo para operadores y validación del `id_operador` proveniente del token.
- Aseguramiento de que la configuración de Keycloak y la API no exponen secretos ni credenciales en el repositorio.

### Integración con otros módulos

- Uso de `latitud` y `longitud` para estado y ubicación de conductores, con forma de lectura y actualización según el contrato.
- Integración con M4 para disponibilidad y ubicación.
- Integración de consultas y aceptación de solicitudes con M5.
- Consumo de endpoints de viajes y cierre de ciclo de vida definidos por M6.
- Manejo explícito de estados de viaje, calificación y coordinación del conductor según el contrato.

---

## Plan de trabajo por área

| Área | Objetivo | Entregables esperados | Criterio de cierre |
|---|---|---|---|
| Plataforma | Dejar la infraestructura ejecutable y estable | Compose, env, seed, Keycloak, smoke tests | arranque reproducible con un comando |
| Seguridad | Proteger acceso y validación JWT | `backend/app/api/seguridad.py`, pruebas de auth y roles | escenarios de 401/403 cubiertos |
| Integración | Completar contract y comportamiento real | endpoints de estado, ubicación, solicitudes, viajes, calificación | validación con OpenAPI y tests |
| Calidad | Cubrir pruebas y CI | cobertura, tests concurrentes y de humo | pipeline en verde y sin regresiones |

### Flujo de ejecución sugerido

1. Definir y ajustar el contrato de la Iteración 2 en `docs/contract/openapi.yaml`.
2. Reforzar la capa de seguridad con pruebas de autenticación y roles.
3. Implementar la actualización de estado/ubicación y la lógica de solicitudes/viajes.
4. Validar integración con M4, M5 y M6 usando datos reales del entorno.
5. Ejecutar smoke tests, concurrencia y validación de cobertura en CI.

---

## Decisiones de diseño

### 1) Seguridad por capas

La decisión principal es separar la validación del token y la autorización de la lógica de negocio. La API debe validar identidad y rol antes de invocar el caso de uso, y la regla de negocio debe seguir centrada en el dominio y no en la infraestructura.

### 2) Plataforma como parte del producto

La infraestructura no queda como soporte opcional: se considera parte del alcance funcional. El servicio no puede considerarse entregado si no se puede levantar con Compose y si no se valida en un entorno real con tokens y datos de prueba.

### 3) Calidad como requisito de entrega

La Iteración 2 no agrega funciones sin cobertura. La verificación pasa por los mismos principios de la constitución: TDD, cobertura, tests de integración y requerimientos de seguridad.

---

## Criterios de aceptación

La iteración queda cerrada cuando se cumplen estas condiciones:

- El entorno local levanta con Docker Compose sin pasos manuales complejos.
- La API valida tokens JWT reales emitidos por Keycloak y rechazará errores de autenticación.
- Los endpoints con permisos de operador y conductor responden con los códigos esperados (`200`, `401`, `403`, `404`, `409`, etc.).
- Las operaciones de estado, ubicación, solicitudes y calificación quedan cubiertas por tests.
- La cobertura y la validación de contrato se mantienen en verde en CI.
- La protección de ramas y la automatización del pipeline están en funcionamiento.

---

## Riesgos y dependencias

### Riesgos principales

- Desalineación entre el contrato y la implementación real.
- Dependencias cruzadas entre M3 y M4/M5/M6 sin contrato claro.
- Casos de concurrencia en estados de habilitación, solicitudes o viajes.
- Falsos positivos de validación si la autenticación no se prueba con tokens reales.

### Dependencias de sincronización

- OpenAPI actualizado y consistente con la implementación.
- Realm de Keycloak y datos de prueba compartidos.
- Reglas de negocio informadas por los casos de uso y el modelo de dominio.
- Revisión de la API y del entorno antes de merge a la rama de integración.

---

## Resultado esperado

La Iteración 2 deja a M3 con una plataforma ejecutable, segura y verificable: la API autenticada por Keycloak, la autorización por rol integrada, la infraestructura validada con Compose y la parte funcional restante operando con reglas claras de negocio y pruebas automatizadas.
