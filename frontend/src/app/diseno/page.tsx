"use client";

import React, { useState } from "react";
import styles from "./diseno.module.css";

type ScreenId = "login" | "estado" | "pedidos" | "viaje" | "ubicacion" | "tokens";
type StateFilter = "todos" | "nominal" | "carga" | "error" | "vacio";

export default function DisenoPage() {
  const [activeScreen, setActiveScreen] = useState<ScreenId>("login");
  const [activeState, setActiveState] = useState<StateFilter>("todos");

  return (
    <div className={styles.disenoContainer}>
      {/* Encabezado del Visor de Prototipo */}
      <header className={styles.header}>
        <div className={styles.headerTop}>
          <div>
            <h1 className={styles.title}>Prototipo Visual — App del Conductor</h1>
            <p className={styles.description}>
              Iteración 2 (T701–T702) · Módulo M3 Conductores y Vehículos
            </p>
          </div>
          <span className={styles.badgeTag}>Ruta aislada: /diseno</span>
        </div>

        {/* Selector de Pantallas */}
        <nav className={styles.navPills} aria-label="Pantallas a revisar">
          <button
            type="button"
            className={`${styles.navButton} ${activeScreen === "login" ? styles.navButtonActive : ""}`}
            onClick={() => setActiveScreen("login")}
          >
            1. Login (US1)
          </button>
          <button
            type="button"
            className={`${styles.navButton} ${activeScreen === "estado" ? styles.navButtonActive : ""}`}
            onClick={() => setActiveScreen("estado")}
          >
            2. Estado Conductor (US2)
          </button>
          <button
            type="button"
            className={`${styles.navButton} ${activeScreen === "pedidos" ? styles.navButtonActive : ""}`}
            onClick={() => setActiveScreen("pedidos")}
          >
            3. Pedidos Entrantes (US3)
          </button>
          <button
            type="button"
            className={`${styles.navButton} ${activeScreen === "viaje" ? styles.navButtonActive : ""}`}
            onClick={() => setActiveScreen("viaje")}
          >
            4. Viaje en Curso (US4)
          </button>
          <button
            type="button"
            className={`${styles.navButton} ${activeScreen === "ubicacion" ? styles.navButtonActive : ""}`}
            onClick={() => setActiveScreen("ubicacion")}
          >
            5. Ubicación Simulada (US5)
          </button>
          <button
            type="button"
            className={`${styles.navButton} ${activeScreen === "tokens" ? styles.navButtonActive : ""}`}
            onClick={() => setActiveScreen("tokens")}
          >
            Tokens Visuales
          </button>
        </nav>

        {/* Filtro de Estados (Nominal / Carga / Error / Vacío) */}
        {activeScreen !== "tokens" && (
          <div className={styles.stateFilters}>
            <span className={styles.stateLabel}>Filtrar estados:</span>
            <button
              type="button"
              className={`${styles.stateButton} ${activeState === "todos" ? styles.stateButtonActive : ""}`}
              onClick={() => setActiveState("todos")}
            >
              Ver los 4 estados
            </button>
            <button
              type="button"
              className={`${styles.stateButton} ${activeState === "nominal" ? styles.stateButtonActive : ""}`}
              onClick={() => setActiveState("nominal")}
            >
              Nominal
            </button>
            <button
              type="button"
              className={`${styles.stateButton} ${activeState === "carga" ? styles.stateButtonActive : ""}`}
              onClick={() => setActiveState("carga")}
            >
              Carga
            </button>
            <button
              type="button"
              className={`${styles.stateButton} ${activeState === "error" ? styles.stateButtonActive : ""}`}
              onClick={() => setActiveState("error")}
            >
              Error
            </button>
            <button
              type="button"
              className={`${styles.stateButton} ${activeState === "vacio" ? styles.stateButtonActive : ""}`}
              onClick={() => setActiveState("vacio")}
            >
              Vacío
            </button>
          </div>
        )}
      </header>

      {/* Renderizado de Pantallas y Estados */}
      <main>
        {activeScreen === "login" && (
          <ScreenContainer title="Pantalla 1: Iniciar Sesión (US1)" filter={activeState}>
            {{
              nominal: <LoginNominal />,
              carga: <LoginCarga />,
              error: <LoginError />,
              vacio: <LoginVacio />,
            }}
          </ScreenContainer>
        )}

        {activeScreen === "estado" && (
          <ScreenContainer title="Pantalla 2: Ponerse en Línea / Estado (US2)" filter={activeState}>
            {{
              nominal: <EstadoNominal />,
              carga: <EstadoCarga />,
              error: <EstadoError />,
              vacio: <EstadoVacio />,
            }}
          </ScreenContainer>
        )}

        {activeScreen === "pedidos" && (
          <ScreenContainer title="Pantalla 3: Pedidos Entrantes / Solicitudes (US3)" filter={activeState}>
            {{
              nominal: <PedidosNominal />,
              carga: <PedidosCarga />,
              error: <PedidosError />,
              vacio: <PedidosVacio />,
            }}
          </ScreenContainer>
        )}

        {activeScreen === "viaje" && (
          <ScreenContainer title="Pantalla 4: Viaje en Curso (US4)" filter={activeState}>
            {{
              nominal: <ViajeNominal />,
              carga: <ViajeCarga />,
              error: <ViajeError />,
              vacio: <ViajeVacio />,
            }}
          </ScreenContainer>
        )}

        {activeScreen === "ubicacion" && (
          <ScreenContainer title="Pantalla 5: Ubicación Simulada (US5)" filter={activeState}>
            {{
              nominal: <UbicacionNominal />,
              carga: <UbicacionCarga />,
              error: <UbicacionError />,
              vacio: <UbicacionVacio />,
            }}
          </ScreenContainer>
        )}

        {activeScreen === "tokens" && <TokensView />}
      </main>
    </div>
  );
}

