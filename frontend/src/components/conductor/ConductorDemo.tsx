"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { EstadoCarga, EstadoError, EstadoVacio } from "../estados/estados";
import styles from "./ConductorDemo.module.css";

type Estado = "DESCONECTADO" | "CONECTADO" | "DISPONIBLE" | "OCUPADO";
type SolicitudEstado = "PENDIENTE" | "ACEPTADO" | "RECHAZADO";
type Punto = { latitud: number; longitud: number; fecha: string };

interface Demo {
  estado: Estado;
  solicitud: SolicitudEstado | null;
  segundos: number;
  pasajeroSubio: boolean;
  ubicacion: Punto | null;
  guardando: boolean;
  error: string | null;
  cambiarEstado: (estado: Exclude<Estado, "OCUPADO">) => void;
  responder: (aceptar: boolean) => void;
  confirmarPasajero: () => void;
  finalizarViaje: () => void;
}

const DemoContext = createContext<Demo | null>(null);
const opciones: Exclude<Estado, "OCUPADO">[] = [
  "DESCONECTADO",
  "CONECTADO",
  "DISPONIBLE",
];

export function ConductorDemoProvider({ children }: { children: ReactNode }) {
  const [estado, setEstado] = useState<Estado>("DISPONIBLE");
  const [solicitud, setSolicitud] = useState<SolicitudEstado | null>("PENDIENTE");
  const [segundos, setSegundos] = useState(90);
  const [pasajeroSubio, setPasajeroSubio] = useState(false);
  const [ubicacion, setUbicacion] = useState<Punto | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (solicitud !== "PENDIENTE") return;
    const timer = window.setInterval(() => setSegundos((actual) => {
      if (actual <= 1) {
        window.clearInterval(timer);
        return 0;
      }
      return actual - 1;
    }), 1000);
    return () => window.clearInterval(timer);
  }, [solicitud]);

  useEffect(() => {
    if (estado !== "OCUPADO") return;
    let paso = 0;
    const actualizar = () => {
      paso += 1;
      setUbicacion({
        latitud: -27.451 + paso * 0.0007,
        longitud: -58.986 + paso * 0.0004,
        fecha: new Date().toISOString(),
      });
    };
    actualizar();
    const timer = window.setInterval(actualizar, 5000);
    return () => window.clearInterval(timer);
  }, [estado]);

  const cambiarEstado = (nuevo: Exclude<Estado, "OCUPADO">) => {
    setGuardando(true);
    setError(null);
    window.setTimeout(() => {
      setEstado(nuevo);
      setGuardando(false);
    }, 250);
  };
  const responder = (aceptar: boolean) => {
    if (segundos === 0) {
      setError("La oferta venció. Ya no podés responderla.");
      return;
    }
    setSolicitud(aceptar ? "ACEPTADO" : "RECHAZADO");
    setError(null);
    if (aceptar) {
      setEstado("OCUPADO");
      setPasajeroSubio(false);
    }
  };
  const finalizarViaje = () => {
    setSolicitud(null);
    setEstado("DISPONIBLE");
    setPasajeroSubio(false);
    setUbicacion(null);
  };

  return (
    <DemoContext.Provider value={{
      estado, solicitud, segundos, pasajeroSubio, ubicacion, guardando, error,
      cambiarEstado, responder, confirmarPasajero: () => setPasajeroSubio(true), finalizarViaje,
    }}>
      {children}
    </DemoContext.Provider>
  );
}

function useDemo() {
  const demo = useContext(DemoContext);
  if (!demo) throw new Error("Las pantallas del conductor requieren ConductorDemoProvider.");
  return demo;
}

function Encabezado({ etiqueta, titulo, texto }: { etiqueta: string; titulo: string; texto: string }) {
  return (
    <header className={styles.encabezado}>
      <p className={styles.etiqueta}>{etiqueta}</p>
      <h1>{titulo}</h1>
      <p className={styles.descripcion}>{texto}</p>
    </header>
  );
}

