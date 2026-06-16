import { BellRing, Brush, CheckCircle2, CircleDollarSign, ClipboardCheck, Download, Edit3, FileSpreadsheet, MessageCircle, Moon, PauseCircle, RefreshCw, ShieldCheck, Sun, Trash2, Users, Utensils, XCircle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";

const emptyStats = { total_members: 0, paid_members: 0, unpaid_members: 0, skipped_members: 0, lunch_attendance: 0, dinner_attendance: 0, available_meals: 0, sold_meals: 0 };

function reminderLink(person) {
  const message = `Assalamu Alaikum ${person.full_name}. Reminder from UFTB Boys Hostel Meal Manager: your weekly meal payment is still unpaid. Please complete it soon. ${roomLabel(person)}`;
  return `https://wa.me/${person.whatsapp_number}?text=${encodeURIComponent(message)}`;
}

const memberTypeLabel = (type) => type === "outside_member" ? "Outside Member" : "Hostel Resident";
const roomLabel = (person) => person.room_number ? `Room ${person.room_number}` : "Outside Member";
const todayIso = () => new Date().toISOString().slice(0, 10);
const csvCell = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
const downloadCsv = (filename, rows) => {
  const csv = rows.map((row) => row.map(csvCell).join(",")).join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
};

export default function ManagerPage() {
  const [form, setForm] = useState({ lunch_menu: "", dinner_menu: "", notice: "" });
  const [registration, setRegistration] = useState({ is_open: true, message: "" });
  const [stats, setStats] = useState(emptyStats);
  const [users, setUsers] = useState([]);
  const [remaining, setRemaining] = useState({ lunch: [], dinner: [] });
  const [attendanceRows, setAttendanceRows] = useState([]);
  const [bazar, setBazar] = useState({ total_amount: 0, expense_count: 0, rows: [] });
  const [bazarForm, setBazarForm] = useState({ date: todayIso(), item_name: "", amount: "", note: "" });
  const [cycle, setCycle] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const unpaidMembers = useMemo(() => users.filter((user) => user.is_meal_member && user.payment_status === "unpaid" && !user.skipped_this_week), [users]);

  const load = async () => {
    try {
      const [menu, statData, userData, remainingData, attendanceData, cycleData, registrationData, bazarData] = await Promise.all([
        api("/menu/today"), api("/dashboard/stats"), api("/manager/users"), api("/attendance/remaining"), api("/attendance/dashboard"), api("/cycle"), api("/registration"), api("/manager/bazar"),
      ]);
      setForm({ lunch_menu: menu.lunch_menu, dinner_menu: menu.dinner_menu, notice: "" });
      setStats(statData);
      setUsers(userData);
      setRemaining(remainingData);
      setAttendanceRows(attendanceData);
      setCycle(cycleData);
      setRegistration(registrationData);
      setBazar(bazarData);
      setError("");
    } catch (err) { setError(err.message); }
  };

  useEffect(() => { load(); }, []);
  const change = (event) => setForm({ ...form, [event.target.name]: event.target.value });
  const updateUserField = (id, field, value) => setUsers(users.map((person) => person.id === id ? { ...person, [field]: value } : person));
  const submit = async (event) => { event.preventDefault(); try { await api("/manager/menu", { method: "POST", body: JSON.stringify(form) }); setMessage("Today's menu and notice are live."); load(); } catch (err) { setError(err.message); } };
  const toggleMember = async (person) => { try { await api(`/members/${person.id}`, { method: "PATCH", body: JSON.stringify({ is_meal_member: !person.is_meal_member }) }); setMessage(`${person.full_name} ${person.is_meal_member ? "removed from" : "added to"} meal members.`); load(); } catch (err) { setError(err.message); } };
  const togglePayment = async (person) => { try { await api(`/payments/${person.id}`, { method: "PATCH", body: JSON.stringify({ status: person.payment_status === "paid" ? "unpaid" : "paid" }) }); setMessage(`${person.full_name}'s payment was updated.`); load(); } catch (err) { setError(err.message); } };
  const toggleWeekActive = async (person) => {
    try {
      const active = person.skipped_this_week;
      await api(`/manager/users/${person.id}/week-active`, { method: "PATCH", body: JSON.stringify({ active, reason: active ? "" : "Inactive this week by manager" }) });
      setMessage(`${person.full_name}'s weekly meal is now ${active ? "active" : "inactive"}.`);
      load();
    } catch (err) { setError(err.message); }
  };
  const saveUser = async (person) => {
    try {
      await api(`/manager/users/${person.id}`, { method: "PATCH", body: JSON.stringify({ member_type: person.member_type, full_name: person.full_name, room_number: person.room_number || null, address_or_identity_note: person.address_or_identity_note || null, whatsapp_number: person.whatsapp_number, role: person.role }) });
      setMessage(`${person.full_name}'s registration was updated.`);
      load();
    } catch (err) { setError(err.message); }
  };
  const deleteUser = async (person) => {
    if (!window.confirm(`Remove ${person.full_name}'s account from the database? This cannot be undone.`)) return;
    try {
      await api(`/manager/users/${person.id}`, { method: "DELETE" });
      setMessage(`${person.full_name}'s account was removed.`);
      load();
    } catch (err) { setError(err.message); }
  };
  const notifyAllUnpaid = async () => {
    try {
      const result = await api("/manager/notifications/unpaid-payment-reminder", { method: "POST", body: "{}" });
      if (!result.notified) {
        setMessage("No unpaid active members found for this week.");
      } else {
        setMessage(`Reminder sent to ${result.notified} unpaid member${result.notified === 1 ? "" : "s"}. Push delivered to ${result.push_sent} device${result.push_sent === 1 ? "" : "s"}.`);
      }
      load();
    } catch (err) { setError(err.message); }
  };
  const saveRegistration = async () => {
    try {
      setRegistration(await api("/manager/registration", { method: "PATCH", body: JSON.stringify({ ...registration, max_registrations: registration.max_registrations ? Number(registration.max_registrations) : null }) }));
      setMessage(`Registration is now ${registration.is_open ? "open" : "closed"}.`);
    } catch (err) { setError(err.message); }
  };
  const startCycle = async () => { if (!window.confirm("Start a new weekly cycle? This clears listings, attendance, notices, and weekly payments.")) return; try { setCycle(await api("/manager/start-new-cycle", { method: "POST", body: "{}" })); setMessage("A new seven-day meal cycle has started."); load(); } catch (err) { setError(err.message); } };
  const addBazarExpense = async (event) => {
    event.preventDefault();
    try {
      await api("/manager/bazar", { method: "POST", body: JSON.stringify({ ...bazarForm, amount: Number(bazarForm.amount) }) });
      setBazarForm({ date: todayIso(), item_name: "", amount: "", note: "" });
      setMessage("Bazar expense added to this week's sheet.");
      load();
    } catch (err) { setError(err.message); }
  };
  const deleteBazarExpense = async (expense) => {
    try { await api(`/manager/bazar/${expense.id}`, { method: "DELETE" }); setMessage("Bazar expense removed."); load(); }
    catch (err) { setError(err.message); }
  };
  const downloadPeople = () => downloadCsv(`uftb-members-${todayIso()}.csv`, [
    ["Name", "Member type", "Room", "Identity note", "WhatsApp", "Role", "Meal member", "This week meal", "Payment"],
    ...users.map((person) => [person.full_name, memberTypeLabel(person.member_type), person.room_number || "Outside Member", person.address_or_identity_note || "", person.whatsapp_number, person.role, person.is_meal_member ? "Yes" : "No", person.skipped_this_week ? "Inactive" : "Active", person.payment_status]),
  ]);
  const downloadBazar = () => downloadCsv(`uftb-bazar-${cycle?.start_date || todayIso()}.csv`, [
    ["Date", "Item", "Amount", "Note", "Added by"],
    ...bazar.rows.map((row) => [row.date, row.item_name, row.amount, row.note || "", row.creator?.full_name || ""]),
    ["", "Total", bazar.total_amount, "", ""],
  ]);

  const statCards = [
    ["Total members", stats.total_members, Users], ["Paid", stats.paid_members, CheckCircle2], ["Unpaid", stats.unpaid_members, XCircle], ["Inactive", stats.skipped_members, PauseCircle],
    ["Lunch ticks", stats.lunch_attendance, Sun], ["Dinner ticks", stats.dinner_attendance, Moon], ["Available", stats.available_meals, Utensils], ["Sold", stats.sold_meals, CircleDollarSign],
  ];

  return <section className="manager-page content-section dashboard-redesign">
    <div className="manager-hero dashboard-hero">
      <div><span className="eyebrow"><span /> Manager command center</span><h1>Dining hall dashboard</h1><p>{cycle ? `Active cycle: ${cycle.start_date} to ${cycle.end_date}` : "Start the first weekly cycle to initialize payments."}</p></div>
      <div className="cycle-badge"><ShieldCheck /><span>{registration.is_open ? "Registration open" : "Registration closed"}</span></div>
    </div>

    <div className="dashboard-stats">{statCards.map(([label, value, Icon]) => <article key={label}><Icon /><span>{label}</span><b>{value}</b></article>)}</div>
    {message && <div className="form-success dashboard-alert"><CheckCircle2 />{message}</div>}{error && <div className="form-error dashboard-alert">{error}</div>}

    <div className="manager-grid dashboard-top-grid">
      <form className="manager-form dashboard-card" onSubmit={submit}>
        <div className="form-title"><Brush /><div><span className="kicker">Today's board</span><h2>Dining information</h2></div></div>
        <label><span><Sun /> Lunch menu</span><textarea name="lunch_menu" value={form.lunch_menu} onChange={change} required /></label>
        <label><span><Moon /> Dinner menu</span><textarea name="dinner_menu" value={form.dinner_menu} onChange={change} required /></label>
        <label><span><BellRing /> Weekly notice</span><textarea name="notice" value={form.notice} onChange={change} placeholder="Optional hostel-wide update" /></label>
        <button className="primary-button submit-button">Publish updates</button>
      </form>

      <aside className="dashboard-side-stack">
        <div className="cleanup-card dashboard-card">
          <RefreshCw /><span className="kicker">Weekly cycle</span><h3>Start fresh week</h3><p>Clears weekly records, then creates a new seven-day cycle.</p><button className="secondary-button" onClick={startCycle}>Start new cycle</button>
        </div>
        <div className="cleanup-card dashboard-card registration-control">
          <Edit3 /><span className="kicker">Registration</span><h3>{registration.is_open ? "Open for students" : "Closed now"}</h3>
          <label className="switch-row"><input type="checkbox" checked={registration.is_open} onChange={(event) => setRegistration({ ...registration, is_open: event.target.checked })} /> Allow student registration</label>
          <label className="limit-field">Registration limit<input type="number" min="1" value={registration.max_registrations || ""} onChange={(event) => setRegistration({ ...registration, max_registrations: event.target.value })} placeholder="No limit" /></label>
          <p className="registration-meter">{registration.current_registrations || 0} registered{registration.max_registrations ? ` · ${registration.remaining_slots ?? 0} slots left` : " · no limit set"}</p>
          <textarea value={registration.message} onChange={(event) => setRegistration({ ...registration, message: event.target.value })} />
          <button className="secondary-button" onClick={saveRegistration}>{registration.is_open ? "Update registration" : "Reopen/update registration"}</button>
        </div>
      </aside>
    </div>

    <div className="manager-section dashboard-card bazar-section">
      <div className="section-title-row"><div className="form-title"><FileSpreadsheet /><div><span className="kicker">Weekly bazar sheet</span><h2>Bazar calculation</h2></div></div><button className="secondary-button export-button" onClick={downloadBazar}><Download size={16} /> Download Excel CSV</button></div>
      <div className="bazar-summary"><article><span>Total bazar</span><b>{Number(bazar.total_amount).toLocaleString()} Tk</b></article><article><span>Entries</span><b>{bazar.expense_count}</b></article><article><span>Cycle</span><b>{cycle ? `${cycle.start_date} to ${cycle.end_date}` : "No cycle"}</b></article></div>
      <form className="bazar-form" onSubmit={addBazarExpense}>
        <input type="date" value={bazarForm.date} onChange={(event) => setBazarForm({ ...bazarForm, date: event.target.value })} required />
        <input value={bazarForm.item_name} onChange={(event) => setBazarForm({ ...bazarForm, item_name: event.target.value })} placeholder="Item name, e.g. rice, chicken" required />
        <input type="number" min="1" step="0.01" value={bazarForm.amount} onChange={(event) => setBazarForm({ ...bazarForm, amount: event.target.value })} placeholder="Amount Tk" required />
        <input value={bazarForm.note} onChange={(event) => setBazarForm({ ...bazarForm, note: event.target.value })} placeholder="Optional note" />
        <button className="primary-button">Add</button>
      </form>
      <div className="data-card bazar-table"><div className="data-row bazar-row data-head"><span>Date</span><span>Item</span><span>Amount</span><span>Note</span><span>Action</span></div>{bazar.rows.length ? bazar.rows.map((row) => <div className="data-row bazar-row" key={row.id}><span>{row.date}</span><b>{row.item_name}</b><span>{Number(row.amount).toLocaleString()} Tk</span><span>{row.note || "No note"}</span><button className="mini-action danger" onClick={() => deleteBazarExpense(row)}><Trash2 size={14} /> Delete</button></div>) : <p className="soft-copy table-empty">No bazar entries for this cycle yet.</p>}</div>
    </div>

    <div className="manager-section dashboard-card">
      <div className="section-title-row"><div className="form-title"><MessageCircle /><div><span className="kicker">Payment reminders</span><h2>Unpaid members</h2></div></div><div className="reminder-actions"><span className="unpaid-count">{unpaidMembers.length} unpaid</span><button className="secondary-button export-button notify-all-button" disabled={!unpaidMembers.length} onClick={notifyAllUnpaid}><BellRing size={16} /> Notify all unpaid</button></div></div>
      <div className="reminder-list">{unpaidMembers.length ? unpaidMembers.map((person) => <a key={person.id} className="reminder-chip" href={reminderLink(person)} target="_blank" rel="noreferrer"><MessageCircle /> {roomLabel(person)} · {person.full_name}</a>) : <p className="soft-copy">Everyone is marked paid for this cycle.</p>}</div>
    </div>

    <div className="manager-section dashboard-card member-management-card"><div className="section-title-row"><div className="form-title"><Users /><div><span className="kicker">Membership, payments & registration</span><h2>Manage students</h2></div></div><button className="secondary-button export-button" onClick={downloadPeople}><Download size={16} /> Download people</button></div><div className="data-card manager-table"><div className="data-row manager-user-row data-head"><span>Student</span><span>Type</span><span>Room</span><span>Identity</span><span>WhatsApp</span><span>Role</span><span>Member</span><span>Meal active</span><span>Payment</span><span>Save</span><span>Remove</span></div>{users.map((person) => <div className="data-row manager-user-row" key={person.id}><input value={person.full_name} onChange={(event) => updateUserField(person.id, "full_name", event.target.value)} /><select value={person.member_type} onChange={(event) => updateUserField(person.id, "member_type", event.target.value)}><option value="hostel_resident">Hostel Resident</option><option value="outside_member">Outside Member</option></select><input value={person.room_number || ""} placeholder={person.member_type === "outside_member" ? "Optional" : "Required"} onChange={(event) => updateUserField(person.id, "room_number", event.target.value)} /><input value={person.address_or_identity_note || ""} placeholder={person.member_type === "outside_member" ? "Identity note" : "Optional"} onChange={(event) => updateUserField(person.id, "address_or_identity_note", event.target.value)} /><input value={person.whatsapp_number} onChange={(event) => updateUserField(person.id, "whatsapp_number", event.target.value)} /><select value={person.role} onChange={(event) => updateUserField(person.id, "role", event.target.value)}><option value="student">student</option><option value="meal_manager">meal_manager</option></select><button className={`mini-action ${person.is_meal_member ? "active" : ""}`} title={memberTypeLabel(person.member_type)} onClick={() => toggleMember(person)}>{person.is_meal_member ? "Member" : "Add"}</button><button disabled={!person.is_meal_member} className={`mini-action meal-active ${person.skipped_this_week ? "inactive" : "active"}`} onClick={() => toggleWeekActive(person)}>{person.skipped_this_week ? "Inactive" : "Active"}</button><button disabled={!person.is_meal_member || person.skipped_this_week} className={`mini-action payment ${person.skipped_this_week ? "skipped" : person.payment_status}`} onClick={() => togglePayment(person)}>{person.skipped_this_week ? "inactive" : person.payment_status}</button><button className="mini-action save" onClick={() => saveUser(person)}>Save</button><button className="mini-action danger" onClick={() => deleteUser(person)}><Trash2 size={14} /> Delete</button></div>)}</div></div>

    <div className="manager-section"><div className="form-title"><ClipboardCheck /><div><span className="kicker">Today's attendance</span><h2>Members remaining</h2></div></div><div className="remaining-grid"><Remaining title="Lunch remaining" icon={<Sun />} people={remaining.lunch} /><Remaining title="Dinner remaining" icon={<Moon />} people={remaining.dinner} /></div></div>
    <div className="manager-section dashboard-card"><div className="form-title"><ClipboardCheck /><div><span className="kicker">Attendance dashboard</span><h2>Lunch and dinner ticks</h2></div></div><div className="data-card attendance-table"><div className="data-row attendance-row data-head"><span>Name</span><span>Room / identity</span><span>Member type</span><span>Lunch tick</span><span>Dinner tick</span></div>{attendanceRows.map((row) => <div className="data-row attendance-row" key={row.user_id}><b>{row.full_name}</b><span>{row.room_number ? `Room ${row.room_number}` : "Outside Member"}{row.address_or_identity_note ? ` · ${row.address_or_identity_note}` : ""}</span><span>{memberTypeLabel(row.member_type)}</span><span className={`tick-pill ${row.skipped_this_week ? "skip" : row.lunch_checked ? "yes" : "no"}`}>{row.skipped_this_week ? "Skipped" : row.lunch_checked ? "Yes" : "No"}</span><span className={`tick-pill ${row.skipped_this_week ? "skip" : row.dinner_checked ? "yes" : "no"}`}>{row.skipped_this_week ? "Skipped" : row.dinner_checked ? "Yes" : "No"}</span></div>)}</div></div>
  </section>;
}

function Remaining({ title, icon, people }) {
  return <article className="remaining-card dashboard-card"><div>{icon}<h3>{title}</h3><b>{people.length}</b></div>{people.length ? <ul>{people.map((person) => <li key={person.user_id}><span>{roomLabel(person)}</span>{person.full_name}</li>)}</ul> : <p>Everyone has checked this meal.</p>}</article>;
}
