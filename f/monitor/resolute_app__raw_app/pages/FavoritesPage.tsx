import React from "react";
import PostTable from "../components/PostTable";
import type { MonitorModel } from "../hooks/useMonitor";

export default function FavoritesPage({ monitor }: { monitor: MonitorModel }) {
  const { posts, favoriteIds, busy, error, toggleFavorite } = monitor;
  return (
    <>
      <header className="header">
        <div>
          <h1>Избранное</h1>
          <p>Отмеченные публикации. Выбор сбросится при обновлении вкладки.</p>
        </div>
      </header>
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      <PostTable
        posts={posts.filter((post) => favoriteIds.includes(post.id))}
        busy={busy}
        favoriteIds={favoriteIds}
        onToggleFavorite={toggleFavorite}
        emptyText="В избранном пока нет публикаций. Добавьте их в разделе «Контроли»."
      />
    </>
  );
}
