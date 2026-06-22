"use client";

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
    <div className="-mx-4 mb-3 flex gap-2 overflow-x-auto px-4 pb-1">
      {dates.map((date) => (
        <button
          key={date}
          onClick={() => onSelect(date)}
          className={`shrink-0 rounded-full px-3 py-1 text-xs ${
            date === active ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
          }`}
          type="button"
        >
          {new Date(date).toLocaleDateString("en", { weekday: "short", day: "numeric", month: "short" })}
        </button>
      ))}
    </div>
  );
}
