import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState, type ReactNode } from "react";
import {
  Car,
  Check,
  MapPin,
  MessageCircle,
  Navigation,
  Phone,
  Power,
  RefreshCw,
  ShieldAlert,
  Star,
  ArrowRight,
} from "lucide-react";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Conductor — Panel de viajes" },
      { name: "description", content: "App de conductor: conéctate, acepta viajes y completa recorridos." },
      { property: "og:title", content: "Conductor — Panel de viajes" },
      { property: "og:description", content: "App de conductor: conéctate, acepta viajes y completa recorridos." },
    ],
  }),
  component: Index,
});

type Step = "offline" | "searching" | "request" | "toPickup" | "waiting" | "onTrip" | "arrived";

const PASSENGER = { name: "Sra. Jane Agbo", rating: 4.9, type: "Viaje Estándar", fare: "$65.00" };
const PICKUP = { title: "Av. Insurgentes Sur 120, Roma Norte" };
const DROPOFF = { title: "Catedral Metropolitana, Centro Histórico" };

function Index() {
  const [step, setStep] = useState<Step>("offline");
  const [wait, setWait] = useState(0);

  useEffect(() => {
    if (step === "searching") {
      const t = setTimeout(() => setStep("request"), 2500);
      return () => clearTimeout(t);
    }
    if (step === "waiting") {
      setWait(0);
      const i = setInterval(() => setWait((w) => w + 1), 1000);
      return () => clearInterval(i);
    }
    return undefined;
  }, [step]);

  const mmss = `${String(Math.floor(wait / 60)).padStart(2, "0")}:${String(wait % 60).padStart(2, "0")}`;

  const status: Record<Step, { label: string; detail?: string; right?: string; tone: "muted" | "live" | "warn" }> = {
    offline: { label: "Desconectado", tone: "muted" },
    searching: { label: "En línea", detail: "Buscando viajes cercanos", tone: "live" },
    request: { label: "Nueva solicitud", detail: "Recogida a 3 min", tone: "live" },
    toPickup: { label: "Hacia recogida", detail: "Llegada en 3 min", right: "1.2 km", tone: "live" },
    waiting: { label: "Esperando pasajero", detail: "Tiempo de espera", right: mmss, tone: "warn" },
    onTrip: { label: "Viaje en curso", detail: "Hacia destino", right: "16 min · 6.5 km", tone: "live" },
    arrived: { label: "Llegaste al destino", detail: "Confirma para cerrar", right: "Catedral", tone: "live" },
  };
  const s = status[step];

  return (
    <main className="flex min-h-screen items-center justify-center bg-background font-sans sm:p-6">
      <div className="relative h-screen w-full max-w-[420px] overflow-hidden bg-map sm:h-[860px] sm:rounded-[2.5rem] sm:border-8 sm:border-foreground sm:shadow-float">
        <MapView step={step} />

        {/* Status bar — same component in every state */}
        <div className="absolute inset-x-4 top-4 flex items-center justify-between gap-3 rounded-2xl bg-foreground px-4 py-3 text-background shadow-float">
          <div className="flex min-w-0 items-center gap-3">
            <span
              className={`h-2.5 w-2.5 shrink-0 rounded-full ${
                s.tone === "live" ? "animate-pulse bg-primary" : s.tone === "warn" ? "animate-pulse bg-chart-4" : "bg-muted-foreground"
              }`}
            />
            <div className="min-w-0">
              <p className="truncate text-[11px] font-bold uppercase tracking-wider">{s.label}</p>
              {s.detail && <p className="truncate text-xs opacity-70">{s.detail}</p>}
            </div>
          </div>
          {s.right && <p className="shrink-0 text-sm font-bold tabular-nums">{s.right}</p>}
        </div>

        {(step === "onTrip" || step === "arrived") && (
          <div className="absolute right-4 top-24 flex flex-col gap-2">
            <FloatBtn label="Ubicación"><Navigation className="h-4 w-4 text-pin-pickup" /></FloatBtn>
            <FloatBtn label="Seguridad"><ShieldAlert className="h-4 w-4 text-destructive" /></FloatBtn>
          </div>
        )}

        {/* Bottom sheet — same shell in every state */}
        <section className="absolute inset-x-3 bottom-3 space-y-4 rounded-3xl bg-card p-4 shadow-sheet">
          {step === "offline" && (
            <>
              <Header icon={<Power className="h-5 w-5" />} title="Estás desconectado" sub="Conéctate para recibir viajes" />
              <PrimaryBtn onClick={() => setStep("searching")}>Conectarse</PrimaryBtn>
            </>
          )}

          {step === "searching" && (
            <>
              <Header icon={<RefreshCw className="h-5 w-5 animate-spin" />} title="Buscando viajes…" sub="Conectado a la red de asignación automática" />
              <GhostBtn onClick={() => setStep("offline")}>Desconectarse</GhostBtn>
            </>
          )}

          {step !== "offline" && step !== "searching" && (
            <>
              <PassengerRow showActions={step !== "request"} showFare={step === "request"} />
              {step === "waiting" && (
                <div className="flex flex-wrap gap-2">
                  <Chip>"Ya llegué"</Chip>
                  <Chip>"Estoy con las luces intermitentes"</Chip>
                </div>
              )}
              <RouteCard step={step} />
            </>
          )}

          {step === "request" && (
            <div className="grid grid-cols-2 gap-3">
              <DangerBtn onClick={() => setStep("searching")}>Rechazar</DangerBtn>
              <PrimaryBtn onClick={() => setStep("toPickup")}>Aceptar</PrimaryBtn>
            </div>
          )}
          {step === "toPickup" && (
            <Actions primary="He llegado al punto de recogida" onPrimary={() => setStep("waiting")} links={[["Cancelar viaje", () => setStep("searching")]]} />
          )}
          {step === "waiting" && (
            <Actions
              primary="Iniciar viaje con el pasajero"
              primaryIcon={<ArrowRight className="h-4 w-4" />}
              onPrimary={() => setStep("onTrip")}
              links={[["Pasajero no se presentó", () => setStep("searching")], ["Cancelar viaje", () => setStep("searching")]]}
            />
          )}
          {step === "onTrip" && (
            <Actions primary="Llegué al destino" onPrimary={() => setStep("arrived")} links={[["Reportar una incidencia", () => {}]]} />
          )}
          {step === "arrived" && (
            <Actions primary="Completar viaje" onPrimary={() => setStep("searching")} links={[["Reportar una incidencia", () => {}]]} />
          )}
        </section>
      </div>
    </main>
  );
}

