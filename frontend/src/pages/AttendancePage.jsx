import { Check, ClipboardCheck, Moon, PauseCircle, PlayCircle, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client";

export default function AttendancePage() {
  const [attendance, setAttendance] = useState({ lunch_checked: false, dinner_checked: false });
  const [weekStatus, setWeekStatus] = useState({ skipped_this_week: false, skip_reason: "" });
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const load = async () => {
    try {
      const [attendanceData, weekData] = await Promise.all([api("/attendance/today"), api("/me/week-status")]);
      setAttendance(attendanceData);
      setWeekStatus(weekData);
      setReason(weekData.skip_reason || "");
      setError("");
    } catch (err) { setError(err.message); }
  };
  useEffect(() => { load(); }, []);
  const check = async (meal) => {
    try { setAttendance(await api(`/attendance/${meal}`, { method: "POST" })); setMessage(`${meal[0].toUpperCase() + meal.slice(1)} attendance recorded.`); setError(""); }
    catch (err) { setError(err.message); }
  };
  const skipWeek = async () => {
    try {
      const data = await api("/me/skip-week", { method: "POST", body: JSON.stringify({ reason }) });
      setWeekStatus(data);
      setAttendance({ ...attendance, skipped_this_week: true });
      setMessage("You skipped this week's meal cycle. The manager will see it.");
      setError("");
    } catch (err) { setError(err.message); }
  };
  const joinWeek = async () => {
    try {
      const data = await api("/me/skip-week", { method: "DELETE" });
      setWeekStatus(data);
      setAttendance({ ...attendance, skipped_this_week: false });
      setReason("");
      setMessage("You joined this week's meal cycle again.");
      setError("");
    } catch (err) { setError(err.message); }
  };
  const notifyMealProvided = async (mealType) => {
    try {
      await api("/notifications/meal-provided", { method: "POST", body: JSON.stringify({ meal_type: mealType }) });
      setMessage(`${mealType} provided notification sent to everyone.`);
      setError("");
    } catch (err) { setError(err.message); }
  };
  return <section className="attendance-page content-section">
    <div className="page-banner"><div><span className="eyebrow"><span /> Today's record</span><h1>Meal attendance</h1><p>Tick each meal once after you eat. Your manager sees only the attendance status.</p></div><ClipboardCheck /></div>
    {message && <div className="form-success"><Check />{message}</div>}{error && <div className="form-error">{error}</div>}
    <div className={`skip-week-panel ${weekStatus.skipped_this_week ? "skipped" : ""}`}>
      <div>
        <span className="kicker">Weekly choice</span>
        <h2>{weekStatus.skipped_this_week ? "You are skipping this week" : "Not eating this week?"}</h2>
        <p>{weekStatus.skipped_this_week ? "You will not appear in unpaid reminders or remaining attendance for this cycle." : "Skip only the current weekly cycle. You can join again before recording attendance."}</p>
      </div>
      <input value={reason} onChange={(event) => setReason(event.target.value)} disabled={weekStatus.skipped_this_week} placeholder="Optional reason, e.g. going home this week" />
      {weekStatus.skipped_this_week ? <button onClick={joinWeek}><PlayCircle /> Join this week again</button> : <button onClick={skipWeek}><PauseCircle /> Skip this week</button>}
    </div>
    <div className="attendance-grid">
      <button className={attendance.lunch_checked ? "checked" : ""} disabled={attendance.lunch_checked || weekStatus.skipped_this_week} onClick={() => check("lunch")}><Sun /><span><small>Midday meal</small><b>{attendance.lunch_checked ? "Lunch checked" : weekStatus.skipped_this_week ? "Skipped this week" : "I ate lunch"}</b></span>{attendance.lunch_checked && <Check />}</button>
      <button className={attendance.dinner_checked ? "checked" : ""} disabled={attendance.dinner_checked || weekStatus.skipped_this_week} onClick={() => check("dinner")}><Moon /><span><small>Evening meal</small><b>{attendance.dinner_checked ? "Dinner checked" : weekStatus.skipped_this_week ? "Skipped this week" : "I ate dinner"}</b></span>{attendance.dinner_checked && <Check />}</button>
    </div>
    <div className="notify-panel">
      <div>
        <span className="kicker">Notify everyone</span>
        <h2>Meal has been provided?</h2>
        <p>Meal manager or any meal member can send a popup update to all logged-in users.</p>
      </div>
      <button onClick={() => notifyMealProvided("Lunch")}><Sun /> Notify lunch provided</button>
      <button onClick={() => notifyMealProvided("Dinner")}><Moon /> Notify dinner provided</button>
    </div>
  </section>;
}
