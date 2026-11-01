# Contrato de eventos de M3

## Alcance acordado

- M3 publica eventos de altas y cambios de estado de conductor y vehículo, incluidas aprobación, observación, rechazo y suspensión.
- M3 no consume eventos de otros módulos en esta funcionalidad.
- Los eventos solo representan cambios confirmados en PostgreSQL.
- El publicador entrega al menos una vez; `event_id` es estable para que los consumidores deduzcan duplicados.

## Campos pendientes de contrato bilateral

No se fijan valores por inferencia. El contrato de eventos aprobado debe especificar, como mínimo:

| Elemento | Debe acordarse |
|---|---|
| Nombre/versionado | Tipo de cada evento de alta y cambio de estado; política de evolución. |
| Exchange | Nombre, tipo, durabilidad y declaraciones/bindings necesarios. |
| Routing key | Valor para cada tipo de evento y convención de enrutamiento. |
| Envelope | Identificador, tipo, versión, fecha, agregado, productor y correlación si aplica. |
| Payload | Campos exactos, tipos, nulos, identificadores públicos y datos excluidos por privacidad. |
| Entrega | Persistencia, publisher confirms, reintentos, retención y deduplicación por `event_id`. |

La configuración de Compose, el adaptador RabbitMQ, los dobles y las aserciones CI deben derivarse del documento acordado. Los valores propuestos en pruebas no reemplazan ese acuerdo.

## Garantía transaccional

El caso de uso guarda estado, historial y outbox en una sola transacción. Un rollback no puede dejar fila publicable. Un commit confirmado conserva la fila hasta que RabbitMQ confirme recepción. El publicador marca la fila enviada después del confirm, por lo que un crash en esa ventana puede causar duplicado con idéntico `event_id`.
