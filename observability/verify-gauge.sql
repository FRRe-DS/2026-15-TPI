-- Sólo PostgreSQL aislado del Grupo 15. Fixtures sintéticos; se revierte todo.
BEGIN;
DO $$
DECLARE
 baseline bigint;
 driver_id bigint;
 vehicle_id bigint;
 other_id bigint;
BEGIN
 SELECT value INTO baseline FROM observability.available_drivers;
 INSERT INTO conductor (dni,nombre,apellido,telefono,email,estado,estado_habilitacion)
 VALUES ('98765431','Fixture','Gauge','000','fixture@example.invalid','DISPONIBLE','APROBADA')
 RETURNING id_conductor INTO driver_id;
 INSERT INTO vehiculo (id_conductor,patente,marca,modelo,anio,tipo,estado_habilitacion)
 VALUES (driver_id,'OBS999','Fixture','Gauge',2026,'AUTO','APROBADA')
 RETURNING id_vehiculo INTO vehicle_id;
 UPDATE conductor SET id_vehiculo_activo=vehicle_id WHERE id_conductor=driver_id;
 IF (SELECT value FROM observability.available_drivers) <> baseline+1 THEN
  RAISE EXCEPTION 'No incluye conductor disponible aprobado';
 END IF;
 UPDATE conductor SET estado='OCUPADO' WHERE id_conductor=driver_id;
 IF (SELECT value FROM observability.available_drivers) <> baseline THEN
  RAISE EXCEPTION 'Cuenta ocupado';
 END IF;
 UPDATE conductor SET estado='DISPONIBLE',estado_habilitacion='PENDIENTE'
 WHERE id_conductor=driver_id;
 IF (SELECT value FROM observability.available_drivers) <> baseline THEN
  RAISE EXCEPTION 'Cuenta conductor pendiente';
 END IF;
 UPDATE conductor SET estado_habilitacion='APROBADA' WHERE id_conductor=driver_id;
 UPDATE vehiculo SET estado_habilitacion='PENDIENTE' WHERE id_vehiculo=vehicle_id;
 IF (SELECT value FROM observability.available_drivers) <> baseline THEN
  RAISE EXCEPTION 'Cuenta vehiculo pendiente';
 END IF;
 UPDATE vehiculo SET estado_habilitacion='APROBADA' WHERE id_vehiculo=vehicle_id;
 INSERT INTO conductor (dni,nombre,apellido,telefono,email)
 VALUES ('98765432','Otro','Fixture','000','otro@example.invalid')
 RETURNING id_conductor INTO other_id;
 UPDATE vehiculo SET id_conductor=other_id WHERE id_vehiculo=vehicle_id;
 IF (SELECT value FROM observability.available_drivers) <> baseline THEN
  RAISE EXCEPTION 'Cuenta vehiculo ajeno';
 END IF;
 IF has_table_privilege('m3_otel','public.conductor','SELECT') OR
    has_table_privilege('m3_otel','public.vehiculo','SELECT') OR
    has_table_privilege('m3_otel','observability.available_drivers','INSERT') THEN
  RAISE EXCEPTION 'Permisos SQL excesivos';
 END IF;
 RAISE NOTICE 'Gauge: incluye aprobado y excluye ocupado, pendientes y vehiculo ajeno; permisos OK';
END $$;
ROLLBACK;
SELECT value AS gauge_restaurado FROM observability.available_drivers;
