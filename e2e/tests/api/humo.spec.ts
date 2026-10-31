/**
 * Humo E2E de la API contra el stack real.
 *
 * Verifica lo que ningún otro test cubre: Keycloak emite el token, la API lo
 * valida contra el JWKS real y la base tiene los datos del seed.
 */
import { API_URL, claimsDelToken, expect, obtenerToken, test } from "../../fixtures/api";
import { datosConductor, datosVehiculo } from "../../fixtures/datos";

test("GET /conductores con token real devuelve los conductores del seed", async ({
  apiOperador,
}) => {
  const respuesta = await apiOperador.get("/conductores");

  expect(respuesta.status()).toBe(200);
  const conductores = await respuesta.json();
  expect(Array.isArray(conductores)).toBe(true);
  expect(conductores.length).toBeGreaterThan(0);
  expect(conductores[0]).toMatchObject({
    dni: expect.stringMatching(/^[0-9]{7,8}$/),
    habilitacion: expect.stringMatching(
      /^(PENDIENTE|OBSERVADA|APROBADA|SUSPENDIDA|RECHAZADA)$/,
    ),
  });
});

test("sin token responde 401 con el formato de error del contrato", async ({ playwright }) => {
  const contexto = await playwright.request.newContext({ baseURL: API_URL });
  const respuesta = await contexto.get("/conductores");
  await contexto.dispose();

  expect(respuesta.status()).toBe(401);
  expect(await respuesta.json()).toEqual({
    codigo: "NO_AUTENTICADO",
    mensaje: expect.any(String),
  });
});

test("el token de operador trae el rol y el id_operador numérico", async () => {
  const claims = claimsDelToken(await obtenerToken("operador"));
  const roles = (claims.realm_access as { roles?: string[] } | undefined)?.roles ?? [];

  expect(roles).toContain("operador");
  expect(typeof claims.id_operador).toBe("number");
});

test("alta de conductor: 201, Location y lectura posterior", async ({ apiOperador }) => {
  const datos = datosConductor();

  const creacion = await apiOperador.post("/conductores", { data: datos });
  expect(creacion.status()).toBe(201);
  expect(creacion.headers()["location"]).toContain("/conductores/");

  const creado = await creacion.json();
  expect(creado.dni).toBe(datos.dni);
  expect(creado.habilitacion).toBe("PENDIENTE");

  const detalle = await apiOperador.get(`/conductores/${creado.id}`);
  expect(detalle.status()).toBe(200);
  expect((await detalle.json()).dni).toBe(datos.dni);
});

test("alta de vehículo: 201 y aparece en el listado del conductor", async ({ apiOperador }) => {
  const conductor = await (await apiOperador.post("/conductores", { data: datosConductor() })).json();
  const vehiculo = datosVehiculo();

  const creacion = await apiOperador.post(`/conductores/${conductor.id}/vehiculos`, {
    data: vehiculo,
  });
  expect(creacion.status()).toBe(201);

  const listado = await apiOperador.get(`/conductores/${conductor.id}/vehiculos`);
  expect(listado.status()).toBe(200);
  const patentes = (await listado.json()).map((item: { patente: string }) => item.patente);
  expect(patentes).toContain(vehiculo.patente);
});

test("DNI duplicado responde 409 DNI_DUPLICADO", async ({ apiOperador }) => {
  const datos = datosConductor();
  const primera = await apiOperador.post("/conductores", { data: datos });
  expect(primera.status()).toBe(201);

  const segunda = await apiOperador.post("/conductores", { data: datos });

  expect(segunda.status()).toBe(409);
  expect(await segunda.json()).toEqual({
    codigo: "DNI_DUPLICADO",
    mensaje: expect.any(String),
  });
});
