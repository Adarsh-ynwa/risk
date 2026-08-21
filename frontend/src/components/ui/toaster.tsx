"use client";

import * as React from "react";
import { Toast, ToastClose, ToastDescription, ToastProvider, ToastTitle, ToastViewport } from "@/components/ui/toast";

type ToastItem = {
  id: string;
  title?: string;
  description?: string;
  variant?: "default" | "destructive";
};

type ToastContextType = {
  toast: (item: Omit<ToastItem, "id">) => void;
};

const ToastContext = React.createContext<ToastContextType | undefined>(undefined);

export function ToastProviderWrapper({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<ToastItem[]>([]);

  const toast = React.useCallback((item: Omit<ToastItem, "id">) => {
    const id = Math.random().toString(36).slice(2);
    setToasts((prev) => [...prev, { ...item, id }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000);
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      <ToastProvider>
        {children}
        {toasts.map((t) => (
          <Toast key={t.id} variant={t.variant} open>
            <div className="grid gap-1">
              {t.title && <ToastTitle>{t.title}</ToastTitle>}
              {t.description && <ToastDescription>{t.description}</ToastDescription>}
            </div>
            <ToastClose />
          </Toast>
        ))}
        <ToastViewport />
      </ToastProvider>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = React.useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProviderWrapper");
  return ctx;
}

export function Toaster() {
  const [toasts, setToasts] = React.useState<ToastItem[]>([]);

  React.useEffect(() => {
    (window as unknown as { __toast?: typeof setToasts }).__toast = setToasts;
  }, []);

  return (
    <ToastProvider>
      {toasts.map((t) => (
        <Toast key={t.id} variant={t.variant} open onOpenChange={() => setToasts((p) => p.filter((x) => x.id !== t.id))}>
          <div className="grid gap-1">
            {t.title && <ToastTitle>{t.title}</ToastTitle>}
            {t.description && <ToastDescription>{t.description}</ToastDescription>}
          </div>
          <ToastClose />
        </Toast>
      ))}
      <ToastViewport />
    </ToastProvider>
  );
}

export function showToast(item: Omit<ToastItem, "id">) {
  const setter = (window as unknown as { __toast?: React.Dispatch<React.SetStateAction<ToastItem[]>> }).__toast;
  if (setter) {
    const id = Math.random().toString(36).slice(2);
    setter((prev) => [...prev, { ...item, id }]);
    setTimeout(() => setter((prev) => prev.filter((t) => t.id !== id)), 4000);
  }
}
