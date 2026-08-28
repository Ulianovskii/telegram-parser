import psycopg
import requests
import wmill


def main(
    channel: str = "andrew_parser_test",
    browser_worker_url: str = "http://host.docker.internal:3001",
):
    database = wmill.get_resource("f/monitor/postgres")

    response = requests.get(
        f"{browser_worker_url}/telegram/{channel}/posts",
        timeout=60,
    )
    response.raise_for_status()

    posts = response.json()["posts"]
    processed = 0

    with psycopg.connect(
        host=database["host"],
        port=database.get("port", 5432),
        dbname=database["dbname"],
        user=database["user"],
        password=database["password"],
        sslmode=database.get("sslmode", "disable"),
    ) as connection:
        with connection.cursor() as cursor:
            for post in posts:
                cursor.execute(
                    """
                    INSERT INTO posts (
                        channel_id,
                        channel_username,
                        message_id,
                        post_url,
                        post_text,
                        published_at
                    )
                    VALUES (
                        NULL,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    ON CONFLICT (
                        channel_username,
                        message_id
                    )
                    DO UPDATE SET
                        post_url = EXCLUDED.post_url,
                        post_text = EXCLUDED.post_text,
                        published_at = EXCLUDED.published_at
                    """,
                    (
                        post["channel_username"],
                        post["message_id"],
                        post["post_url"],
                        post["post_text"],
                        post["published_at"],
                    ),
                )

                processed += 1

    return {
        "channel": channel,
        "fetched": len(posts),
        "processed": processed,
    }