/* ==========================================================
   CONTENEDOR DE ESTADOS (GRID / COMPARATIVA)
   ========================================================== */
interface ScreenContainerProps {
  title: string;
  filter: StateFilter;
  children: {
    nominal: React.ReactNode;
    carga: React.ReactNode;
    error: React.ReactNode;
    vacio: React.ReactNode;
  };
}

function ScreenContainer({ title, filter, children }: ScreenContainerProps) {
  return (
    <div>
      <h2 style={{ fontSize: "1.25rem", margin: "0 0 1rem 0", color: "#1e3a8a" }}>{title}</h2>
      <div className={styles.statesGrid}>
        {(filter === "todos" || filter === "nominal") && (
          <div className={styles.stateCard}>
            <div className={styles.stateCardHeader}>
              <h3 className={styles.stateCardTitle}>Estado Nominal</h3>
              <span className={`${styles.stateBadge} ${styles.badgeNominal}`}>Normal</span>
            </div>
            <div className={styles.stateCardBody}>{children.nominal}</div>
          </div>
        )}

        {(filter === "todos" || filter === "carga") && (
          <div className={styles.stateCard}>
            <div className={styles.stateCardHeader}>
              <h3 className={styles.stateCardTitle}>Estado de Carga</h3>
              <span className={`${styles.stateBadge} ${styles.badgeCarga}`}>Loading</span>
            </div>
            <div className={styles.stateCardBody}>{children.carga}</div>
          </div>
        )}

        {(filter === "todos" || filter === "error") && (
          <div className={styles.stateCard}>
            <div className={styles.stateCardHeader}>
              <h3 className={styles.stateCardTitle}>Estado de Error</h3>
              <span className={`${styles.stateBadge} ${styles.badgeError}`}>Alert</span>
            </div>
            <div className={styles.stateCardBody}>{children.error}</div>
          </div>
        )}

        {(filter === "todos" || filter === "vacio") && (
          <div className={styles.stateCard}>
            <div className={styles.stateCardHeader}>
              <h3 className={styles.stateCardTitle}>Estado Vacío</h3>
              <span className={`${styles.stateBadge} ${styles.badgeVacio}`}>Empty</span>
            </div>
            <div className={styles.stateCardBody}>{children.vacio}</div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ==========================================================
   1. PANTALLA: LOGIN (US1)
   ========================================================== */
function LoginNominal() {
  return (
    <div className={styles.loginBox}>
      <div className={styles.brandHeader}>
        <h4 className={styles.brandTitle}>Módulo M3</h4>
        <p className={styles.brandSubtitle}>Acceso de Conductores</p>
      </div>
      <form onSubmit={(e) => e.preventDefault()}>
        <div className={styles.formGroup}>
          <label htmlFor="user-nominal" className={styles.formLabel}>
            Usuario o ID de Conductor
          </label>
          <input
            id="user-nominal"
            type="text"
            className={styles.formInput}
            defaultValue="conductor.m3"
            placeholder="ej. conductor.m3"
          />
        </div>
        <div className={styles.formGroup}>
          <label htmlFor="pass-nominal" className={styles.formLabel}>
            Contraseña
          </label>
          <input
            id="pass-nominal"
            type="password"
            className={styles.formInput}
            defaultValue="password123"
          />
        </div>
        <button type="submit" className={styles.btnPrimary}>
          Iniciar Sesión
        </button>
      </form>
      <p className={styles.loginFooterNotice}>
        Autenticación segura contra Keycloak (realm m3)
      </p>
    </div>
  );
}

function LoginCarga() {
  return (
    <div className={styles.loginBox}>
      <div className={styles.brandHeader}>
        <h4 className={styles.brandTitle}>Módulo M3</h4>
        <p className={styles.brandSubtitle}>Acceso de Conductores</p>
      </div>
      <form onSubmit={(e) => e.preventDefault()}>
        <div className={styles.formGroup}>
          <label className={styles.formLabel}>Usuario o ID de Conductor</label>
          <input
            type="text"
            className={styles.formInput}
            value="conductor.m3"
            disabled
          />
        </div>
        <div className={styles.formGroup}>
          <label className={styles.formLabel}>Contraseña</label>
          <input
            type="password"
            className={styles.formInput}
            value="••••••••••••"
            disabled
          />
        </div>
        <button type="button" className={styles.btnPrimary} disabled aria-busy="true">
          <span className={styles.spinner} style={{ width: 16, height: 16, borderWidth: 2, margin: 0 }} />
          <span>Verificando credenciales...</span>
        </button>
      </form>
      <div className={styles.loadingStateBox} style={{ padding: "1rem 0" }}>
        <p style={{ margin: 0, fontSize: "0.875rem" }}>Conectando con el servidor de autenticación...</p>
      </div>
    </div>
  );
}

function LoginError() {
  return (
    <div className={styles.loginBox}>
      <div className={styles.brandHeader}>
        <h4 className={styles.brandTitle}>Módulo M3</h4>
        <p className={styles.brandSubtitle}>Acceso de Conductores</p>
      </div>

      <div role="alert" className={styles.alertError}>
        <div>
          <h5 className={styles.alertErrorTitle}>Credenciales inválidas</h5>
          <p className={styles.alertErrorMessage}>
            El usuario o la contraseña ingresados no coinciden con una cuenta habilitada. Verifique sus datos e intente nuevamente.
          </p>
        </div>
      </div>

      <form onSubmit={(e) => e.preventDefault()}>
        <div className={styles.formGroup}>
          <label htmlFor="user-error" className={styles.formLabel}>
            Usuario o ID de Conductor
          </label>
          <input
            id="user-error"
            type="text"
            className={`${styles.formInput} ${styles.formInputError}`}
            defaultValue="conductor.invalido"
          />
        </div>
        <div className={styles.formGroup}>
          <label htmlFor="pass-error" className={styles.formLabel}>
            Contraseña
          </label>
          <input
            id="pass-error"
            type="password"
            className={`${styles.formInput} ${styles.formInputError}`}
            defaultValue="erronea"
          />
        </div>
        <button type="submit" className={styles.btnPrimary}>
          Reintentar Acceso
        </button>
      </form>
    </div>
  );
}

function LoginVacio() {
  return (
    <div className={styles.loginBox}>
      <div className={styles.emptyStateBox}>
        <h4 className={styles.emptyStateTitle}>Sesión No Iniciada</h4>
        <p className={styles.emptyStateText}>
          Para operar en la plataforma M3 es obligatorio ingresar sus credenciales de conductor.
        </p>
      </div>
      <form style={{ marginTop: "1.5rem" }} onSubmit={(e) => e.preventDefault()}>
        <div className={styles.formGroup}>
          <label htmlFor="user-empty" className={styles.formLabel}>
            Usuario
          </label>
          <input
            id="user-empty"
            type="text"
            className={styles.formInput}
            placeholder="Ingrese su usuario..."
          />
        </div>
        <div className={styles.formGroup}>
          <label htmlFor="pass-empty" className={styles.formLabel}>
            Contraseña
          </label>
          <input
            id="pass-empty"
            type="password"
            className={styles.formInput}
            placeholder="Ingrese su clave..."
          />
        </div>
        <button type="submit" className={styles.btnPrimary}>
          Iniciar Sesión
        </button>
      </form>
    </div>
  );
}

/* ==========================================================
   2. PANTALLA: ESTADO DEL CONDUCTOR (US2)
   ========================================================== */
function EstadoNominal() {
  return (
    <div>
      <div className={styles.driverHeaderCard}>
        <div className={styles.driverNameRow}>
          <h4 className={styles.driverName}>Juan Carlos Pérez</h4>
          <span className={`${styles.statusPillLarge} ${styles.statusPillConectado}`} style={{ fontSize: "0.75rem", padding: "2px 8px" }}>
            Habilitado
          </span>
        </div>
        <div className={styles.driverMeta}>
          <span>DNI: 30.456.789</span>
          <span>Vehículo: <strong>VEH-402</strong> (Toyota Corolla)</span>
          <span>Puntaje: <strong>4.85 ★</strong> (128 calificaciones)</span>
        </div>
      </div>

      <div className={styles.statusIndicatorBox}>
        <div className={styles.currentStatusLabel}>Estado Operativo Actual</div>
        <span className={`${styles.statusPillLarge} ${styles.statusPillConectado}`}>
          CONECTADO
        </span>
      </div>

      <div className={styles.statusButtonGroup}>
        <button type="button" className={styles.btnStatusAction}>
          <span>Desconectarme del servicio</span>
          <span style={{ color: "#475569" }}>DESCONECTADO</span>
        </button>
        <button type="button" className={`${styles.btnStatusAction} ${styles.btnStatusActionActive}`}>
          <span>Permanecer conectado en espera</span>
          <span style={{ fontWeight: "bold" }}>CONECTADO (Actual)</span>
        </button>
        <button type="button" className={`${styles.btnStatusAction} ${styles.btnStatusActionDisponible}`}>
          <span>Ponerse disponible para viajes</span>
          <span style={{ fontWeight: "bold", color: "#14532d" }}>DISPONIBLE →</span>
        </button>
      </div>
      <p style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "1rem", textAlign: "center" }}>
        * Nota de especificación: El estado OCUPADO se asigna automáticamente al aceptar un pedido y no se ofrece manualmente.
      </p>
    </div>
  );
}

function EstadoCarga() {
  return (
    <div>
      <div className={styles.driverHeaderCard}>
        <div className={styles.skeletonBar} style={{ width: "60%", height: 20 }} />
        <div className={styles.skeletonBar} style={{ width: "90%", height: 14 }} />
      </div>

      <div className={styles.loadingStateBox}>
        <div className={styles.spinner} />
        <p style={{ fontWeight: 600, margin: "0 0 0.5rem 0", color: "#0f172a" }}>
          Actualizando estado operativo...
        </p>
        <p style={{ margin: 0, fontSize: "0.875rem" }}>
          Comunicando nuevo estado <code>DISPONIBLE</code> al servidor M3.
        </p>
      </div>

      <div className={styles.statusButtonGroup} style={{ opacity: 0.6 }}>
        <button type="button" className={styles.btnStatusAction} disabled>
          <span>DESCONECTADO</span>
        </button>
        <button type="button" className={styles.btnStatusAction} disabled>
          <span>CONECTADO</span>
        </button>
        <button type="button" className={styles.btnStatusAction} disabled>
          <span>DISPONIBLE</span>
        </button>
      </div>
    </div>
  );
}

function EstadoError() {
  return (
    <div>
      <div role="alert" className={styles.alertError}>
        <div>
          <h5 className={styles.alertErrorTitle}>Error 422: CONDUCTOR_NO_HABILITADO</h5>
          <p className={styles.alertErrorMessage}>
            No es posible cambiar al estado DISPONIBLE. Su cuenta posee la habilitación municipal en estado PENDIENTE o no cuenta con un vehículo activo verificado.
          </p>
        </div>
      </div>

      <div className={styles.driverHeaderCard}>
        <div className={styles.driverNameRow}>
          <h4 className={styles.driverName}>Juan Carlos Pérez</h4>
          <span className={`${styles.statusPillLarge} ${styles.statusPillDesconectado}`} style={{ fontSize: "0.75rem", padding: "2px 8px", backgroundColor: "#fffbeb", color: "#78350f" }}>
            Habilitación Pendiente
          </span>
        </div>
        <div className={styles.driverMeta}>
          <span>DNI: 30.456.789</span>
          <span>Vehículo: <em>Sin asignar</em></span>
        </div>
      </div>

      <div className={styles.statusButtonGroup}>
        <button type="button" className={`${styles.btnStatusAction} ${styles.btnStatusActionActive}`}>
          <span>Permanecer DESCONECTADO</span>
          <span style={{ fontWeight: "bold" }}>DESCONECTADO</span>
        </button>
        <button type="button" className={styles.btnStatusAction} style={{ opacity: 0.5, cursor: "not-allowed" }} disabled>
          <span>Ponerse DISPONIBLE (Bloqueado)</span>
          <span style={{ color: "#b91c1c" }}>No autorizado</span>
        </button>
      </div>
    </div>
  );
}

function EstadoVacio() {
  return (
    <div>
      <div className={styles.emptyStateBox}>
        <h4 className={styles.emptyStateTitle}>Sin Información de Conductor</h4>
        <p className={styles.emptyStateText}>
          No se pudieron recuperar los datos operativos de su sesión. Por favor reingrese o solicite habilitación al operador de base.
        </p>
      </div>
    </div>
  );
}

/* ==========================================================
   3. PANTALLA: PEDIDOS ENTRANTES / SOLICITUDES (US3)
   ========================================================== */
function PedidosNominal() {
  return (
    <div className={styles.ordersList}>
      {/* Solicitud 1: PENDIENTE con cuenta regresiva */}
      <div className={`${styles.orderCard} ${styles.orderCardPending}`}>
        <div className={styles.orderHeaderRow}>
          <span className={styles.orderFare}>$ 4.250</span>
          <span className={styles.countdownBadge}>
            ⏱ Vence en 38s
          </span>
        </div>
        <div className={styles.orderRouteInfo}>
          <div className={styles.routePoint}>
            <span className={styles.routeIcon}>●</span>
            <span><strong>Origen:</strong> Av. San Martín 1540, Florida</span>
          </div>
          <div className={styles.routePoint}>
            <span className={styles.routeIcon}>▼</span>
            <span><strong>Destino:</strong> Maipú 850, Retiro (Distancia: 4.8 km)</span>
          </div>
          <div style={{ marginTop: "0.5rem", fontSize: "0.75rem", color: "#64748b" }}>
            Pasajero: Ignacio V. · Solicitud #REQ-9901
          </div>
        </div>
        <div className={styles.orderActionRow}>
          <button type="button" className={styles.btnAccept}>
            Aceptar Viaje
          </button>
          <button type="button" className={styles.btnReject}>
            Rechazar
          </button>
        </div>
      </div>

      {/* Solicitud 2: ACEPTADO */}
      <div className={styles.orderCard}>
        <div className={styles.orderHeaderRow}>
          <span className={styles.orderFare}>$ 3.800</span>
          <span className={`${styles.statusPillLarge} ${styles.statusPillDisponible}`} style={{ fontSize: "0.75rem", padding: "2px 8px" }}>
            ACEPTADO
          </span>
        </div>
        <div className={styles.orderRouteInfo}>
          <div className={styles.routePoint}>
            <span className={styles.routeIcon}>●</span>
            <span>Cabildo 2040 → Juramento 1800</span>
          </div>
          <p style={{ margin: "4px 0 0 0", fontSize: "0.75rem", color: "#64748b" }}>
            Aceptado a las 15:42 · En preparación
          </p>
        </div>
      </div>

      {/* Solicitud 3: VENCIDA */}
      <div className={styles.orderCard} style={{ opacity: 0.65 }}>
        <div className={styles.orderHeaderRow}>
          <span style={{ fontSize: "1rem", fontWeight: 600, color: "#64748b" }}>$ 2.900</span>
          <span className={`${styles.statusPillLarge} ${styles.statusPillDesconectado}`} style={{ fontSize: "0.75rem", padding: "2px 8px" }}>
            VENCIDA
          </span>
        </div>
        <div className={styles.orderRouteInfo}>
          <p style={{ margin: 0 }}>Av. Santa Fe 3200 → Callao 1100</p>
          <p style={{ margin: "4px 0 0 0", fontSize: "0.75rem", color: "#64748b" }}>
            Oferta expirada. Botones de acción inhabilitados.
          </p>
        </div>
      </div>
    </div>
  );
}

function PedidosCarga() {
  return (
    <div>
      <div className={styles.loadingStateBox}>
        <div className={styles.spinner} />
        <p style={{ fontWeight: 600, margin: "0 0 0.5rem 0", color: "#0f172a" }}>
          Buscando solicitudes entrantes...
        </p>
        <p style={{ margin: 0, fontSize: "0.875rem" }}>
          Consultando pedidos asignados en tiempo real.
        </p>
      </div>
      <div className={styles.ordersList} style={{ opacity: 0.5 }}>
        <div className={styles.orderCard}>
          <div className={styles.skeletonBar} style={{ width: "30%", height: 24 }} />
          <div className={styles.skeletonBar} style={{ width: "80%", height: 16 }} />
          <div className={styles.skeletonBar} style={{ width: "60%", height: 16 }} />
        </div>
      </div>
    </div>
  );
}

function PedidosError() {
  return (
    <div>
      <div role="alert" className={styles.alertError}>
        <div>
          <h5 className={styles.alertErrorTitle}>Error 410: Oferta Vencida</h5>
          <p className={styles.alertErrorMessage}>
            La solicitud de viaje seleccionada ya no se encuentra disponible. Expiró el tiempo de respuesta o fue tomada por otro conductor.
          </p>
        </div>
      </div>
      <div role="alert" className={styles.alertError} style={{ backgroundColor: "#fffbeb", borderColor: "#fcd34d", color: "#78350f" }}>
        <div>
          <h5 className={styles.alertErrorTitle} style={{ color: "#78350f" }}>Conflicto de asignación (409)</h5>
          <p className={styles.alertErrorMessage}>
            No fue posible confirmar la solicitud. El estado operativo cambió durante la confirmación.
          </p>
        </div>
      </div>
    </div>
  );
}

function PedidosVacio() {
  return (
    <div className={styles.emptyStateBox}>
      <h4 className={styles.emptyStateTitle}>No hay solicitudes</h4>
      <p className={styles.emptyStateText}>
        No tienes viajes pendientes en este momento. Mantente en estado <strong>DISPONIBLE</strong> para recibir nuevos pedidos en tu zona.
      </p>
    </div>
  );
}

/* ==========================================================
   4. PANTALLA: VIAJE EN CURSO (US4)
   ========================================================== */
function ViajeNominal() {
  const [passengerBoarded, setPassengerBoarded] = useState(false);

  return (
    <div className={styles.tripContainer}>
      <div className={styles.tripStatusHeader}>
        <div>
          <span className={styles.tripId}>Viaje #TRIP-7734</span>
          <div style={{ fontSize: "0.75rem", color: "#64748b" }}>Tarifa pactada: $ 4.250</div>
        </div>
        <span className={`${styles.statusPillLarge} ${styles.statusPillOcupado}`}>
          OCUPADO
        </span>
      </div>

      <div style={{ backgroundColor: "#f8fafc", padding: "0.75rem", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
        <p style={{ margin: "0 0 4px 0", fontSize: "0.875rem" }}><strong>Pasajera:</strong> Laura Gómez</p>
        <p style={{ margin: 0, fontSize: "0.75rem", color: "#475569" }}>Origen: Av. San Martín 1540 → Destino: Maipú 850</p>
      </div>

      {/* Stepper de progresión */}
      <div className={styles.stepperContainer}>
        <div className={styles.stepperItem}>
          <span className={styles.stepperIconDone}>✓</span>
          <span className={styles.stepperTextDone}>1. Conductor en camino al punto de partida</span>
        </div>
        <div className={styles.stepperItem}>
          <span className={passengerBoarded ? styles.stepperIconDone : styles.stepperIconActive}>
            {passengerBoarded ? "✓" : "2"}
          </span>
          <span className={passengerBoarded ? styles.stepperTextDone : styles.stepperTextActive}>
            2. Pasajero a bordo del vehículo
          </span>
        </div>
        <div className={styles.stepperItem}>
          <span className={passengerBoarded ? styles.stepperIconActive : styles.stepperIconPending}>3</span>
          <span className={passengerBoarded ? styles.stepperTextActive : styles.stepperTextPending}>
            3. Viaje hacia el destino final
          </span>
        </div>
      </div>

      {/* Acciones del Viaje */}
      <div>
        <button
          type="button"
          className={styles.btnTripAdvance}
          onClick={() => setPassengerBoarded(true)}
          disabled={passengerBoarded}
        >
          Pasajero subió{passengerBoarded ? " ✓" : ""}
        </button>
        <button
          type="button"
          className={styles.btnTripFinish}
          disabled={!passengerBoarded}
        >
          Finalizar viaje
        </button>
      </div>
      <p style={{ fontSize: "0.75rem", color: "#64748b", margin: 0, textAlign: "center" }}>
        Al finalizar, la aplicación solicita el estado DISPONIBLE y retorna al listado de solicitudes.
      </p>
    </div>
  );
}

function ViajeCarga() {
  return (
    <div>
      <div className={styles.loadingStateBox}>
        <div className={styles.spinner} />
        <p style={{ fontWeight: 600, margin: "0 0 0.5rem 0", color: "#0f172a" }}>
          Finalizando viaje...
        </p>
        <p style={{ margin: 0, fontSize: "0.875rem" }}>
          Registrando fin de recorrido y actualizando a estado DISPONIBLE.
        </p>
      </div>
      <div style={{ opacity: 0.6 }}>
        <button type="button" className={styles.btnTripFinish} disabled>
          Procesando cierre de viaje...
        </button>
      </div>
    </div>
  );
}

function ViajeError() {
  return (
    <div>
      <div role="alert" className={styles.alertError}>
        <div>
          <h5 className={styles.alertErrorTitle}>Error al sincronizar viaje</h5>
          <p className={styles.alertErrorMessage}>
            No se pudo registrar la finalización del viaje en el servidor central (500). Verifique su conexión y reintente el cierre.
          </p>
        </div>
      </div>
      <button type="button" className={styles.btnTripFinish}>
        Reintentar Finalizar Viaje
      </button>
    </div>
  );
}

function ViajeVacio() {
  return (
    <div className={styles.emptyStateBox}>
      <h4 className={styles.emptyStateTitle}>Sin viaje en curso</h4>
      <p className={styles.emptyStateText}>
        No tienes ningún viaje activo asignado en este momento. Acepta una solicitud en la sección de pedidos para comenzar un trayecto.
      </p>
    </div>
  );
}

/* ==========================================================
   5. PANTALLA: UBICACIÓN SIMULADA (US5)
   ========================================================== */
function UbicacionNominal() {
  return (
    <div>
      <div className={styles.telemetryCard}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
          <span style={{ fontSize: "0.875rem", fontWeight: 700, color: "#1e3a8a" }}>
            Telemetría GPS activa
          </span>
          <span className={styles.pulseIndicator}>
            <span className={styles.pulseDot} />
            Transmitiendo a M4
          </span>
        </div>
        <p style={{ margin: "0 0 1rem 0", fontSize: "0.75rem", color: "#475569" }}>
          Transmisión periódica activa durante el viaje (cada 5 segundos). Sin mapa según especificación.
        </p>

        <div className={styles.telemetryGrid}>
          <div className={styles.telemetryItem}>
            <div className={styles.telemetryLabel}>Latitud</div>
            <div className={styles.telemetryValue}>-34.603722</div>
          </div>
          <div className={styles.telemetryItem}>
            <div className={styles.telemetryLabel}>Longitud</div>
            <div className={styles.telemetryValue}>-58.381592</div>
          </div>
          <div className={styles.telemetryItem}>
            <div className={styles.telemetryLabel}>Precisión</div>
            <div className={styles.telemetryValue}>± 4.5 m</div>
          </div>
          <div className={styles.telemetryItem}>
            <div className={styles.telemetryLabel}>Último Envío</div>
            <div className={styles.telemetryValue} style={{ fontSize: "0.875rem" }}>15:45:10 UTC</div>
          </div>
        </div>
      </div>

      <div style={{ backgroundColor: "#f0fdf4", border: "1px solid #86efac", borderRadius: "6px", padding: "0.75rem", fontSize: "0.75rem", color: "#14532d" }}>
        ✓ Conductor en estado <strong>OCUPADO</strong>: sincronización continua de coordenadas activada.
      </div>
    </div>
  );
}

function UbicacionCarga() {
  return (
    <div>
      <div className={styles.loadingStateBox}>
        <div className={styles.spinner} />
        <p style={{ fontWeight: 600, margin: "0 0 0.5rem 0", color: "#0f172a" }}>
          Sincronizando coordenadas...
        </p>
        <p style={{ margin: 0, fontSize: "0.875rem" }}>
          Estableciendo conexión con el receptor telemático del Módulo M4.
        </p>
      </div>
      <div className={styles.telemetryGrid} style={{ opacity: 0.5 }}>
        <div className={styles.telemetryItem}>
          <div className={styles.skeletonBar} style={{ width: "50%", height: 12 }} />
          <div className={styles.skeletonBar} style={{ width: "80%", height: 20 }} />
        </div>
        <div className={styles.telemetryItem}>
          <div className={styles.skeletonBar} style={{ width: "50%", height: 12 }} />
          <div className={styles.skeletonBar} style={{ width: "80%", height: 20 }} />
        </div>
      </div>
    </div>
  );
}

function UbicacionError() {
  return (
    <div>
      <div role="alert" className={styles.alertError}>
        <div>
          <h5 className={styles.alertErrorTitle}>Error en la transmisión de ubicación</h5>
          <p className={styles.alertErrorMessage}>
            Fallo de red al enviar el punto de recorrido (-34.6037, -58.3815). Se intentará automáticamente en el próximo intervalo de 5 segundos.
          </p>
        </div>
      </div>
      <div className={styles.telemetryCard} style={{ opacity: 0.7 }}>
        <div className={styles.telemetryLabel}>Última coordenada confirmada</div>
        <div className={styles.telemetryValue} style={{ fontSize: "0.875rem" }}>-34.603500, -58.381200 (hace 45s)</div>
      </div>
    </div>
  );
}

function UbicacionVacio() {
  return (
    <div className={styles.emptyStateBox}>
      <h4 className={styles.emptyStateTitle}>Ubicación Desconocida</h4>
      <p className={styles.emptyStateText}>
        No se registran coordenadas activas para este conductor (campos en valor <code>null</code>). Conforme al contrato, no se muestran coordenadas predeterminadas ni ceros.
      </p>
      <div style={{ marginTop: "1rem" }}>
        <span className={`${styles.statusPillLarge} ${styles.statusPillDesconectado}`}>
          desconocida
        </span>
      </div>
    </div>
  );
}

/* ==========================================================
   VISTA DE TOKENS VISUALES (PALETA, TIPOGRAFÍA, RADIOS)
   ========================================================== */
function TokensView() {
  const colorTokens = [
    { name: "--color-primary", hex: "#1e3a8a", role: "Marca principal / Botones primarios (Azul 900)" },
    { name: "--color-primary-hover", hex: "#172554", role: "Hover botones primarios (Azul 950)" },
    { name: "--color-bg-canvas", hex: "#f8fafc", role: "Fondo general de la aplicación (Slate 50)" },
    { name: "--color-bg-surface", hex: "#ffffff", role: "Fondo tarjetas y componentes (Blanco)" },
    { name: "--color-text-primary", hex: "#0f172a", role: "Texto de alta legibilidad (Slate 900, 16:1)" },
    { name: "--color-text-secondary", hex: "#475569", role: "Texto secundario accesible (Slate 600, 5.5:1)" },
    { name: "--color-success-solid", hex: "#15803d", role: "DISPONIBLE / Aceptar viaje (Verde 700)" },
    { name: "--color-warning-solid", hex: "#b45309", role: "PENDIENTE / OCUPADO / Vence (Ámbar 700)" },
    { name: "--color-danger-solid", hex: "#b91c1c", role: "Error / Rechazar / Alert (Rojo 700)" },
    { name: "--color-info-solid", hex: "#0284c7", role: "CONECTADO / Telemetría GPS (Celeste 600)" },
  ];

  const spacingTokens = [
    { token: "--spacing-1", val: "0.25rem (4px)" },
    { token: "--spacing-2", val: "0.5rem (8px)" },
    { token: "--spacing-3", val: "0.75rem (12px)" },
    { token: "--spacing-4", val: "1rem (16px)" },
    { token: "--spacing-5", val: "1.25rem (20px)" },
    { token: "--spacing-6", val: "1.5rem (24px)" },
    { token: "--spacing-8", val: "2rem (32px)" },
    { token: "--spacing-10", val: "2.5rem (40px)" },
  ];

  const radiusTokens = [
    { token: "--radius-sm", val: "0.25rem (4px)", use: "Badges y campos compactos" },
    { token: "--radius-md", val: "0.375rem (6px)", use: "Botones, inputs, tarjetas secundarias" },
    { token: "--radius-lg", val: "0.5rem (8px)", use: "Tarjetas principales y modales" },
    { token: "--radius-xl", val: "0.75rem (12px)", use: "Contenedores destacados" },
    { token: "--radius-full", val: "9999px", use: "Pills de estado y contadores circulares" },
  ];

  return (
    <div className={styles.tokensSection}>
      <h3 className={styles.tokensTitle}>Guía de Tokens Visuales (T701–T702)</h3>
      <p style={{ color: "#475569", marginBottom: "1.5rem" }}>
        Tokens base formalizados para implementar en <code>globals.css</code> durante T703 (OpenCode).
      </p>

      <h4 style={{ fontSize: "1rem", color: "#1e3a8a", marginBottom: "0.75rem" }}>Paleta de Colores</h4>
      <div className={styles.swatchGrid}>
        {colorTokens.map((c) => (
          <div key={c.name} className={styles.swatchCard}>
            <div className={styles.swatchColor} style={{ backgroundColor: c.hex }} />
            <div className={styles.swatchInfo}>
              <div className={styles.swatchName}>{c.name}</div>
              <div className={styles.swatchHex}>{c.hex}</div>
              <div style={{ color: "#475569", marginTop: 4 }}>{c.role}</div>
            </div>
          </div>
        ))}
      </div>

      <h4 style={{ fontSize: "1rem", color: "#1e3a8a", margin: "1.5rem 0 0.75rem 0" }}>Escala de Espaciados</h4>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem", marginBottom: "1.5rem" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "2px solid #cbd5e1" }}>
            <th style={{ padding: "8px" }}>Token</th>
            <th style={{ padding: "8px" }}>Valor Rem (Px)</th>
            <th style={{ padding: "8px" }}>Muestra Visual</th>
          </tr>
        </thead>
        <tbody>
          {spacingTokens.map((s) => (
            <tr key={s.token} style={{ borderBottom: "1px solid #e2e8f0" }}>
              <td style={{ padding: "8px", fontFamily: "monospace", fontWeight: 600 }}>{s.token}</td>
              <td style={{ padding: "8px" }}>{s.val}</td>
              <td style={{ padding: "8px" }}>
                <div style={{ width: s.val.split(" ")[0], height: 16, backgroundColor: "#1e3a8a", borderRadius: 2 }} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h4 style={{ fontSize: "1rem", color: "#1e3a8a", margin: "1.5rem 0 0.75rem 0" }}>Radios de Borde</h4>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "2px solid #cbd5e1" }}>
            <th style={{ padding: "8px" }}>Token</th>
            <th style={{ padding: "8px" }}>Valor</th>
            <th style={{ padding: "8px" }}>Uso Recomendado</th>
          </tr>
        </thead>
        <tbody>
          {radiusTokens.map((r) => (
            <tr key={r.token} style={{ borderBottom: "1px solid #e2e8f0" }}>
              <td style={{ padding: "8px", fontFamily: "monospace", fontWeight: 600 }}>{r.token}</td>
              <td style={{ padding: "8px" }}>{r.val}</td>
              <td style={{ padding: "8px", color: "#475569" }}>{r.use}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
