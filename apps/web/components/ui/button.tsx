import { Slot } from "@radix-ui/react-slot";
import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  asChild?: boolean;
  variant?: "primary" | "ghost" | "outline";
  size?: "sm" | "md" | "lg" | "icon";
};

export function Button({ asChild, className, variant = "primary", size = "md", ...props }: ButtonProps) {
  const Comp = asChild ? Slot : "button";
  return (
    <Comp
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-1 focus-visible:outline-offset-2 focus-visible:outline-muted-foreground disabled:pointer-events-none disabled:opacity-50",
        size === "sm" && "h-8 px-2.5",
        size === "md" && "h-9 px-3",
        size === "lg" && "h-10 px-4",
        size === "icon" && "h-9 w-9",
        variant === "primary" && "bg-primary text-primary-foreground hover:bg-primary-hover",
        variant === "ghost" && "text-muted-foreground hover:bg-muted hover:text-foreground",
        variant === "outline" && "border border-border bg-background hover:bg-muted",
        className,
      )}
      {...props}
    />
  );
}
