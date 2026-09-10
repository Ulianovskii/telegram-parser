import React, { useState } from "react";
import Sidebar from "./components/Sidebar";
import ProfilePage from "./f/monitor/resolute_app__raw_app/pages/ProfilePage";
import ControlsPage from "./f/monitor/resolute_app__raw_app/pages/ControlsPage";
import FavoritesPage from "./f/monitor/resolute_app__raw_app/pages/FavoritesPage";
import { useMonitor } from "./hooks/useMonitor";
import type { Page } from "./f/monitor/resolute_app__raw_app/types";
import "./index.css";

export default function App() {
  const [page, setPage] = useState<Page>("controls");
  // Общие данные сохраняются при переключении страниц.
  const monitor = useMonitor();

  return (
    <div className="appLayout">
      <Sidebar page={page} onNavigate={setPage} />
      <main className="page">
        {page === "profile" && <ProfilePage />}
        {page === "controls" && <ControlsPage monitor={monitor} />}
        {page === "favorites" && <FavoritesPage monitor={monitor} />}
      </main>
    </div>
  );
}
