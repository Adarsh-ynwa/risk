"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, LoaderCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, type TransactionCreateRequest } from "@/lib/api";

const initialForm: TransactionCreateRequest = {
  customer_id: "CUST-DEMO-001",
  transaction_amount: 2500,
  country: "India",
  city: "Mumbai",
  merchant_category: "Electronics",
  payment_method: "Credit Card",
  device_type: "Mobile",
  account_balance: 10000,
  customer_age: 30,
  credit_score: 650,
  account_age_years: 2,
  num_prev_transactions: 10,
  transaction_freq_monthly: 5,
  distance_from_home_km: 5,
  time_since_last_txn_hrs: 24,
  is_international: false,
  failed_attempts: 0,
  pin_changed_recently: false,
};

const fields: { key: keyof TransactionCreateRequest; label: string; type?: "text" | "number" }[] = [
  { key: "customer_id", label: "Customer ID" },
  { key: "transaction_amount", label: "Transaction amount", type: "number" },
  { key: "country", label: "Country" },
  { key: "city", label: "City" },
  { key: "merchant_category", label: "Merchant category" },
  { key: "payment_method", label: "Payment method" },
  { key: "device_type", label: "Device type" },
  { key: "account_balance", label: "Account balance", type: "number" },
  { key: "customer_age", label: "Customer age", type: "number" },
  { key: "credit_score", label: "Credit score", type: "number" },
  { key: "account_age_years", label: "Account age (years)", type: "number" },
  { key: "num_prev_transactions", label: "Previous transactions", type: "number" },
  { key: "transaction_freq_monthly", label: "Transactions/month", type: "number" },
  { key: "distance_from_home_km", label: "Distance from home (km)", type: "number" },
  { key: "time_since_last_txn_hrs", label: "Hours since last transaction", type: "number" },
  { key: "failed_attempts", label: "Failed attempts", type: "number" },
];

export default function NewTransactionPage() {
  const router = useRouter();
  const [form, setForm] = useState(initialForm);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const result = await api.createTransaction(form);
      router.push(`/transactions/${result.transaction_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not analyze the transaction.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <Button variant="ghost" size="sm" onClick={() => router.back()} className="mb-3 gap-2">
          <ArrowLeft className="h-4 w-4" />Back to transactions
        </Button>
        <h1 className="text-3xl font-bold">Add a new transaction</h1>
        <p className="text-muted-foreground">Submitting this payment automatically creates a unique transaction ID, saves it, and runs the risk model.</p>
      </div>

      <form onSubmit={submit} className="space-y-6 rounded-xl border bg-card p-5 shadow-sm">
        <div className="grid gap-4 sm:grid-cols-2">
          {fields.map(({ key, label, type = "text" }) => (
            <label key={key} className="space-y-1.5 text-sm font-medium">
              {label}
              <Input
                type={type}
                step={type === "number" ? "any" : undefined}
                min={type === "number" ? 0 : undefined}
                required
                value={form[key] as string | number}
                onChange={(event) => setForm((current) => ({
                  ...current,
                  [key]: type === "number" ? Number(event.target.value) : event.target.value,
                }))}
              />
            </label>
          ))}
        </div>

        <div className="flex flex-wrap gap-6 rounded-lg bg-muted/50 p-4 text-sm">
          <label className="flex items-center gap-2"><input type="checkbox" checked={form.is_international} onChange={(e) => setForm({ ...form, is_international: e.target.checked })} />International payment</label>
          <label className="flex items-center gap-2"><input type="checkbox" checked={form.pin_changed_recently} onChange={(e) => setForm({ ...form, pin_changed_recently: e.target.checked })} />PIN changed recently</label>
        </div>

        {error && <p className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">{error}</p>}

        <Button type="submit" disabled={submitting} className="gap-2">
          {submitting && <LoaderCircle className="h-4 w-4 animate-spin" />}
          {submitting ? "Analyzing transaction..." : "Submit and analyze"}
        </Button>
      </form>
    </div>
  );
}
