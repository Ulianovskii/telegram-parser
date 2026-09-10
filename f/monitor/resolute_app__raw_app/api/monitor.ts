import { backend } from "../wmill";

// Только этот модуль знает имена backend.a … backend.g из Windmill.
export const listPosts = () => backend.a({});
export const getSettings = () => backend.d({});

export const syncChannel = () =>
  backend.b({
    channel: "andrew_parser_test",
    browser_worker_url: "http://host.docker.internal:3001",
  });

export const processPosts = () =>
  backend.c({
    limit: 20,
  });

export const sendCatPosts = () =>
  backend.g({
    chat_id: 103181087,
    topic: "котики",
    limit: 20,
  });

export const updatePrompt = (prompt: string) => backend.e({ prompt });
export const updateTopics = (topics: string[]) => backend.f({ topics });
