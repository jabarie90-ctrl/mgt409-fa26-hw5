const API = "http://localhost:8000";

async function read(path: string, init?: RequestInit) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = (body as { detail?: string }).detail;
    throw new Error(detail || res.statusText);
  }
  return body;
}

export type Ticket = {
  id: number;
  type: string;
  requester: string;
  subject: string;
  sku?: string | null;
  size?: string | null;
  qty?: number | null;
  lease_id?: number | null;
  invoice_id?: number | null;
  status: string;
  notes?: string | null;
};

export type Pay = {
  id: number;
  kind: string;
  ref_id: number;
  amount: number;
  approved_by?: string | null;
};

export type EventRow = {
  time?: string;
  ticket_id?: number;
  kind: string;
  agent?: string;
  tool?: string;
  to?: string;
  task?: string;
  args?: unknown;
  result?: unknown;
  verdict?: unknown;
};

export async function getTickets(): Promise<Ticket[]> {
  const data = await read("/tickets");
  return data.tickets as Ticket[];
}

export async function runTicket(ticketId: number) {
  return read(`/tickets/${ticketId}/run`, { method: "POST" });
}

export async function getEvents(ticketId?: number | null): Promise<EventRow[]> {
  const q = ticketId ? `?ticket_id=${ticketId}&limit=200` : "?limit=200";
  const data = await read(`/events${q}`);
  return data.events as EventRow[];
}

export async function getCash(): Promise<{ name: string; balance: number; date: string }> {
  return read("/cash");
}

export async function getDesk(): Promise<{ date_today?: string; notes?: string }> {
  return read("/desk");
}

export async function getPending(): Promise<Pay[]> {
  const data = await read("/payments/pending");
  return data.payments as Pay[];
}

export async function approvePay(paymentId: number, approvedBy: string) {
  return read("/approve-pay", {
    method: "POST",
    body: JSON.stringify({ payment_id: paymentId, approved_by: approvedBy }),
  });
}

export async function resetShop() {
  return read("/reset", { method: "POST" });
}
