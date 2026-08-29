import React, { useEffect, useState } from "react";
import { backend } from "./wmill";
import "./index.css";

type Post = {
  id: number;
  post_url: string;
  post_text: string;
  summary: string | null;
  topic: string | null;
  sent_to_bot: boolean;
  ai_processed_at: string | null;
  published_at: string | null;
};

type Action =
  | "load"
  | "sync"
  | "gpt"
  | "telegram"
  | "prompt"
  | "topics"
  | null;

export default function App() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [prompt, setPrompt] = useState("");
  const [topicsText, setTopicsText] = useState("");
  const [action, setAction] = useState<Action>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function fetchPosts() {
    const result = await backend.a({});
    setPosts(Array.isArray(result) ? result : []);
  }

  async function fetchSettings() {
    const result = await backend.d({});

    setPrompt(result.prompt ?? "");
    setTopicsText(
      Array.isArray(result.topics)
        ? result.topics.join("\n")
        : "",
    );
  }

  async function loadData() {
    setAction("load");
    setError("");

    try {
      await Promise.all([fetchPosts(), fetchSettings()]);
    } catch (err) {
      console.error(err);
      setError("Не удалось загрузить данные");
    } finally {
      setAction(null);
    }
  }

  async function syncPosts() {
    setAction("sync");
    setError("");
    setMessage("");

    try {
      const result = await backend.b({
        channel: "andrew_parser_test",
        browser_worker_url: "http://host.docker.internal:3001",
      });

      await fetchPosts();

      setMessage(
        `Сбор завершён. Получено публикаций: ${result.fetched ?? 0}`,
      );
    } catch (err) {
      console.error(err);
      setError(
        "Не удалось собрать посты. Проверь Browser Worker.",
      );
    } finally {
      setAction(null);
    }
  }

  async function processWithGpt() {
    setAction("gpt");
    setError("");
    setMessage("");

    try {
      const result = await backend.c({
        limit: 20,
      });

      await fetchPosts();

      if (result.processed === 0) {
        setMessage("Новых постов для обработки нет");
      } else {
        setMessage(
          `GPT обработал публикаций: ${result.processed}. Ошибок: ${result.failed}`,
        );
      }
    } catch (err) {
      console.error(err);
      setError("Не удалось обработать посты через GPT");
    } finally {
      setAction(null);
    }
  }

  async function sendCatPosts() {
  setAction("telegram");
  setError("");
  setMessage("");

  try {
    const result = await backend.g({
      chat_id: 103181087,
      topic: "котики",
      limit: 20,
    });

    await fetchPosts();

    if (result.sent === 0) {
      setMessage(
        "Новых новостей про котиков для отправки нет",
      );
    } else {
      setMessage(
        `Отправлено в Telegram: ${result.sent}. Ошибок: ${result.failed}`,
      );
    }
  } catch (err) {
    console.error(err);
    setError("Не удалось отправить новости в Telegram");
  } finally {
    setAction(null);
  }
}

  async function savePrompt() {
    if (!prompt.trim()) {
      setError("Промт не может быть пустым");
      return;
    }

    setAction("prompt");
    setError("");
    setMessage("");

    try {
      await backend.e({
        prompt: prompt.trim(),
      });

      setMessage("Промт сохранён");
    } catch (err) {
      console.error(err);
      setError("Не удалось сохранить промт");
    } finally {
      setAction(null);
    }
  }

  async function saveTopics() {
    const topics = topicsText
      .split(/[\n,]+/)
      .map((topic) => topic.trim())
      .filter(Boolean);

    if (topics.length === 0) {
      setError("Нужно указать хотя бы одну тематику");
      return;
    }

    setAction("topics");
    setError("");
    setMessage("");

    try {
      const result = await backend.f({
        topics,
      });

      setTopicsText(result.topics.join("\n"));
      setMessage("Тематики сохранены");
    } catch (err) {
      console.error(err);
      setError("Не удалось сохранить тематики");
    } finally {
      setAction(null);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  const busy = action !== null;

  return (
    <main className="page">
      <header className="header">
        <div>
          <h1>Мониторинг Telegram</h1>
          <p>Собранные публикации из каналов</p>
        </div>

        <div className="actions">
          <button onClick={syncPosts} disabled={busy}>
            {action === "sync"
              ? "Собираем..."
              : "Собрать новые посты"}
          </button>

          <button
            className="gptButton"
            onClick={processWithGpt}
            disabled={busy}
          >
            {action === "gpt"
              ? "Обработка..."
              : "Обработать в GPT"}
          </button>
        </div>
      </header>

      <button
  className="telegramButton"
  onClick={sendCatPosts}
  disabled={busy}
>
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
            {action === "prompt"
              ? "Сохранение..."
              : "Сохранить промт"}
          </button>
        </div>

        <div className="settingsBlock topicsBlock">
          <label htmlFor="topics">
            Тематики — по одной на строку
          </label>

          <textarea
            id="topics"
            value={topicsText}
            onChange={(event) =>
              setTopicsText(event.target.value)
            }
            rows={5}
          />

          <button onClick={saveTopics} disabled={busy}>
            {action === "topics"
              ? "Сохранение..."
              : "Сохранить тематики"}
          </button>
        </div>
      </section>

      {error && <div className="error">{error}</div>}
      {message && <div className="message">{message}</div>}

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
            </tr>
          </thead>

          <tbody>
            {posts.map((post) => (
              <tr key={post.id}>
                <td className="date">
                  {post.published_at
                    ? new Date(post.published_at).toLocaleString(
                        "ru-RU",
                      )
                    : "—"}
                </td>

                <td>
                  <a
                    href={post.post_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Открыть пост
                  </a>
                </td>

                <td className="postText">{post.post_text}</td>

                <td className="summary">
                  {post.summary || "Ещё не обработан"}
                </td>

                <td>
                  {post.topic ? (
                    <span className="topic">{post.topic}</span>
                  ) : (
                    "—"
                  )}
                </td>

                <td>
                  <span
                    className={
                      post.sent_to_bot
                        ? "status sent"
                        : "status pending"
                    }
                  >
                    {post.sent_to_bot ? "Да" : "Нет"}
                  </span>
                </td>
              </tr>
            ))}

            {!busy && posts.length === 0 && (
              <tr>
                <td colSpan={6} className="empty">
                  Постов пока нет
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}