import { LoginScreen } from "../../components/conductor/ConductorDemo";

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;
  const demoDisponible =
    process.env.NODE_ENV === "development" && process.env.USE_MOCK === "true";
  return <LoginScreen error={error} demoDisponible={demoDisponible} />;
}
