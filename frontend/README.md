# Frontend - Módulo M3 (Conductores y Vehículos)

Interfaz web construida con **Next.js 16**, **React 19** y **TypeScript 5.9** para la visualización del listado de conductores registrados en la plataforma.

## Requisitos previos

- Node.js 24 LTS
- npm

## Instalación y Configuración

1. Instalar las dependencias:

   ```bash
   npm install
   ```

2. Configurar las variables de entorno creando un archivo `.env` basado en `.env.example`:

   ```bash
   cp .env.example .env
   ```

   Completar los valores con los datos del entorno (Keycloak y API backend):

   ```env
   API_URL=http://localhost:8080/api/v1
   KEYCLOAK_URL=http://localhost:8081
   KEYCLOAK_REALM=m3
   KEYCLOAK_CLIENT_ID=frontend-client
   KEYCLOAK_CLIENT_SECRET=tu-client-secret
   TEST_USER=tu-usuario
   TEST_PASSWORD=tu-contrasenia
   ```

## Ejecución en Desarrollo

Para iniciar el servidor de desarrollo en `http://localhost:3000`:

```bash
npm run dev
```

El servidor de Next.js autentica con Keycloak utilizando las credenciales configuradas y consulta la API backend, protegiendo los secretos para que nunca lleguen al navegador.

## Scripts Disponibles

- `npm run dev`: Inicia el servidor de desarrollo de Next.js.
- `npm run build`: Compila la aplicación para producción.
- `npm run lint`: Ejecuta el linter ESLint.
- `npm test`: Ejecuta la suite de pruebas unitarias con Vitest.
