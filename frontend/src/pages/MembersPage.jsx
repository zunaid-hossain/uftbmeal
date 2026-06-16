import { BadgeCheck, PauseCircle, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client";

const label = (type) => type === "outside_member" ? "Outside Member" : "Hostel Resident";
const roomLabel = (member) => member.room_number ? `Room ${member.room_number}` : "Outside Member";

export default function MembersPage() {
  const [members, setMembers] = useState([]);
  const [filter, setFilter] = useState("all");
  const [error, setError] = useState("");
  useEffect(() => { api("/members").then(setMembers).catch((err) => setError(err.message)); }, []);
  const shown = filter === "all" ? members : members.filter((member) => member.member_type === filter);
  return <section className="directory-page content-section">
    <div className="page-banner"><div><span className="eyebrow"><span /> Dining community</span><h1>Meal members</h1><p>Registered members currently participating in the hostel meal cycle.</p></div><Users /></div>
    <div className="filters directory-filters">{[["all", "All"], ["hostel_resident", "Hostel Resident"], ["outside_member", "Outside Member"]].map(([value, text]) => <button key={value} className={filter === value ? "active" : ""} onClick={() => setFilter(value)}>{text}</button>)}</div>
    {error && <div className="form-error">{error}</div>}
    <div className="member-grid">{shown.map((member) => <article className={`member-card ${member.skipped_this_week ? "skipped" : ""}`} key={member.id}><div className="avatar large-avatar">{member.full_name.charAt(0)}</div><div><h3>{member.full_name}</h3><p>{roomLabel(member)} · {label(member.member_type)}</p>{member.address_or_identity_note && <small>{member.address_or_identity_note}</small>}{member.skipped_this_week && <small className="skip-note">Skipped this week</small>}</div>{member.skipped_this_week ? <PauseCircle /> : <BadgeCheck />}</article>)}</div>
  </section>;
}
