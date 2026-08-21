"use client";

import Link from "next/link";
import { formatCurrency, RiskBadge } from "@/components/dashboard/kpi-card";
import type { TransactionSummary } from "@/lib/api";

export function TransactionsTable({ items }: { items: TransactionSummary[] }) {
  if (!items.length) {
    return (
      <div className="rounded-lg border border-dashed border-border p-12 text-center text-muted-foreground">
        No transactions found.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/30 text-left text-muted-foreground">
            <th className="px-4 py-3 font-medium">Transaction ID</th>
            <th className="px-4 py-3 font-medium">Amount</th>
            <th className="px-4 py-3 font-medium hidden md:table-cell">Customer</th>
            <th className="px-4 py-3 font-medium hidden lg:table-cell">Payment</th>
            <th className="px-4 py-3 font-medium hidden lg:table-cell">Location</th>
            <th className="px-4 py-3 font-medium">Risk Score</th>
            <th className="px-4 py-3 font-medium">Level</th>
            <th className="px-4 py-3 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {items.map((t) => (
            <tr key={t.transaction_id} className="border-b border-border/50 hover:bg-muted/20 transition-colors">
              <td className="px-4 py-3">
                <Link href={`/transactions/${t.transaction_id}`} className="font-mono text-primary hover:underline">
                  {t.transaction_id.slice(0, 12)}…
                </Link>
              </td>
              <td className="px-4 py-3 font-medium">{formatCurrency(t.transaction_amount)}</td>
              <td className="px-4 py-3 hidden md:table-cell font-mono text-xs">{t.customer_id}</td>
              <td className="px-4 py-3 hidden lg:table-cell">{t.payment_method}</td>
              <td className="px-4 py-3 hidden lg:table-cell">{t.city}</td>
              <td className="px-4 py-3 font-bold">{t.risk_score != null ? Math.round(t.risk_score) : "—"}</td>
              <td className="px-4 py-3"><RiskBadge level={t.risk_level} /></td>
              <td className="px-4 py-3 text-xs text-muted-foreground">{t.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
