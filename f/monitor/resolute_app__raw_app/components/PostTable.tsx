import React from "react";

import type { Post } from "../types";

// Props — данные и обработчики, которые App передаёт таблице.
type Props = {
  posts: Post[];
  busy: boolean;
  favoriteIds: number[];
  onToggleFavorite: (id: number) => void;
  emptyText: string;
};

export default function PostTable({
  posts,
  busy,
  favoriteIds,
  onToggleFavorite,
  emptyText,
}: Props) {
  return (
    <div className="tableWrapper">
      <table>
        <thead>
          <tr>
            <th>Дата</th>
            <th>Ссылка</th>
            <th>Текст поста</th>
            <th>Краткий пересказ</th>
            <th>Тематика</th>
            <th>Отправлено в бот</th>
            <th>Избранное</th>
          </tr>
        </thead>

        <tbody>
          {busy && posts.length === 0 && (
            <tr>
              <td colSpan={7} className="empty" role="status">
                Загрузка…
              </td>
            </tr>
          )}
          {posts.map((post) => (
            <tr key={post.id}>
              <td className="date">
                {post.published_at
                  ? new Date(post.published_at).toLocaleString("ru-RU")
                  : "—"}
              </td>

              <td>
                <a href={post.post_url} target="_blank" rel="noreferrer">
                  Открыть пост
                </a>
              </td>

              <td className="postText">{post.post_text}</td>

              <td className="summary">{post.summary || "Ещё не обработан"}</td>

              <td>
                {post.topic ? <span className="topic">{post.topic}</span> : "—"}
              </td>

              <td>
                <span
                  className={
                    post.sent_to_bot ? "status sent" : "status pending"
                  }
                >
                  {post.sent_to_bot ? "Да" : "Нет"}
                </span>
              </td>
              <td>
                <button
                  className="favoriteButton"
                  aria-pressed={favoriteIds.includes(post.id)}
                  onClick={() => onToggleFavorite(post.id)}
                >
                  {favoriteIds.includes(post.id) ? "Убрать" : "В избранное"}
                </button>
              </td>
            </tr>
          ))}

          {!busy && posts.length === 0 && (
            <tr>
              <td colSpan={7} className="empty">
                {emptyText}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
