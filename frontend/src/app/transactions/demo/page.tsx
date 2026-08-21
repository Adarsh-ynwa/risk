"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function DemoRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    api.highestRisk()
      .then(({ transaction_id }) => router.replace(`/transactions/${transaction_id}`))
      .catch(() => router.replace("/transactions?critical_only=true"));
  }, [router]);

  return (
    <div className="flex min-h-[50vh] items-center justify-center">
      <div className="text-center space-y-3">
        <div className="mx-auto h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        <p className="text-muted-foreground">Finding highest risk transaction for demo...</p>
      </div>
    </div>
  );
}