/* ---------- building blocks ---------- */

function Header({ icon, title, sub }: { icon: ReactNode; title: string; sub: string }) {
  return (
    <div className="flex items-center gap-3">
      <div className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-accent text-accent-foreground">{icon}</div>
      <div className="min-w-0">
        <p className="truncate font-bold">{title}</p>
        <p className="truncate text-xs text-muted-foreground">{sub}</p>
      </div>
    </div>
  );
}

function PassengerRow({ showActions, showFare }: { showActions: boolean; showFare: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <div className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-accent font-bold text-accent-foreground">JA</div>
      <div className="min-w-0 flex-1">
        <p className="truncate font-bold">{PASSENGER.name}</p>
        <p className="flex items-center gap-1 text-xs text-muted-foreground">
          <Star className="h-3 w-3 fill-chart-4 text-chart-4" /> {PASSENGER.rating} · {PASSENGER.type}
        </p>
      </div>
      {showActions && (
        <div className="flex gap-2">
          <IconBtn label="Mensaje"><MessageCircle className="h-4 w-4" /></IconBtn>
          <IconBtn label="Llamar"><Phone className="h-4 w-4" /></IconBtn>
        </div>
      )}
      {showFare && (
        <div className="text-right">
          <p className="text-lg font-extrabold text-primary">{PASSENGER.fare}</p>
          <p className="text-[11px] text-muted-foreground">Tarifa estimada</p>
        </div>
      )}
    </div>
  );
}

