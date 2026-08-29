ALTER TABLE posts
    ADD COLUMN topic text,
    ADD COLUMN sent_to_bot boolean NOT NULL DEFAULT false,
    ADD COLUMN ai_processed_at timestamp with time zone;

CREATE TABLE monitor_settings (
    id smallint PRIMARY KEY CHECK (id = 1),
    prompt text NOT NULL,
    topics text[] NOT NULL,
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

INSERT INTO monitor_settings (
    id,
    prompt,
    topics
)
VALUES (
    1,
    'Сделай короткий пересказ поста и определи одну тематику из предложенного списка.',
    ARRAY['котики', 'собаки', 'животные', 'прочие новости']
);