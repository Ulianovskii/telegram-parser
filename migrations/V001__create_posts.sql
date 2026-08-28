CREATE TABLE posts (
    id BIGSERIAL PRIMARY KEY,
    channel_id BIGINT NOT NULL,
    channel_username TEXT,
    message_id BIGINT NOT NULL,
    post_url TEXT NOT NULL,
    post_text TEXT NOT NULL,
    published_at TIMESTAMPTZ,
    summary TEXT,
    topics TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (channel_id, message_id)
);

CREATE INDEX idx_posts_published_at
    ON posts (published_at DESC);