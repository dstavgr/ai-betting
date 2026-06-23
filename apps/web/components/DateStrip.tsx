"use client";

const DAY_MS = 24 * 60 * 60 * 1000;

function parseDateKey(date: string) {
  const [year, month, day] = date.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function startOfToday() {
  const today = new Date();
  return new Date(today.getFullYear(), today.getMonth(), today.getDate());
}

function dateLabel(date: string) {
  const target = parseDateKey(date);
  const diffDays = Math.round((target.getTime() - startOfToday().getTime()) / DAY_MS);

  if (diffDays === 0) return "Today";
  if (diffDays === -1) return "Yesterday";
  if (diffDays === 1) return "Tomorrow";

  return target.toLocaleDateString("en", { weekday: "short", day: "numeric", month: "short" });
}

export function DateStrip({
  dates,
  active,
  onSelect,
}: {
  dates: string[];
  active: string;
  onSelect: (date: string) => void;
}) {
  return (
    <div className="-mx-4 mb-3 flex gap-2 overflow-x-auto border-b border-border px-4 pb-3 md:mx-0 md:px-0">
      {dates.map((date) => (
        <button
          key={date}
          onClick={() => onSelect(date)}
          className={`shrink-0 rounded-md border px-3 py-1.5 text-xs font-medium transition-colors ${
            date === active
              ? "border-primary bg-primary text-primary-foreground"
              : "border-border bg-card text-muted-foreground hover:bg-muted/70"
          }`}
          type="button"
        >
          {dateLabel(date)}
        </button>
      ))}
    </div>
  );
}