function EstadoPill({ estado }: { estado: Estado | SolicitudEstado }) {
  return <span className={`${styles.pill} ${styles[estado.toLowerCase()]}`}>{estado}</span>;
}

export function EstadoScreen() {
  const { estado, cambiarEstado, guardando, error } = useDemo();
  return (
    <main className={styles.pagina}>
      <Encabezado etiqueta="PANEL DEL CONDUCTOR" titulo="Tu jornada, a tu ritmo" texto="Controlá cuándo recibir viajes y consultá tu estado actual." />
      <section className={styles.tarjeta} aria-labelledby="estado-titulo">
        <div className={styles.fila}>
          <div><p className={styles.etiqueta}>ESTADO ACTUAL</p><h2 id="estado-titulo">Disponibilidad</h2></div>
          <EstadoPill estado={estado} />
        </div>
        <p className={styles.texto}>Elegí tu estado operativo. Mientras tengas un viaje activo, el estado ocupado se administra automáticamente.</p>
        <div className={styles.estados}>
          {opciones.map((opcion) => (
            <button key={opcion} type="button" className={opcion === estado ? styles.seleccionado : styles.botonSecundario}
              aria-pressed={estado === opcion} disabled={guardando || estado === "OCUPADO"} onClick={() => cambiarEstado(opcion)}>
              {guardando && opcion === estado ? "Guardando…" : opcion}
            </button>
          ))}
        </div>
        {guardando && <EstadoCarga mensaje="Guardando tu estado…" />}
        {error && <EstadoError mensaje={error} />}
      </section>
      <Link className={styles.linkSiguiente} href="/solicitudes">Ver solicitudes <span aria-hidden="true">→</span></Link>
    </main>
  );
}

export function SolicitudesScreen() {
  const router = useRouter();
  const { estado, solicitud, segundos, error, responder } = useDemo();
  const pendiente = solicitud === "PENDIENTE" && segundos > 0;
  return (
    <main className={styles.pagina}>
      <Encabezado etiqueta="VIAJES" titulo="Solicitudes" texto="Revisá los detalles antes de aceptar un nuevo viaje." />
      {error && <EstadoError mensaje={error} />}
      {!solicitud && <EstadoVacio mensaje="No hay solicitudes por ahora." />}
      {solicitud && (
        <article className={styles.tarjeta}>
          <div className={styles.fila}>
            <div><p className={styles.etiqueta}>SOLICITUD #2048</p><h2>Viaje de pasajero</h2></div>
            <EstadoPill estado={solicitud} />
          </div>
          <dl className={styles.recorrido}>
            <div><dt>Origen</dt><dd>Av. Sarmiento 450</dd></div>
            <div><dt>Destino</dt><dd>Terminal de Resistencia</dd></div>
            <div><dt>Pasajero</dt><dd>Camila R.</dd></div>
          </dl>
          {pendiente ? (
            <>
              <p className={styles.temporizador}>Respondé antes de que venza · <strong>{Math.floor(segundos / 60)}:{String(segundos % 60).padStart(2, "0")}</strong></p>
              <div className={styles.acciones}>
                <button className={styles.botonPrimario} type="button" disabled={estado !== "DISPONIBLE"} onClick={() => { responder(true); router.push("/viaje"); }}>Aceptar viaje</button>
                <button className={styles.botonSecundario} type="button" onClick={() => responder(false)}>Rechazar</button>
              </div>
              {estado !== "DISPONIBLE" && <p className={styles.nota}>Conectate y ponete disponible para responder.</p>}
            </>
          ) : solicitud === "ACEPTADO" ? (
            <Link className={styles.botonPrimario} href="/viaje">Continuar al viaje <span aria-hidden="true">→</span></Link>
          ) : <EstadoVacio mensaje="Rechazaste esta solicitud." />}
          {solicitud === "PENDIENTE" && segundos === 0 && <EstadoError mensaje="Oferta vencida. Ya no se puede responder." />}
        </article>
      )}
    </main>
  );
}

