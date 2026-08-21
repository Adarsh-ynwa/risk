import { Activity, AlertTriangle, Shield, TrendingUp, Wallet } from "lucide-react";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { DashboardCharts } from "@/components/dashboard/dashboard-charts";
import { TransactionsTable } from "@/components/transactions/transactions-table";
import { api } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

export default async function DashboardPage() {
  let stats, summary, recent;

  try {
    [stats, summary, recent] = await Promise.all([
      api.stats(),
      api.riskSummary(),
      api.transactions({ page: 1, page_size: 10, sort_by: "risk_score", sort_order: "desc", minimum_risk: 60 }),
    ]);
  } catch {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-8 text-center">
        <p className="text-lg font-semibold text-destructive">Backend unavailable</p>
        <p className="mt-2 text-sm text-muted-foreground">
          Start the API server: <code className="text-primary">uvicorn app.main:app --reload</code>
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">AI Risk Manager</h1>
        <p className="text-muted-foreground mt-1">Intelligent payment risk operations</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <KpiCard title="Transactions Analyzed" value={stats.transactions_analyzed.toLocaleString()} icon={Activity} />
        <KpiCard title="High Risk" value={stats.high_risk_transactions.toLocaleString()} icon={AlertTriangle} accent="bg-orange-500/10 text-orange-400" />
        <KpiCard title="Critical" value={stats.critical_transactions.toLocaleString()} icon={Shield} accent="bg-red-500/10 text-red-400" />
        <KpiCard title="Amount at Risk" value={formatCurrency(stats.amount_at_risk)} icon={Wallet} accent="bg-amber-500/10 text-amber-400" />
        <KpiCard title="Observed Fraud Rate" value={`${stats.fraud_prevalence_rate}%`} subtitle={`${stats.fraud_count} labeled fraud of ${stats.total_transactions}`} icon={TrendingUp} />
      </div>

      <DashboardCharts summary={summary} />

      <div>
        <h2 className="text-xl font-semibold mb-4">Recent Risky Transactions</h2>
        <TransactionsTable items={recent.items} />
      </div>
    </div>
  );
}
