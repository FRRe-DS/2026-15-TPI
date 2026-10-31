/**
 * E2E del frontend real (Next.js) contra la API y Keycloak.
 *
 * Requiere `frontend/.env.local` completo y el stack de Compose levantado.
 * El token se pide en el servidor de Next, así que acá no hay login: se valida
 * lo que ve el usuario.
 */
import { expect, test } from "../../fixtures/api";
import { datosConductor } from "../../fixtures/datos";

test("la pantalla lista conductores del seed con su badge de habilitación", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: /Módulo de Conductores/i }),
  ).toBeVisible();

  const tabla = page.getByRole("table");
  await expect(tabla).toBeVisible();
  await expect(tabla.getByRole("columnheader", { name: "DNI" })).toBeVisible();

  const filas = tabla.locator("tbody tr");
  await expect(filas.first()).toBeVisible();

  const badge = page.locator("[data-estado]").first();
  await expect(badge).toBeVisible();
  await expect(badge).toHaveAttribute(
    "data-estado",
    /^(PENDIENTE|OBSERVADA|APROBADA|SUSPENDIDA|RECHAZADA)$/,
  );
});

test("un conductor creado por la API aparece en la pantalla", async ({ page, apiOperador }) => {
  const datos = datosConductor();
  const creacion = await apiOperador.post("/conductores", { data: datos });
  expect(creacion.status()).toBe(201);

  await page.goto("/");

  const fila = page.getByRole("row", { name: new RegExp(datos.dni) });
  await expect(fila).toBeVisible();
  await expect(fila.getByText(datos.nombre, { exact: true })).toBeVisible();
});

test("la pantalla responde sin errores de consola y con un solo h1", async ({ page }) => {
  const errores: string[] = [];
  page.on("pageerror", (error) => errores.push(error.message));

  const respuesta = await page.goto("/");

  expect(respuesta?.status()).toBe(200);
  await expect(page.locator("h1")).toHaveCount(1);
  expect(errores).toEqual([]);
});