export function ViajeScreen() {
  const router = useRouter();
  const { solicitud, pasajeroSubio, confirmarPasajero, finalizarViaje } = useDemo();
  const activo = solicitud === "ACEPTADO";
  return (
    <main className={styles.pagina}>
      <Encabezado etiqueta="EN CURSO" titulo="Tu viaje" texto="Acompañá cada etapa del recorrido del pasajero." />
      {!activo ? <EstadoVacio mensaje="No tenés un viaje activo. Las solicitudes aceptadas aparecen acá." /> : (
        <section className={styles.tarjeta}>
          <div className={styles.fila}><h2>Solicitud #2048</h2><EstadoPill estado="OCUPADO" /></div>
          <ol className={styles.pasos}>
            <li className={styles.completado}>Solicitud aceptada</li>
            <li className={pasajeroSubio ? styles.completado : ""}>Pasajero a bordo</li>
            <li>Viaje finalizado</li>
          </ol>
          <p className={styles.texto}>{pasajeroSubio ? "El viaje está en curso. Podés finalizarlo al llegar." : "Confirmá cuando el pasajero haya subido."}</p>
          {!pasajeroSubio ? (
            <button className={styles.botonPrimario} type="button" onClick={confirmarPasajero}>Pasajero subió</button>
          ) : (
            <button className={styles.botonPrimario} type="button" onClick={() => { finalizarViaje(); router.push("/solicitudes"); }}>Finalizar viaje</button>
          )}
        </section>
      )}
    </main>
  );
}

export function UbicacionScreen() {
  const { estado, ubicacion } = useDemo();
  return (
    <main className={styles.pagina}>
      <Encabezado etiqueta="UBICACIÓN" titulo="Ubicación compartida" texto="La posición se simula durante el viaje. No se muestra un mapa." />
      <section className={styles.tarjeta}>
        <div className={styles.fila}><h2>Último punto enviado</h2><EstadoPill estado={estado} /></div>
        {estado !== "OCUPADO" ? <EstadoVacio mensaje="La ubicación se activa automáticamente al iniciar un viaje." /> :
          ubicacion ? (
            <div className={styles.coordenada}>
              <strong>{ubicacion.latitud.toFixed(5)}, {ubicacion.longitud.toFixed(5)}</strong>
              <span>Actualizado {new Date(ubicacion.fecha).toLocaleTimeString("es-AR")}</span>
            </div>
          ) : <EstadoCarga mensaje="Esperando la primera ubicación…" />}
      </section>
    </main>
  );
}

export function LoginScreen({
  error,
  demoDisponible = false,
}: {
  error?: string;
  demoDisponible?: boolean;
}) {
  const mensaje = error === "credenciales"
    ? "Usuario o contraseña inválidos."
    : error
      ? "No se pudo iniciar sesión. Intentá nuevamente."
      : null;
  return (
    <main className={styles.login}>
      <div className={styles.loginMarca}>M3 <span>· CONDUCTORES</span></div>
      <section className={styles.tarjeta}>
        <p className={styles.etiqueta}>BIENVENIDO/A</p>
        <h1>Ingresá a tu cuenta</h1>
        <p className={styles.descripcion}>Usá tus credenciales de conductor para continuar.</p>
        {mensaje && <EstadoError mensaje={mensaje} />}
        <form className={styles.formulario} action="/api/sesion" method="post">
          <label htmlFor="usuario">Usuario</label>
          <input id="usuario" name="usuario" autoComplete="username" required />
          <label htmlFor="contrasena">Contraseña</label>
          <input id="contrasena" name="contrasena" type="password" autoComplete="current-password" required />
          <button className={styles.botonPrimario} type="submit">Iniciar sesión <span aria-hidden="true">→</span></button>
        </form>
        {demoDisponible && (
          <Link className={styles.botonSecundario} href="/estado">Explorar modo demo</Link>
        )}
      </section>
      <p className={styles.loginPie}>
        {demoDisponible
          ? "Modo demo: las pantallas usan datos de prueba."
          : "Tus credenciales se procesan de forma segura en el servidor."}
      </p>
    </main>
  );
}
