import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import React from "react";

const badgeVariants = cva(
  "inline-flex items-center font-medium font-mono uppercase tracking-wider border",
  {
    variants: {
      variant: {
        default: "bg-zinc-800 text-zinc-300 border-zinc-700",
        success: "bg-emerald-950 text-emerald-400 border-emerald-800",
        warning: "bg-amber-950 text-amber-400 border-amber-800",
        error: "bg-red-950 text-red-400 border-red-800",
        info: "bg-blue-950 text-blue-400 border-blue-800",
      },
      size: {
        sm: "text-[10px] px-1.5 py-0 rounded-sm",
        default: "text-xs px-2 py-0.5 rounded-sm",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, size, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant, size }), className)} {...props} />
  );
}
