import { BellRing } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client";

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  return Uint8Array.from([...rawData].map((char) => char.charCodeAt(0)));
}

export default function PushAlertsButton({ user }) {
  const [supported, setSupported] = useState(false);
  const [enabled, setEnabled] = useState(false);
  const [busy, setBusy] = useState(false);
  const [label, setLabel] = useState("Enable alerts");

  useEffect(() => {
    let alive = true;
    const check = async () => {
      const canPush = Boolean(user && "serviceWorker" in navigator && "PushManager" in window && "Notification" in window);
      if (!canPush) return;
      try {
        const registration = await navigator.serviceWorker.register("/sw.js");
        const subscription = await registration.pushManager.getSubscription();
        if (!alive) return;
        setSupported(true);
        setEnabled(Boolean(subscription));
        setLabel(subscription ? "Alerts on" : "Enable alerts");
      } catch {
        if (alive) setSupported(false);
      }
    };
    check();
    return () => { alive = false; };
  }, [user]);

  if (!user || !supported) return null;

  const enable = async () => {
    setBusy(true);
    try {
      const config = await api("/push/public-key");
      if (!config.enabled || !config.public_key) throw new Error("Push notification keys are not configured on the server");
      const permission = await Notification.requestPermission();
      if (permission !== "granted") throw new Error("Notification permission was not allowed");
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(config.public_key),
      });
      await api("/push/subscribe", {
        method: "POST",
        body: JSON.stringify({
          endpoint: subscription.endpoint,
          keys: subscription.toJSON().keys,
          user_agent: navigator.userAgent,
        }),
      });
      setEnabled(true);
      setLabel("Alerts on");
    } catch (err) {
      setLabel(err.message);
      window.setTimeout(() => setLabel(enabled ? "Alerts on" : "Enable alerts"), 3500);
    } finally {
      setBusy(false);
    }
  };

  const disable = async () => {
    setBusy(true);
    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();
      if (subscription) {
        await api(`/push/subscribe?endpoint=${encodeURIComponent(subscription.endpoint)}`, { method: "DELETE" });
        await subscription.unsubscribe();
      }
      setEnabled(false);
      setLabel("Enable alerts");
    } catch (err) {
      setLabel(err.message);
      window.setTimeout(() => setLabel(enabled ? "Alerts on" : "Enable alerts"), 3500);
    } finally {
      setBusy(false);
    }
  };

  return (
    <button className={`push-alert-button ${enabled ? "enabled" : ""}`} disabled={busy} onClick={enabled ? disable : enable}>
      <BellRing size={15} /> {busy ? "Working..." : label}
    </button>
  );
}
