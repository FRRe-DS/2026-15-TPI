/**
 * Seguridad y reglas de negocio visibles desde afuera del proceso.
 *
 * Los tests unitarios y de API usan casos de uso simulados; estos ejercitan
 * la cadena completa: token de Keycloak → dependencia de FastAPI → caso de uso
 * → PostgreSQL.
 */
import { expect, test } from "../../fixtures/api";
import { datosConductor, datosLicencia, datosVehiculo } from "../../fixtures/datos";

test("un conductor no puede aprobar su propia habilitación (403)", async ({
  apiOperador,
  apiConductor,
}) => {
  const conductor = await (
    await apiOperador.post("/conductores", { data: datosConductor() })
  ).json();

  const respuesta = await apiConductor.post(`/conductores/${conductor.id}/habilitacion`, {
    data: { accion: "APROBAR", motivo: "Intento sin rol de operador" },
  });

  expect(respuesta.status()).toBe(403);
  expect(await respuesta.json()).toEqual({
    codigo: "SIN_PERMISOS",
    mensaje: expect.any(String),
  });
});

test("un conductor no puede habilitar un vehículo (403)", async ({ apiOperador, apiConductor }) => {
  const conductor = await (
    await apiOperador.post("/conductores", { data: datosConductor() })
  ).json();
  const vehiculo = await (
    await apiOperador.post(`/conductores/${conductor.id}/vehiculos`, {
      data: datosVehiculo(),
    })
  ).json();

  const respuesta = await apiConductor.post(
    `/conductores/${conductor.id}/vehiculos/${vehiculo.id}/habilitacion`,
    { data: { accion: "APROBAR", motivo: "Intento sin rol de operador" } },
  );

  expect(respuesta.status()).toBe(403);
});

test("aprobar sin licencia vigente responde 422 y no cambia el estado", async ({
  apiOperador,
}) => {
  const conductor = await (
    await apiOperador.post("/conductores", { data: datosConductor() })
  ).json();

  const aprobacion = await apiOperador.post(`/conductores/${conductor.id}/habilitacion`, {
    data: { accion: "APROBAR", motivo: "Sin licencia cargada" },
  });
  expect(aprobacion.status()).toBe(422);
  expect((await aprobacion.json()).codigo).toBe("LICENCIA_VIGENTE_REQUERIDA");

  const detalle = await (await apiOperador.get(`/conductores/${conductor.id}`)).json();
  expect(detalle.habilitacion).toBe("PENDIENTE");
});

test("flujo completo: licencia, aprobación e historial", async ({ apiOperador }) => {
  const conductor = await (
    await apiOperador.post("/conductores", { data: datosConductor() })
  ).json();

  const licencia = await apiOperador.post(`/conductores/${conductor.id}/documentacion`, {
    data: datosLicencia(),
  });
  expect(licencia.status()).toBe(201);
  expect((await licencia.json()).estado).toBe("VIGENTE");

  const aprobacion = await apiOperador.post(`/conductores/${conductor.id}/habilitacion`, {
    data: { accion: "APROBAR", motivo: "Licencia vigente verificada" },
  });
  expect(aprobacion.status()).toBe(200);

  const habilitacion = await (
    await apiOperador.get(`/conductores/${conductor.id}/habilitacion`)
  ).json();
  expect(habilitacion.estado).toBe("APROBADA");
  expect(habilitacion.eventos.map((evento: { accion: string }) => evento.accion)).toEqual([
    "ALTA",
    "APROBAR",
  ]);
});

test("recurso inexistente responde 404 NO_ENCONTRADO", async ({ apiOperador }) => {
  const respuesta = await apiOperador.get("/conductores/999999");

  expect(respuesta.status()).toBe(404);
  expect(await respuesta.json()).toEqual({
    codigo: "NO_ENCONTRADO",
    mensaje: expect.any(String),
  });
});

test("patente duplicada responde 409 PATENTE_DUPLICADA", async ({ apiOperador }) => {
  const conductor = await (
    await apiOperador.post("/conductores", { data: datosConductor() })
  ).json();
  const vehiculo = datosVehiculo();

  const primera = await apiOperador.post(`/conductores/${conductor.id}/vehiculos`, {
    data: vehiculo,
  });
  expect(primera.status()).toBe(201);

  const segunda = await apiOperador.post(`/conductores/${conductor.id}/vehiculos`, {
    data: vehiculo,
  });

  expect(segunda.status()).toBe(409);
  expect((await segunda.json()).codigo).toBe("PATENTE_DUPLICADA");
});
