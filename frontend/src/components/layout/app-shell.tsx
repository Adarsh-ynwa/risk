"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  LayoutDashboard,
  ArrowLeftRight,
  BarChart3,
  ClipboardList,
  Gauge,
  Settings,
  ShieldAlert,
  Sparkles,
  Menu,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/transactions", label: "Transactions", icon: ArrowLeftRight },
  { href: "/alerts", label: "Alert Queue", icon: ClipboardList },
  { href: "/evaluation", label: "Evaluation", icon: Gauge },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/settings", label: "Settings", icon: Settings },
];

function NavLinks({ pathname, onNavigate }: { pathname: string; onNavigate?: () => void }) {
  return (
    <>
      {nav.map(({ href, label, icon: Icon }) => (
        <Link
          key={href}
          href={href}
          onClick={onNavigate}
          className={cn(
            "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors",
            pathname.startsWith(href)
              ? "bg-primary/10 text-primary"
              : "text-muted-foreground hover:bg-accent hover:text-foreground"
          )}
        >
          <Icon className="h-4 w-4" />
          {label}
        </Link>
      ))}
    </>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-border/70 bg-black/35 backdrop-blur-xl lg:flex">
        <div className="flex h-16 items-center gap-2 border-b border-border px-6">
          <ShieldAlert className="h-7 w-7 text-primary" />
          <div>
            <p className="text-sm font-bold tracking-tight">AI Risk Manager</p>
            <p className="text-[10px] text-muted-foreground">Payment Risk Ops</p>
          </div>
        </div>
        <nav className="space-y-1 p-4">
          <NavLinks pathname={pathname} />
        </nav>
        <div className="mt-auto p-4">
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-xs text-amber-200/80">
            Demo environment — no real payments are processed.
          </div>
        </div>
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-black/60"
            aria-label="Close menu"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="relative flex h-full w-72 flex-col border-r border-border bg-card shadow-xl">
            <div className="flex h-16 items-center justify-between border-b border-border px-4">
              <div className="flex items-center gap-2">
                <ShieldAlert className="h-6 w-6 text-primary" />
                <p className="text-sm font-bold">AI Risk Manager</p>
              </div>
              <Button variant="ghost" size="icon" onClick={() => setMobileOpen(false)} aria-label="Close">
                <X className="h-5 w-5" />
              </Button>
            </div>
            <nav className="flex-1 space-y-1 overflow-auto p-4">
              <NavLinks pathname={pathname} onNavigate={() => setMobileOpen(false)} />
            </nav>
            <div className="border-t border-border p-4">
              <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-xs text-amber-200/80">
                Demo environment — no real payments are processed.
              </div>
            </div>
          </aside>
        </div>
      )}

      <div className="flex flex-1 flex-col min-w-0">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-3 border-b border-border/70 bg-background/80 px-4 backdrop-blur-xl lg:px-8">
          <div className="flex items-center gap-3 min-w-0">
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden shrink-0"
              onClick={() => setMobileOpen(true)}
              aria-label="Open menu"
            >
              <Menu className="h-5 w-5" />
            </Button>
            <div className="lg:hidden min-w-0">
              <p className="text-sm font-semibold truncate">AI Risk Manager</p>
            </div>
            <p className="hidden text-sm text-muted-foreground lg:block">
              Experimental AI-powered payment risk management prototype
            </p>
          </div>
          <DemoModeButton />
        </header>
        <main className="flex-1 overflow-auto p-4 lg:p-8">{children}</main>
      </div>
    </div>
  );
}

function DemoModeButton() {
  return (
    <Link href="/transactions/demo" className="shrink-0">
      <Button size="sm" variant="outline" className="gap-2 border-primary/40 text-primary">
        <Sparkles className="h-4 w-4" />
        <span className="hidden sm:inline">View Highest Risk Transaction</span>
        <span className="sm:hidden">Demo</span>
      </Button>
    </Link>
  );
}
