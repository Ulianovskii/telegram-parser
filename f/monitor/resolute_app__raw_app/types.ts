export type Post = {
  id: number;
  post_url: string;
  post_text: string;
  summary: string | null;
  topic: string | null;
  sent_to_bot: boolean;
  ai_processed_at: string | null;
  published_at: string | null;
};

export type Action =
  "load" | "sync" | "gpt" | "telegram" | "prompt" | "topics" | null;

export type Page = "profile" | "controls" | "favorites";
