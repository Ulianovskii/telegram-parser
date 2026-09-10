import React from "react";
import type { Page } from "../types";

const items: { id: Page; label: string }[] = [
  { id: "profile", label: "Профиль" },
  { id: "controls", label: "Контроли" },
  { id: "favorites", label: "Избранное" },
];

type Props = { page: Page; onNavigate: (page: Page) => void };

export default function Sidebar({ page, onNavigate }: Props) {
  return (
    <aside className="sidebar">
      <div className="sidebarTitle">Мониторинг Telegram</div>
      <nav className="sidebarNav" aria-label="Главное меню">
        {items.map((item) => (
          <button
            key={item.id}
            className={`navButton ${page === item.id ? "active" : ""}`}
            onClick={() => onNavigate(item.id)}
            aria-current={page === item.id ? "page" : undefined}
          >
            {item.label}
          </button>
        ))}
      </nav>
    </aside>
  );
}
