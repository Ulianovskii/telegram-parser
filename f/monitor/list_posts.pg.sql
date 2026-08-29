SELECT
    id,
    post_url,
    post_text,
    summary,
    topic,
    sent_to_bot,
    ai_processed_at,
    published_at
FROM posts
ORDER BY published_at DESC NULLS LAST, id DESC;