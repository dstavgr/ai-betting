import { FormPill } from "@/components/ui/form-pill";
import { teamForm } from "@/lib/teamForm";
import type { Fixture } from "@/lib/types";

type FormGuideProps = {
  fixtures: Fixture[];
  teamName: string;
  limit?: number;
};

function RecordPart({ value, label }: { value: number; label: "W" | "D" | "L" }) {
  return (
    <span>
      <span className="font-display font-semibold tabular-nums">{value}</span>
      {label}
    </span>
  );
}

export function FormGuide({ fixtures, teamName, limit }: FormGuideProps) {
  const form = teamForm(fixtures, teamName, { limit });

  return (
    <div className="flex min-w-0 items-center gap-2">
      <div className="flex shrink-0 items-center gap-1" aria-label={`${teamName} form`}>
        {form.results.map((result, index) => (
          <FormPill key={`${result}-${index}`} result={result} size="sm" />
        ))}
      </div>
      <div className="flex min-w-0 items-center gap-1 text-[11px] font-medium text-muted-foreground">
        <RecordPart value={form.record.w} label="W" />
        <RecordPart value={form.record.d} label="D" />
        <RecordPart value={form.record.l} label="L" />
      </div>
    </div>
  );
}
