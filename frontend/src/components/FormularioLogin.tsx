"use client";

import { useId, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import styles from "./FormularioLogin.module.css";

const MENSAJE_CREDENCIALES_INVALIDAS =
  "Credenciales inválidas. Revisá tu usuario y contraseña e intentá de nuevo.";
const MENSAJE_ERROR_GENERICO =
  "No se pudo iniciar sesión. Intentá de nuevo en unos instantes.";
const MENSAJE_SIN_CONEXION =
  "No se pudo conectar con el servidor. Revisá tu conexión e intentá de nuevo.";

interface RespuestaError {
  mensaje?: unknown;
}

async function leerMensajeDeError(respuesta: Response): Promise<string> {
  try {
    const datos = (await respuesta.json()) as RespuestaError;
    return typeof datos.mensaje === "string" && datos.mensaje
      ? datos.mensaje
      : MENSAJE_ERROR_GENERICO;
  } catch {
    return MENSAJE_ERROR_GENERICO;
  }
}

export function FormularioLogin() {
  const router = useRouter();
  const idBase = useId();
  const idUsuario = `${idBase}-usuario`;
  const idPassword = `${idBase}-password`;

  const [usuario, setUsuario] = useState("");
  const [password, setPassword] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (enviando) return;

    setError(null);
    setEnviando(true);

    try {
      // Las credenciales se validan en el route handler del servidor de Next:
      // el navegador nunca habla con Keycloak ni recibe el token.
      const respuesta = await fetch("/api/sesion", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ usuario, password }),
      });

      if (!respuesta.ok) {
        setError(
          respuesta.status === 401
            ? MENSAJE_CREDENCIALES_INVALIDAS
            : await leerMensajeDeError(respuesta)
        );
        return;
      }

      setPassword("");
      router.replace("/estado");
    } catch {
      setError(MENSAJE_SIN_CONEXION);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section className={styles.tarjeta} aria-labelledby={`${idBase}-titulo`}>
      <header className={styles.encabezado}>
        <h1 id={`${idBase}-titulo`} className={styles.titulo}>
          Módulo M3
        </h1>
        <p className={styles.subtitulo}>Acceso de Conductores</p>
      </header>

      <form className={styles.formulario} onSubmit={enviar} noValidate>
        {error ? (
          <p className={styles.error} role="alert">
            {error}
          </p>
        ) : null}

        <div className={styles.campo}>
          <label className={styles.etiqueta} htmlFor={idUsuario}>
            Usuario
          </label>
          <input
            className={styles.input}
            id={idUsuario}
            name="usuario"
            type="text"
            autoComplete="username"
            autoCapitalize="none"
            autoFocus
            required
            value={usuario}
            disabled={enviando}
            onChange={(evento) => setUsuario(evento.target.value)}
          />
        </div>

        <div className={styles.campo}>
          <label className={styles.etiqueta} htmlFor={idPassword}>
            Contraseña
          </label>
          <input
            className={styles.input}
            id={idPassword}
            name="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            disabled={enviando}
            onChange={(evento) => setPassword(evento.target.value)}
          />
        </div>

        <button
          className={styles.boton}
          type="submit"
          disabled={enviando}
          aria-busy={enviando}
        >
          {enviando ? "Verificando credenciales..." : "Iniciar sesión"}
        </button>
      </form>
    </section>
  );
}
