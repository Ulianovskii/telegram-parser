import { useEffect, useState } from "react";
import * as monitorApi from "../api/monitor";
import type { Action, Post } from "../types";

// Общая логика приложения. Вызывается один раз в App, а не отдельно на страницах.
export function useMonitor() {
  // Временное избранное: хранится в памяти этой вкладки.
  const [favoriteIds, setFavoriteIds] = useState<number[]>([]);

  function toggleFavorite(id: number) {
    setFavoriteIds((current) =>
      current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id],
    );
  }

  const [posts, setPosts] = useState<Post[]>([]);
  const [prompt, setPrompt] = useState("");
  const [topicsText, setTopicsText] = useState("");
  const [action, setAction] = useState<Action>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  // Запросы к backend Windmill и обновление состояния приложения.
  async function fetchPosts() {
    const result = await monitorApi.listPosts();
    setPosts(Array.isArray(result) ? result : []);
  }

  async function fetchSettings() {
    const result = await monitorApi.getSettings();

    setPrompt(result.prompt ?? "");
    setTopicsText(Array.isArray(result.topics) ? result.topics.join("\n") : "");
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
      const result = await monitorApi.syncChannel();

      await fetchPosts();

      setMessage(`Сбор завершён. Получено публикаций: ${result.fetched ?? 0}`);
    } catch (err) {
      console.error(err);
      setError("Не удалось собрать посты. Проверь Browser Worker.");
    } finally {
      setAction(null);
    }
  }

  async function processWithGpt() {
    setAction("gpt");
    setError("");
    setMessage("");

    try {
      const result = await monitorApi.processPosts();

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
      const result = await monitorApi.sendCatPosts();

      await fetchPosts();

      if (result.sent === 0) {
        setMessage("Новых новостей про котиков для отправки нет");
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
      await monitorApi.updatePrompt(prompt.trim());

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
      const result = await monitorApi.updateTopics(topics);

      setTopicsText(result.topics.join("\n"));
      setMessage("Тематики сохранены");
    } catch (err) {
      console.error(err);
      setError("Не удалось сохранить тематики");
    } finally {
      setAction(null);
    }
  }

  // Первичная загрузка после появления компонента на экране.
  useEffect(() => {
    loadData();
  }, []);

  const busy = action !== null;

  return {
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
  };
}

export type MonitorModel = ReturnType<typeof useMonitor>;
