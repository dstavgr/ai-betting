import { crestUrl } from "@/lib/crest";

export function TeamCrest({
  name,
  apiFootballId,
  size = 20,
}: {
  name: string;
  apiFootballId?: number | null;
  size?: number;
}) {
  const url = crestUrl(apiFootballId);

  if (!url) {
    return (
      <span
        className="flex shrink-0 items-center justify-center rounded-full bg-muted text-[10px] font-semibold text-muted-foreground"
        style={{ width: size, height: size }}
        aria-hidden="true"
      >
        {name.slice(0, 2).toUpperCase()}
      </span>
    );
  }

  // eslint-disable-next-line @next/next/no-img-element
  return <img src={url} alt="" width={size} height={size} className="shrink-0 rounded-full" loading="lazy" />;
}
