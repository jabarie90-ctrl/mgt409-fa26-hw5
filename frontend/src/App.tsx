import { useCallback, useEffect, useMemo, useState } from "react";
import {
  approvePay,
  getCash,
  getDesk,
  getEvents,
  getPending,
  getTickets,
  resetShop,
  runTicket,
  type EventRow,
  type Pay,
  type Ticket,
} from "./api";
import "./App.css";

const AGENTS = [
  { id: "boss", label: "Boss", tone: "brass" },
  { id: "inventory", label: "Inventory", tone: "shelf" },
  { id: "accounting", label: "Accounting", tone: "ledger" },
  { id: "facilities", label: "Facilities", tone: "brick" },
  { id: "customer_service", label: "Customer Service", tone: "cream" },
] as const;

function agentOf(row: EventRow): string {
  return (row.agent || "boss").toLowerCase().replace(" ", "_");
}

function clip(value: unknown): string {
  if (value == null) return "";
  const text = typeof value === "string" ? value : JSON.stringify(value);
  return text.length > 220 ? text.slice(0, 220) + "…" : text;
}

function money(n: number): string {
  return n.toLocaleString("en-US", { style: "currency", currency: "USD" });
}

function agentSummary(rows: EventRow[]): string {
  const done = [...rows].reverse().find((row) => row.kind === "HANDOFF_RESULT" || row.kind === "RUN_END");
  if (done) {
    return clip(done.result || done.verdict || done.task);
  }
  const tools = [...new Set(rows.filter((row) => row.kind === "TOOL" && row.tool).map((row) => row.tool))];
  if (tools.length) return `Used ${tools.join(", ")}`;
  return "";
}

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [picked, setPicked] = useState<number | null>(() => {
    const n = Number(new URLSearchParams(window.location.search).get("ticket") || 101);
    return Number.isFinite(n) ? n : 101;
  });
  const [events, setEvents] = useState<EventRow[]>([]);
  const [pending, setPending] = useState<Pay[]>([]);
  const [cash, setCash] = useState<number | null>(null);
  const [desk, setDesk] = useState("—");
  const [running, setRunning] = useState(false);
  const [approver, setApprover] = useState("Jabarie");
  const [error, setError] = useState("");
  const [verdict, setVerdict] = useState("");

  const refresh = useCallback(async () => {
    const [t, e, p, c, d] = await Promise.all([
      getTickets(),
      getEvents(picked),
      getPending(),
      getCash(),
      getDesk(),
    ]);
    setTickets(t);
    setEvents(e);
    setPending(p);
    setCash(Number(c.balance));
    setDesk(String(d.date_today || "—"));
  }, [picked]);

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message));
  }, [refresh, picked]);

  useEffect(() => {
    if (!running) return;
    const id = window.setInterval(() => {
      Promise.all([getEvents(picked), getPending(), getCash()])
        .then(([e, p, c]) => {
          setEvents(e);
          setPending(p);
          setCash(Number(c.balance));
        })
        .catch(() => undefined);
    }, 1200);
    return () => window.clearInterval(id);
  }, [running, picked]);

  const pickedTicket = tickets.find((t) => t.id === picked) || null;
  const ticketEvents = useMemo(
    () => events.filter((row) => !picked || row.ticket_id === picked),
    [events, picked],
  );

  async function onRun() {
    if (!picked) return;
    setError("");
    setVerdict("");
    setRunning(true);
    try {
      const data = await runTicket(picked);
      const v = data.verdict as { status?: string; summary?: string };
      setVerdict(`${v.status || ""} — ${v.summary || ""}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "run failed");
    } finally {
      setRunning(false);
    }
  }

  async function onApprove(id: number) {
    setError("");
    try {
      await approvePay(id, approver.trim() || "store manager");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "approve failed");
    }
  }

  async function onReset() {
    setError("");
    setVerdict("");
    await resetShop();
    await refresh();
  }

  return (
    <div className="desk">
      <header className="mast">
        <div>
          <p className="eyebrow">Chapel Street · after hours</p>
          <h1>Campus Customs desk</h1>
        </div>
        <p className="mast-note">Agents stage money. A human stamps it. Nobody emails the customer.</p>
      </header>

      {error ? <div className="banner">{error}</div> : null}

      <div className="grid">
        <section className="spike">
          <h2>Ticket spike</h2>
          {tickets.map((t) => (
            <button
              key={t.id}
              className={`ticket ${picked === t.id ? "picked" : ""} ${t.status === "resolved" ? "done" : ""}`}
              onClick={() => setPicked(t.id)}
            >
              <span className="num">#{t.id}</span>
              <span className="who">{t.requester}</span>
              <span className="sub">{t.subject}</span>
              <span className="sku">
                {t.sku ? `${t.sku} ${t.size || ""} × ${t.qty ?? ""}` : t.type}
              </span>
              <span className={`chip ${t.status}`}>{t.status}</span>
              {t.status === "resolved" ? <span className="stamp">RESOLVED</span> : null}
            </button>
          ))}
          <div className="run-row">
            <button className="run" disabled={!picked || running} onClick={onRun}>
              {running ? "Desk is working…" : `Run ticket ${picked ?? ""}`}
            </button>
            {verdict ? <p className="verdict">{verdict}</p> : null}
            {pickedTicket?.notes ? <p className="notes">{pickedTicket.notes}</p> : null}
          </div>
        </section>

        <section className="radio">
          <h2>Agent radio</h2>
          <div className="shift">
            {AGENTS.map((agent) => {
              const rows = ticketEvents.filter((row) => agentOf(row) === agent.id);
              const summary = agentSummary(rows);
              return (
                <p key={`sum-${agent.id}`}>
                  <strong>{agent.label}.</strong> {summary || "Did not work this ticket."}
                </p>
              );
            })}
          </div>
          <div className="lanes">
            {AGENTS.map((agent) => {
              const rows = ticketEvents.filter((row) => agentOf(row) === agent.id);
              const last = rows.slice(-3);
              return (
                <article key={agent.id} className={`lane ${agent.tone}`}>
                  <h3>{agent.label}</h3>
                  {last.length === 0 ? (
                    <p className="quiet">quiet</p>
                  ) : (
                    last.map((row, i) => (
                      <p key={`${agent.id}-${i}`}>
                        <strong>{row.kind}</strong>{" "}
                        {row.tool || row.to || ""} {clip(row.task || row.result || row.args)}
                      </p>
                    ))
                  )}
                </article>
              );
            })}
          </div>
        </section>

        <aside className="till">
          <h2>Till</h2>
          <p className="shop-day">Shop today {desk}</p>
          <p className="led">{cash == null ? "—" : money(cash)}</p>
          <p className="till-cap">checking · cash only goes out</p>

          <h3>Waiting on a human</h3>
          {pending.length === 0 ? <p className="quiet">no staged pays</p> : null}
          {pending.map((pay) => (
            <div key={pay.id} className="pay">
              <p>
                #{pay.id} {pay.kind} {money(Number(pay.amount))} · ref {pay.ref_id}
              </p>
              <label>
                Stamped by
                <input value={approver} onChange={(e) => setApprover(e.target.value)} />
              </label>
              <button className="stamp-btn" onClick={() => onApprove(pay.id)}>
                Stamp approve
              </button>
            </div>
          ))}

          <button className="reset" onClick={onReset}>
            Reset shop books
          </button>
        </aside>
      </div>
    </div>
  );
}