function RouteCard({ step }: { step: Step }) {
  const rows =
    step === "request"
      ? [
          { kind: "pickup" as const, label: "Recogida", title: PICKUP.title, meta: "A 1.2 km · ~3 min" },
          { kind: "drop" as const, label: "Destino", title: DROPOFF.title, meta: "7.8 km · ~18 min" },
        ]
      : step === "toPickup"
        ? [{ kind: "pickup" as const, label: "Punto de recogida", title: PICKUP.title, meta: "Distancia: ~1.2 km" }]
        : [{ kind: "drop" as const, label: "Destino", title: DROPOFF.title, meta: step === "waiting" ? "7.8 km · ~18 min" : "Restante: ~6.5 km" }];
  return (
    <div className="space-y-3 rounded-2xl bg-muted p-3">
      {rows.map((r) => (
        <div key={r.label} className="flex items-start gap-3">
          <span className={`mt-1 h-3 w-3 shrink-0 rounded-full border-[3px] ${r.kind === "pickup" ? "border-pin-pickup" : "border-primary"} bg-card`} />
          <div className="min-w-0 flex-1">
            <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{r.label}</p>
            <p className="truncate text-sm font-semibold">{r.title}</p>
            <p className="text-xs text-muted-foreground">{r.meta}</p>
          </div>
        </div>
      ))}
      {step !== "request" && (
        <div className="flex justify-between border-t border-border pt-2 text-xs">
          <span className="text-muted-foreground">Tarifa {step === "toPickup" ? "estimada" : "actual"}</span>
          <span className="font-bold text-primary">+{PASSENGER.fare}</span>
        </div>
      )}
    </div>
  );
}

function Actions({
  primary,
  primaryIcon = <Check className="h-4 w-4" />,
  onPrimary,
  links,
}: {
  primary: string;
  primaryIcon?: ReactNode;
  onPrimary: () => void;
  links: [string, () => void][];
}) {
  return (
    <div className="space-y-2">
      <PrimaryBtn onClick={onPrimary}>
        {primaryIcon}
        {primary}
      </PrimaryBtn>
      <div className="flex justify-center gap-6">
        {links.map(([l, fn]) => (
          <button key={l} onClick={fn} className="py-1 text-xs font-semibold text-muted-foreground hover:text-foreground">
            {l}
          </button>
        ))}
      </div>
    </div>
  );
}

const base = "flex h-12 w-full items-center justify-center gap-2 rounded-2xl text-sm font-bold transition active:scale-[0.98]";
function PrimaryBtn({ children, onClick }: { children: ReactNode; onClick: () => void }) {
  return <button onClick={onClick} className={`${base} bg-primary text-primary-foreground hover:opacity-90`}>{children}</button>;
}
function DangerBtn({ children, onClick }: { children: ReactNode; onClick: () => void }) {
  return <button onClick={onClick} className={`${base} bg-secondary text-destructive hover:bg-border`}>{children}</button>;
}
function GhostBtn({ children, onClick }: { children: ReactNode; onClick: () => void }) {
  return <button onClick={onClick} className={`${base} bg-secondary text-secondary-foreground hover:bg-border`}>{children}</button>;
}
function IconBtn({ children, label }: { children: ReactNode; label: string }) {
  return <button aria-label={label} className="grid h-10 w-10 place-items-center rounded-xl bg-secondary text-primary hover:bg-accent">{children}</button>;
}
function FloatBtn({ children, label }: { children: ReactNode; label: string }) {
  return <button aria-label={label} className="grid h-11 w-11 place-items-center rounded-2xl bg-card shadow-float">{children}</button>;
}
function Chip({ children }: { children: ReactNode }) {
  return <button className="rounded-full bg-secondary px-3 py-1.5 text-xs font-semibold text-secondary-foreground hover:bg-accent">{children}</button>;
}

