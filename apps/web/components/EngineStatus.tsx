import { Activity, AlertTriangle } from "lucide-react";

import type { EngineHealthResult } from "@/lib/api";
import { Badge } from "@/components/ui/badge";

export function EngineStatus({ health }: { health: EngineHealthResult }) {
  if (!health.ok) {
    return (
      <Badge variant="danger" className="gap-1.5">
        <AlertTriangle className="h-3.5 w-3.5" />
        Engine offline
      </Badge>
    );
  }

  return (
    <Badge variant="value" className="gap-1.5">
      <Activity className="h-3.5 w-3.5" />
      Engine {health.data.version}
    </Badge>
  );
}
