import psycopg
import requests
import wmill


def main(
    chat_id: int = 103181087,
    topic: str = "котики",
    limit: int = 20,
):
    database = wmill.get_resource("f/monitor/postgres")
    telegram = wmill.get_resource(
        "f/monitor/cat_observer_bot"
    )

    sent = []
    errors = []

    with psycopg.connect(
        host=database["host"],
        port=database.get("port", 5432),
        dbname=database["dbname"],
        user=database["user"],
        password=database["password"],
        sslmode=database.get("sslmode", "disable"),
        autocommit=True,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, summary, post_url
                FROM posts
                WHERE topic = %s
                  AND summary IS NOT NULL
                  AND sent_to_bot = false
                ORDER BY published_at ASC NULLS LAST, id ASC
                LIMIT %s
                """,
                (topic, limit),
            )

            posts = cursor.fetchall()

            for post_id, summary, post_url in posts:
                try:
                    text = (
                        f"Тема: {topic}\n\n"
                        f"{summary[:3500]}\n\n"
                        f"{post_url}"
                    )

                    response = requests.post(
                        (
                            "https://api.telegram.org/"
                            f"bot{telegram['token']}/sendMessage"
                        ),
                        json={
                            "chat_id": chat_id,
                            "text": text,
                            "disable_web_page_preview": False,
                        },
                        timeout=30,
                    )

                    response.raise_for_status()

                    result = response.json()

                    if not result.get("ok"):
                        raise RuntimeError(
                            result.get(
                                "description",
                                "Telegram вернул ошибку",
                            )
                        )

                    cursor.execute(
                        """
                        UPDATE posts
                        SET sent_to_bot = true
                        WHERE id = %s
                          AND sent_to_bot = false
                        """,
                        (post_id,),
                    )

                    sent.append(post_id)

                except Exception as error:
                    errors.append(
                        {
                            "id": post_id,
                            "error": str(error),
                        }
                    )

    return {
        "topic": topic,
        "found": len(posts),
        "sent": len(sent),
        "failed": len(errors),
        "sent_post_ids": sent,
        "errors": errors,
    }