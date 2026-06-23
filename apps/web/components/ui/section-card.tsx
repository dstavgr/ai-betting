import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

type SectionHeaderProps = HTMLAttributes<HTMLDivElement> & {
  label: ReactNode;
  action?: ReactNode;
};

export function SectionHeader({ label, action, className, ...props }: SectionHeaderProps) {
  return (
    <div className={cn("flex items-center justify-between gap-3", className)} {...props}>
      <h2 className="min-w-0 truncate text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
        {label}
      </h2>
      {action ? <div className="shrink-0 text-xs font-medium text-muted-foreground">{action}</div> : null}
    </div>
  );
}

type SectionCardProps = Omit<HTMLAttributes<HTMLDivElement>, "title"> & {
  title?: ReactNode;
  action?: ReactNode;
  headerClassName?: string;
};

export function SectionCard({
  title,
  action,
  headerClassName,
  className,
  children,
  ...props
}: SectionCardProps) {
  return (
    <section
      className={cn("rounded-lg border border-border bg-card p-3 text-card-foreground sm:p-4", className)}
      {...props}
    >
      {title ? <SectionHeader label={title} action={action} className={cn("mb-3", headerClassName)} /> : null}
      {children}
    </section>
  );
}
