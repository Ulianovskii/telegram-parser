SELECT
    id,
    post_url,
    post_text,
    summary,
    topics,
    published_at
FROM posts
ORDER BY published_at DESC NULLS LAST, id DESC;