"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Search, Filter, Plus } from "lucide-react";
import { TransactionsTable } from "@/components/transactions/transactions-table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, type PaginatedTransactions, type TransactionFilters } from "@/lib/api";

const selectClass = "h-10 rounded-md border border-input bg-background px-3 text-sm";

export default function TransactionsPage() {
  const [data, setData] = useState<PaginatedTransactions | null>(null);
  const [filters, setFilters] = useState<TransactionFilters | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [riskLevel, setRiskLevel] = useState("");
  const [status, setStatus] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("");
  const [merchantCategory, setMerchantCategory] = useState("");
  const [criticalOnly, setCriticalOnly] = useState(false);
  const [sortBy, setSortBy] = useState("risk_score");

  useEffect(() => {
    api.transactionFilters().then(setFilters).catch(() => setFilters(null));
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const result = await api.transactions({
        page,
        page_size: 20,
        search: search || undefined,
        risk_level: riskLevel || undefined,
        status: status || undefined,
        payment_method: paymentMethod || undefined,
        merchant_category: merchantCategory || undefined,
        sort_by: sortBy,
        sort_order: "desc",
        critical_only: criticalOnly,
      });
      setData(result);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [page, search, riskLevel, status, paymentMethod, merchantCategory, criticalOnly, sortBy]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const resetPage = () => setPage(1);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Transactions</h1>
          <p className="text-muted-foreground">Monitor and investigate payment transactions</p>
        </div>
        <Button asChild className="gap-2">
          <Link href="/transactions/new"><Plus className="h-4 w-4" />Add transaction</Link>
        </Button>
      </div>

      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-[200px] max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by ID, customer, city..."
            className="pl-9"
            value={search}
            onChange={(e) => { setSearch(e.target.value); resetPage(); }}
          />
        </div>
        <select className={selectClass} value={riskLevel} onChange={(e) => { setRiskLevel(e.target.value); resetPage(); }}>
          <option value="">All Risk Levels</option>
          <option value="LOW">LOW</option>
          <option value="MEDIUM">MEDIUM</option>
          <option value="HIGH">HIGH</option>
          <option value="CRITICAL">CRITICAL</option>
        </select>
        <select className={selectClass} value={status} onChange={(e) => { setStatus(e.target.value); resetPage(); }}>
          <option value="">All Statuses</option>
          {(filters?.statuses ?? []).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select className={selectClass} value={paymentMethod} onChange={(e) => { setPaymentMethod(e.target.value); resetPage(); }}>
          <option value="">All Payment Methods</option>
          {(filters?.payment_methods ?? []).map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
        <select className={selectClass} value={merchantCategory} onChange={(e) => { setMerchantCategory(e.target.value); resetPage(); }}>
          <option value="">All Categories</option>
          {(filters?.merchant_categories ?? []).map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <select className={selectClass} value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
          <option value="risk_score">Sort: Risk Score</option>
          <option value="amount">Sort: Amount</option>
          <option value="date">Sort: Date</option>
        </select>
        <Button
          variant={criticalOnly ? "default" : "outline"}
          onClick={() => { setCriticalOnly(!criticalOnly); resetPage(); }}
          className="gap-2"
        >
          <Filter className="h-4 w-4" />
          Show Critical Only
        </Button>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-12 animate-pulse rounded-lg bg-muted" />
          ))}
        </div>
      ) : data ? (
        <>
          <TransactionsTable items={data.items} />
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Page {data.page} of {data.total_pages} ({data.total} total)
            </p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</Button>
              <Button variant="outline" size="sm" disabled={page >= data.total_pages} onClick={() => setPage(page + 1)}>Next</Button>
            </div>
          </div>
        </>
      ) : (
        <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
          Failed to load transactions. Is the backend running?
        </div>
      )}
    </div>
  );
}
