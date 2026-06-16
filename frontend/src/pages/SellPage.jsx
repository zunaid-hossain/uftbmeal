import { ArrowLeft, CalendarDays, CheckCircle2, CircleDollarSign, Moon, NotebookPen, Sun } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";

function localDateValue() {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}

export default function SellPage() {
  const [form, setForm] = useState({ meal_type: "Lunch", date: localDateValue(), price: "", note: "", status: "available" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const change = (event) => setForm({ ...form, [event.target.name]: event.target.value });
  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setError("");
    try { await api("/meals", { method: "POST", body: JSON.stringify({ ...form, price: Number(form.price) }) }); navigate("/"); }
    catch (err) { setError(err.message); setBusy(false); }
  };

  return (
    <section className="form-page">
      <div className="form-page-heading"><Link to="/"><ArrowLeft /> Back to meal board</Link><span className="kicker">Share a meal</span><h1>Turn an extra meal<br />into someone's good news.</h1><p>Only lunch and dinner meals are accepted. Your WhatsApp number is shared when a buyer contacts you.</p></div>
      <form className="feature-form" onSubmit={submit}>
        <div className="step-label"><span>01</span><div><b>Choose the meal</b><small>What are you offering?</small></div></div>
        <div className="meal-type-picker">
          <label className={form.meal_type === "Lunch" ? "selected" : ""}><input type="radio" name="meal_type" value="Lunch" checked={form.meal_type === "Lunch"} onChange={change} /><Sun /><span><b>Lunch</b><small>Midday meal</small></span><CheckCircle2 /></label>
          <label className={form.meal_type === "Dinner" ? "selected" : ""}><input type="radio" name="meal_type" value="Dinner" checked={form.meal_type === "Dinner"} onChange={change} /><Moon /><span><b>Dinner</b><small>Evening meal</small></span><CheckCircle2 /></label>
        </div>
        <div className="form-divider" />
        <div className="step-label"><span>02</span><div><b>Add the details</b><small>Keep it clear and simple.</small></div></div>
        <div className="two-columns">
          <label>Date<div className="input-wrap"><CalendarDays /><input type="date" name="date" value={form.date} onChange={change} required /></div></label>
          <label>Price (Tk)<div className="input-wrap"><CircleDollarSign /><input type="number" name="price" value={form.price} onChange={change} min="1" max="10000" required placeholder="70" /></div></label>
        </div>
        <label>Note <span className="optional">optional</span><div className="input-wrap textarea"><NotebookPen /><textarea name="note" value={form.note} onChange={change} maxLength="500" placeholder="Token included, collect before 1 PM..." /></div></label>
        {error && <div className="form-error">{error}</div>}
        <button className="primary-button submit-button" disabled={busy}>{busy ? "Publishing..." : "Publish meal offer"}<CheckCircle2 size={19} /></button>
      </form>
    </section>
  );
}
