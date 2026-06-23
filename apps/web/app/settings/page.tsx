import { ShieldCheck } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const settings = [
  ["League scope", "Greek Super League first"],
  ["Numeric path", "Predictive model and deterministic functions only"],
  ["AI output provider", "DeepSeek via OpenAI-compatible API"],
  ["AI output models", "deepseek-chat for concise match outputs"],
  ["Domain target", "bet.stav.gr"],
  ["Status", "MVP scaffold deployed behind localhost proxy"],
];

export default function SettingsPage() {
  return (
    <div className="space-y-4">
      <section>
        <p className="text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">Configuration</p>
        <h1 className="mt-1 text-lg font-semibold">Settings</h1>
      </section>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Guardrails</CardTitle>
          <ShieldCheck className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
        </CardHeader>
        <CardContent>
          <dl className="divide-y divide-border">
            {settings.map(([label, value]) => (
              <div key={label} className="grid gap-1 py-3 sm:grid-cols-[180px_1fr]">
                <dt className="text-sm text-muted-foreground">{label}</dt>
                <dd className="text-sm font-medium">{value}</dd>
              </div>
            ))}
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
