ALTER TABLE posts
    ALTER COLUMN channel_id DROP NOT NULL;

CREATE UNIQUE INDEX idx_posts_channel_username_message_id
    ON posts (channel_username, message_id);