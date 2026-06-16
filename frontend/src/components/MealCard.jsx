import { BadgeCheck, CalendarDays, MapPin, MessageCircle, Trash2 } from "lucide-react";

function whatsappLink(meal) {
  const message = `Assalamu Alaikum. I want to buy your ${meal.meal_type} meal. Price: ${meal.price} Tk`;
  return `https://wa.me/${meal.seller.whatsapp_number}?text=${encodeURIComponent(message)}`;
}

const roomLabel = (seller) => seller.room_number ? `Room ${seller.room_number}` : "Outside Member";

export default function MealCard({ meal, currentUser, onSold, onDelete }) {
  const isOwner = currentUser?.id === meal.seller.id;
  const formattedDate = new Intl.DateTimeFormat("en-BD", { day: "numeric", month: "short" }).format(new Date(`${meal.date}T00:00:00`));

  return (
    <article className={`meal-card ${meal.status === "sold" ? "sold" : ""}`}>
      <div className="card-topline">
        <span className={`meal-tag ${meal.meal_type.toLowerCase()}`}>{meal.meal_type}</span>
        <span className="meal-date"><CalendarDays size={14} /> {formattedDate}</span>
      </div>
      <div className="price-row"><strong>{Number(meal.price).toLocaleString()}<small> Tk</small></strong><span>{meal.status}</span></div>
      <p className="meal-note">{meal.note || "A fresh hostel meal, ready for exchange."}</p>
      <div className="seller-row">
        <div className="avatar">{meal.seller.full_name.charAt(0)}</div>
        <div><b>{meal.seller.full_name}</b><span><MapPin size={13} /> {roomLabel(meal.seller)}</span></div>
        <BadgeCheck className="verified" size={19} />
      </div>
      {isOwner ? (
        <div className="owner-actions">
          {meal.status !== "sold" && <button onClick={() => onSold(meal.id)}><BadgeCheck size={17} /> Mark sold</button>}
          <button className="danger" onClick={() => onDelete(meal.id)}><Trash2 size={17} /> Delete</button>
        </div>
      ) : meal.status === "available" ? (
        <a className="whatsapp-button" href={whatsappLink(meal)} target="_blank" rel="noreferrer">
          <MessageCircle size={19} /> Message Seller on WhatsApp
        </a>
      ) : <button className="disabled-button" disabled>Meal already sold</button>}
    </article>
  );
}
