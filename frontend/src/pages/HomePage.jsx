import { ArrowRight, BellRing, MessageCircle, Moon, Search, ShieldCheck, Soup, Sun } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import heroImage from "../assets/hostel-meal-hero.png";
import { api } from "../api/client";
import MealCard from "../components/MealCard";

function localDateValue() {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}

export default function HomePage({ user }) {
  const [meals, setMeals] = useState([]);
  const [menu, setMenu] = useState(null);
  const [cycle, setCycle] = useState(null);
  const [filter, setFilter] = useState("All");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const [mealData, allMeals, menuData, cycleData] = await Promise.all([api("/meals/today"), user ? api("/meals") : Promise.resolve([]), api("/menu/today"), api("/cycle")]);
      const today = localDateValue();
      const ownTodayMeals = allMeals.filter((meal) => meal.seller.id === user?.id && meal.date === today);
      const merged = [...mealData, ...ownTodayMeals].filter((meal, index, array) => array.findIndex((item) => item.id === meal.id) === index);
      setMeals(merged);
      setMenu(menuData);
      setCycle(cycleData);
      setError("");
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [user?.id]);
  const shown = useMemo(() => filter === "All" ? meals : meals.filter((meal) => meal.meal_type === filter), [meals, filter]);
  const count = (type) => meals.filter((meal) => meal.meal_type === type).length;

  const markSold = async (id) => { await api(`/meals/${id}/mark-sold`, { method: "PATCH" }); load(); };
  const remove = async (id) => { if (window.confirm("Delete this meal post?")) { await api(`/meals/${id}`, { method: "DELETE" }); load(); } };

  return (
    <>
      <section className="hero">
        <img src={heroImage} alt="Students exchanging hostel meals" />
        <div className="hero-overlay" />
        <div className="hero-content">
          <span className="eyebrow"><span /> Made for UFTB Boys Hostel</span>
          <h1>Good food<br /><em>shouldn't go to waste.</em></h1>
          <p>Pass on a meal you can't eat. Find one when you need it. Simple, fast, and within the hostel.</p>
          <div className="hero-actions">
            <a href="#market" className="primary-button"><Search size={18} /> Find today's meal</a>
            <Link to={user?.is_meal_member ? "/sell" : user ? "/members" : "/register"} className="text-link">{user?.is_meal_member ? "Sell a meal" : "Join meal members"} <ArrowRight size={17} /></Link>
          </div>
          <div className="hero-stats">
            <div><b>{meals.length}</b><span>meals available</span></div>
            <div><b>{count("Lunch")}</b><span>lunch offers</span></div>
            <div><b>{count("Dinner")}</b><span>dinner offers</span></div>
          </div>
        </div>
      </section>

      <section className="content-section menu-section">
        {cycle?.manager && <div className="manager-spotlight"><div className="avatar">{cycle.manager.full_name.charAt(0)}</div><div><span className="kicker">Current meal manager</span><b>{cycle.manager.full_name}</b><small>{cycle.manager.room_number ? `Room ${cycle.manager.room_number}` : "Outside Member"} · Cycle ends {new Intl.DateTimeFormat("en-BD", { day: "numeric", month: "short" }).format(new Date(`${cycle.end_date}T00:00:00`))}</small></div><a href={`https://wa.me/${cycle.manager.whatsapp_number}`} target="_blank" rel="noreferrer"><MessageCircle /> WhatsApp</a><ShieldCheck /></div>}
        {menu?.notice && <div className="notice"><BellRing size={19} /><b>Hostel notice</b><span>{menu.notice}</span></div>}
        <div className="section-heading">
          <div><span className="kicker">On the menu</span><h2>Today at the dining hall</h2></div>
          <span className="today-label">{new Intl.DateTimeFormat("en-BD", { weekday: "long", day: "numeric", month: "long" }).format(new Date())}</span>
        </div>
        <div className="menu-grid">
          <article className="menu-panel lunch-panel"><Sun /><div><span>Today's lunch</span><h3>{menu?.lunch_menu || "Loading today's menu..."}</h3></div><b>12:30<br />PM</b></article>
          <article className="menu-panel dinner-panel"><Moon /><div><span>Today's dinner</span><h3>{menu?.dinner_menu || "Loading today's menu..."}</h3></div><b>8:00<br />PM</b></article>
        </div>
      </section>

      <section className="content-section market-section" id="market">
        <div className="section-heading market-heading">
          <div><span className="kicker">Meal board</span><h2>Available today</h2><p>Contact a hostel mate directly. No platform fees, no fuss.</p></div>
          <div className="filters">{["All", "Lunch", "Dinner"].map((item) => <button key={item} className={filter === item ? "active" : ""} onClick={() => setFilter(item)}>{item}{item !== "All" && <span>{count(item)}</span>}</button>)}</div>
        </div>
        {error && <div className="form-error">{error}</div>}
        {loading ? <div className="empty-state">Checking today's meal board...</div> : shown.length ? (
          <div className="meal-grid">{shown.map((meal) => <MealCard key={meal.id} meal={meal} currentUser={user} onSold={markSold} onDelete={remove} />)}</div>
        ) : (
          <div className="empty-state"><SoupIcon /><h3>No {filter === "All" ? "" : filter.toLowerCase()} meals posted yet</h3><p>Be the first to offer one to your hostel mates.</p>{user?.is_meal_member && <Link to="/sell" className="primary-button">Post a meal</Link>}</div>
        )}
      </section>
    </>
  );
}

function SoupIcon() { return <div className="empty-icon"><Soup /></div>; }
