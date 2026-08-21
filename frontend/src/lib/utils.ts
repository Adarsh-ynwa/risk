import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function riskLevelColor(level: string | null | undefined): string {
  switch (level?.toUpperCase()) {
    case "LOW":
      return "text-risk-low bg-risk-low/10 border-risk-low/30";
    case "MEDIUM":
      return "text-risk-medium bg-risk-medium/10 border-risk-medium/30";
    case "HIGH":
      return "text-risk-high bg-risk-high/10 border-risk-high/30";
    case "CRITICAL":
      return "text-risk-critical bg-risk-critical/10 border-risk-critical/30";
    default:
      return "text-muted-foreground bg-muted border-border";
  }
}

export function riskBadgeClass(level: string | null | undefined): string {
  const base = "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold";
  return cn(base, riskLevelColor(level));
}
