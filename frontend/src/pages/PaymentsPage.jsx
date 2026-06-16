import { CheckCircle2, CircleDollarSign, PauseCircle, WalletCards, XCircle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";

const label = (type) => type === "outside_member" ? "Outside Member" : "Hostel Resident";
const roomLabel = (item) => item.room_number ? `Room ${item.room_number}` : "Outside Member";

export default function PaymentsPage() {
  const [payments, setPayments] = useState([]);
  const [error, setError] = useState("");
  useEffect(() => { api("/payments").then(setPayments).catch((err) => setError(err.message)); }, []);
  const paid = useMemo(() => payments.filter((item) => item.status === "paid").length, [payments]);
  const skipped = useMemo(() => payments.filter((item) => item.skipped_this_week).length, [payments]);
  return <section className="directory-page content-section">
    <div className="page-banner"><div><span className="eyebrow"><span /> Weekly accounts</span><h1>Payment status</h1><p>See the current payment position for every active meal member.</p></div><WalletCards /></div>
    <div className="stat-strip"><div><CircleDollarSign /><span>Total members</span><b>{payments.length}</b></div><div><CheckCircle2 /><span>Paid members</span><b>{paid}</b></div><div><PauseCircle /><span>Skipped week</span><b>{skipped}</b></div><div><XCircle /><span>Unpaid members</span><b>{payments.length - skipped - paid}</b></div></div>
    {error && <div className="form-error">{error}</div>}
    <div className="data-card"><div className="data-row payment-row data-head"><span>Name</span><span>Member type</span><span>Room / identity</span><span>Status</span></div>{payments.map((item) => <div className="data-row payment-row" key={item.user_id}><b>{item.full_name}</b><span>{label(item.member_type)}</span><span>{roomLabel(item)}{item.address_or_identity_note ? ` · ${item.address_or_identity_note}` : ""}</span><span className={`status-pill ${item.skipped_this_week ? "skipped" : item.status}`}>{item.skipped_this_week ? <PauseCircle /> : item.status === "paid" ? <CheckCircle2 /> : <XCircle />}{item.skipped_this_week ? "skipped" : item.status}</span></div>)}</div>
  </section>;
}
