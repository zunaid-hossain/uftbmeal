import { BellRing, X } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client";

export default function NotificationPopup({ user }) {
  const [active, setActive] = useState(null);

  useEffect(() => {
    if (!user) return undefined;
    let cancelled = false;

    const load = async () => {
      try {
        const notifications = await api("/notifications?limit=5");
        const latest = notifications[0];
        const seenId = Number(localStorage.getItem("uftb_last_notification_id") || 0);
        if (!cancelled && latest && latest.id > seenId) setActive(latest);
      } catch {
        // Notification polling should never interrupt the main app.
      }
    };

    load();
    const timer = window.setInterval(load, 15000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [user]);

  if (!active) return null;

  const close = () => {
    localStorage.setItem("uftb_last_notification_id", String(active.id));
    setActive(null);
  };

  return (
    <aside className="notification-popup" role="status" aria-live="polite">
      <button className="notification-close" onClick={close} aria-label="Close notification"><X size={16} /></button>
      <div className="notification-icon"><BellRing /></div>
      <div>
        <span className="kicker">Meal update</span>
        <h3>{active.title}</h3>
        <p>{active.message}</p>
        {active.creator && <small>Sent by {active.creator.full_name}</small>}
      </div>
    </aside>
  );
}
