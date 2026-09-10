import React from "react";
import PostTable from "../components/PostTable";
import type { MonitorModel } from "../hooks/useMonitor";

export default function ControlsPage({ monitor }: { monitor: MonitorModel }) {
  const {
    posts,
    prompt,
    topicsText,
    action,
    error,
    message,
    busy,
    favoriteIds,
    setPrompt,
    setTopicsText,
    toggleFavorite,
    syncPosts,
    processWithGpt,
    sendCatPosts,
    savePrompt,
    saveTopics,
  } = monitor;
  return (
    <>
      <header className="header">
        <div>
          <h1>Контроли</h1>
          <p>Собранные публикации из каналов</p>
        </div>

        <div className="actions">
          <button onClick={syncPosts} disabled={busy}>
            {action === "sync" ? "Собираем..." : "Собрать новые посты"}
          </button>

          <button
            className="gptButton"
            onClick={processWithGpt}
            disabled={busy}
          >
            {action === "gpt" ? "Обработка..." : "Обработать в GPT"}
          </button>
        </div>
      </header>

      <button className="telegramButton" onClick={sendCatPosts} disabled={busy}>
        {action === "telegram"
          ? "Отправка..."
          : "Отправить новости про котиков"}
      </button>

      <section className="settingsPanel">
        <div className="settingsBlock promptBlock">
          <label htmlFor="prompt">Промт обработки</label>

          <textarea
            id="prompt"
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            rows={5}
          />

          <button onClick={savePrompt} disabled={busy}>
            {action === "prompt" ? "Сохранение..." : "Сохранить промт"}
          </button>
        </div>

        <div className="settingsBlock topicsBlock">
          <label htmlFor="topics">Тематики — по одной на строку</label>

          <textarea
            id="topics"
            value={topicsText}
            onChange={(event) => setTopicsText(event.target.value)}
            rows={5}
          />

          <button onClick={saveTopics} disabled={busy}>
            {action === "topics" ? "Сохранение..." : "Сохранить тематики"}
          </button>
        </div>
      </section>

      {error && <div className="error">{error}</div>}
      {message && <div className="message">{message}</div>}

      <PostTable
        posts={posts}
        busy={busy}
        favoriteIds={favoriteIds}
        onToggleFavorite={toggleFavorite}
        emptyText="Постов пока нет"
      />
    </>
  );
}
