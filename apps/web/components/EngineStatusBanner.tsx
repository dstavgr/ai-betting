import { EngineStatus } from "@/components/EngineStatus";
import { getEngineHealth } from "@/lib/api";

export async function EngineStatusBanner() {
  const health = await getEngineHealth();

  if (health.ok) {
    return null;
  }

  return (
    <div className="flex items-center justify-center gap-2 bg-destructive px-4 py-2 text-center text-xs text-destructive-foreground">
      <EngineStatus health={health} />
      <span>Live data is temporarily unavailable. Showing what we can.</span>
    </div>
  );
}
