-- Ejecutar como administrador después de las migraciones, sólo en el entorno de prueba.
CREATE SCHEMA IF NOT EXISTS observability;
CREATE OR REPLACE VIEW observability.available_drivers AS
SELECT count(*)::bigint AS value
FROM public.conductor c
JOIN public.vehiculo v ON v.id_vehiculo = c.id_vehiculo_activo
 AND v.id_conductor = c.id_conductor
WHERE c.estado = 'DISPONIBLE'
 AND c.estado_habilitacion = 'APROBADA'
 AND v.estado_habilitacion = 'APROBADA';
DO $$ BEGIN
 IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'm3_otel') THEN
  CREATE ROLE m3_otel LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
 END IF;
END $$;
ALTER ROLE m3_otel SET default_transaction_read_only = on;
ALTER ROLE m3_otel SET statement_timeout = '5s';
GRANT CONNECT ON DATABASE m3 TO m3_otel;
GRANT USAGE ON SCHEMA observability TO m3_otel;
GRANT SELECT ON observability.available_drivers TO m3_otel;
