import { ArrowRight, LockKeyhole, MessageCircle, Soup, UserRound } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { api, saveSession } from "../api/client";

export default function AuthPage({ mode, onAuth }) {
  const register = mode === "register";
  const [form, setForm] = useState({ member_type: "hostel_resident", full_name: "", room_number: "", address_or_identity_note: "", whatsapp_number: "", password: "", role: "student", manager_registration_code: "" });
  const [registration, setRegistration] = useState({ is_open: true, message: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (register) api("/registration").then(setRegistration).catch(() => {});
  }, [register]);

  const change = (event) => setForm({ ...form, [event.target.name]: event.target.value });
  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setError("");
    try {
      if (register && !registration.is_open && form.role !== "meal_manager") {
        throw new Error(registration.message || "Registration is currently closed");
      }
      const payload = register ? form : { whatsapp_number: form.whatsapp_number, password: form.password };
      const data = await api(register ? "/auth/register" : "/auth/login", { method: "POST", body: JSON.stringify(payload) });
      saveSession(data); onAuth(data.user); navigate(location.state?.from || "/");
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };

  return (
    <section className="auth-page">
      <div className="auth-intro">
        <span className="brand-mark large"><Soup size={28} /></span>
        <span className="eyebrow"><span /> Hostel community</span>
        <h1>{register ? "Join the meal circle." : "Welcome back."}</h1>
        <p>{register ? "Create your hostel profile and exchange meals with students just a few doors away." : "Sign in to post a meal, manage your listings, and help reduce food waste."}</p>
        <blockquote>"One unused meal can make someone else's day easier."</blockquote>
      </div>
      <div className="auth-card">
        <div><span className="kicker">{register ? "Create account" : "Sign in"}</span><h2>{register ? "Your hostel details" : "Continue to UFTB Meals"}</h2></div>
        <form onSubmit={submit}>
          {register && !registration.is_open && <div className="form-error">{registration.message || "Student registration is currently closed."}</div>}
          {register && <><label>Member type<select name="member_type" value={form.member_type} onChange={change}><option value="hostel_resident">Hostel Resident</option><option value="outside_member">Outside Meal Member</option></select></label>
          <label>Full name<div className="input-wrap"><UserRound /><input name="full_name" value={form.full_name} onChange={change} required placeholder="e.g. Nayeem Hasan" /></div></label>
          {form.member_type === "hostel_resident" ? <label>Room number<input name="room_number" value={form.room_number} onChange={change} required placeholder="e.g. B-204" /></label> : <label>Identity note<input name="address_or_identity_note" value={form.address_or_identity_note} onChange={change} required placeholder="e.g. Nearby mess student, department, address" /><small>Outside members do not need a hostel room number.</small></label>}</>}
          <label>WhatsApp number<div className="input-wrap"><MessageCircle /><input name="whatsapp_number" value={form.whatsapp_number} onChange={change} required placeholder="88017XXXXXXXX" /></div><small>Bangladesh format with country code, no + sign.</small></label>
          <label>Password<div className="input-wrap"><LockKeyhole /><input type="password" name="password" value={form.password} onChange={change} required minLength="8" placeholder="At least 8 characters" /></div></label>
          {register && <><label>Account type<select name="role" value={form.role} onChange={change}><option value="student">Student</option><option value="meal_manager">Meal manager</option></select></label>
          {form.role === "meal_manager" && <label>Manager registration code<input type="password" name="manager_registration_code" value={form.manager_registration_code} onChange={change} required placeholder="Private code from hostel administration" /></label>}</>}
          {error && <div className="form-error">{error}</div>}
          <button className="primary-button submit-button" disabled={busy || (register && !registration.is_open && form.role !== "meal_manager")}>{busy ? "Please wait..." : register ? "Create my account" : "Sign in"}<ArrowRight size={18} /></button>
        </form>
        <p className="auth-switch">{register ? "Already registered?" : "New to the exchange?"} <Link to={register ? "/login" : "/register"}>{register ? "Sign in" : "Create an account"}</Link></p>
      </div>
    </section>
  );
}
