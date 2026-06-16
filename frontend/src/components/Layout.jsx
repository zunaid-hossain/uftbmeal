import { ClipboardCheck, CreditCard, LogOut, Menu, Plus, Soup, UserRound, Users, X } from "lucide-react";
import { useState } from "react";
import { Link, NavLink } from "react-router-dom";
import NotificationPopup from "./NotificationPopup";
import PushAlertsButton from "./PushAlertsButton";

const roomLabel = (user) => user?.room_number ? `Room ${user.room_number}` : "Outside Member";

export default function Layout({ user, logout, children }) {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);

  return (
    <div className="app-shell">
      <header className="site-header">
        <Link className="brand" to="/" onClick={close}>
          <span className="brand-mark"><Soup size={22} /></span>
          <span><b>UFTB</b><small>Meal Exchange</small></span>
        </Link>
        <button className="menu-toggle" onClick={() => setOpen(!open)} aria-label="Toggle navigation">
          {open ? <X /> : <Menu />}
        </button>
        <nav className={open ? "nav-links open" : "nav-links"}>
          <NavLink to="/" onClick={close}>Find a meal</NavLink>
          <NavLink to="/payments" onClick={close}><CreditCard size={15} /> Payments</NavLink>
          <NavLink to="/members" onClick={close}><Users size={15} /> Members</NavLink>
          {user?.is_meal_member && <NavLink to="/sell" onClick={close}>Sell meal</NavLink>}
          {user?.is_meal_member && <NavLink to="/attendance" onClick={close}><ClipboardCheck size={15} /> Attendance</NavLink>}
          {user?.role === "meal_manager" && <NavLink to="/manager" onClick={close}>Manager</NavLink>}
          {user ? (
            <>
              <span className="user-chip"><UserRound size={15} /> {roomLabel(user)}</span>
              <PushAlertsButton user={user} />
              <button className="nav-action ghost" onClick={() => { logout(); close(); }}><LogOut size={16} /> Log out</button>
            </>
          ) : (
            <Link className="nav-action" to="/login" onClick={close}>Sign in <Plus size={16} /></Link>
          )}
        </nav>
      </header>
      <NotificationPopup user={user} />
      <main>{children}</main>
      <footer>
        <div><span className="brand-mark small"><Soup size={16} /></span> UFTB Boys Hostel Meal Exchange</div>
        <p>This website was built by Robo&amp;tech.</p>
      </footer>
    </div>
  );
}