/* ---------- map ---------- */

function MapView({ step }: { step: Step }) {
  const car = step === "onTrip" || step === "arrived" ? { x: 120, y: 330 } : step === "waiting" ? { x: 230, y: 380 } : { x: 210, y: 420 };
  return (
    <svg viewBox="0 0 420 860" preserveAspectRatio="xMidYMid slice" className="absolute inset-0 h-full w-full">
      <rect width="420" height="860" className="fill-map" />
      {[[30, 40, 140, 130], [250, 60, 150, 110], [40, 520, 120, 140], [280, 560, 120, 120], [60, 240, 90, 70]].map(([x, y, w, h], i) => (
        <rect key={i} x={x} y={y} width={w} height={h} rx="14" className="fill-map-block" />
      ))}
      <g className="stroke-map-road" strokeWidth="22" fill="none" strokeLinecap="round">
        <path d="M-20 200 L440 150" />
        <path d="M-20 480 L440 440" />
        <path d="M170 -20 L240 880" />
        <path d="M-20 720 L440 700" />
        <path d="M330 -20 L360 880" />
      </g>

      {step === "request" && (
        <>
          <path d="M200 300 Q300 360 270 560" className="stroke-pin-pickup" strokeWidth="5" fill="none" strokeLinecap="round" />
          <Pin x={200} y={300} cls="fill-pin-pickup" label="Recogida · 3 min" />
          <Pin x={270} y={560} cls="fill-primary" label="Destino" />
        </>
      )}
      {step === "toPickup" && (
        <>
          <path d="M210 420 L240 560" className="stroke-primary" strokeWidth="5" fill="none" strokeLinecap="round" />
          <Pin x={240} y={560} cls="fill-pin-pickup" label="Recogida: Sra. Jane" />
        </>
      )}
      {step === "waiting" && (
        <>
          <circle cx="215" cy="380" r="55" className="fill-primary/15 stroke-primary" strokeDasharray="5 5" />
          <Pin x={200} y={370} cls="fill-pin-pickup" label="Punto de recogida" />
        </>
      )}
      {(step === "onTrip" || step === "arrived") && (
        <>
          <path d="M120 330 L170 360 L330 330 L340 480" className="stroke-primary" strokeWidth="6" fill="none" strokeLinejoin="round" strokeLinecap="round" />
          <Pin x={340} y={480} cls="fill-primary" label="Catedral Metropolitana" />
        </>
      )}

      {(step === "offline" || step === "searching") && (
        <g className={step === "searching" ? "animate-pulse" : ""}>
          <circle cx={car.x} cy={car.y} r="110" className={step === "searching" ? "fill-primary/10" : "fill-muted-foreground/5"} />
          <circle cx={car.x} cy={car.y} r="60" className={step === "searching" ? "fill-primary/15 stroke-primary/40" : "fill-muted-foreground/10"} />
        </g>
      )}
      <foreignObject x={car.x - 20} y={car.y - 20} width="40" height="40">
        <div className="grid h-10 w-10 place-items-center rounded-full border-4 border-card bg-foreground text-background shadow-float">
          <Car className="h-4 w-4" />
        </div>
      </foreignObject>
    </svg>
  );
}

function Pin({ x, y, cls, label }: { x: number; y: number; cls: string; label: string }) {
  return (
    <g>
      <circle cx={x} cy={y} r="11" className="fill-card" />
      <circle cx={x} cy={y} r="7" className={cls} />
      <foreignObject x={x - 90} y={y - 46} width="180" height="30">
        <div className="flex justify-center">
          <span className="flex items-center gap-1 rounded-full bg-foreground px-2.5 py-1 text-[10px] font-bold text-background">
            <MapPin className="h-3 w-3" />
            {label}
          </span>
        </div>
      </foreignObject>
    </g>
  );
}
