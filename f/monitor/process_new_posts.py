import json

import psycopg
import requests
import wmill


MODEL = "gpt-5-nano"


def main(limit: int = 20):
    database = wmill.get_resource("f/monitor/postgres")
    openai = wmill.get_resource("f/monitor/openai")

    api_key = openai.get("api_key") or openai.get("token")

    if not api_key:
        raise ValueError(
            "В ресурсе f/monitor/openai не найдено поле api_key"
        )

    processed = []
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
                SELECT prompt, topics
                FROM monitor_settings
                WHERE id = 1
                """
            )

            settings = cursor.fetchone()

            if settings is None:
                raise ValueError("Настройки monitor_settings не найдены")

            prompt, topics = settings

            cursor.execute(
                """
                SELECT id, post_text
                FROM posts
                WHERE ai_processed_at IS NULL
                ORDER BY published_at ASC NULLS LAST, id ASC
                LIMIT %s
                """,
                (limit,),
            )

            posts = cursor.fetchall()

            for post_id, post_text in posts:
                try:
                    response = requests.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": MODEL,
                            "messages": [
                                {
                                    "role": "system",
                                    "content": (
                                        f"{prompt}\n\n"
                                        "Допустимые тематики: "
                                        + ", ".join(topics)
                                    ),
                                },
                                {
                                    "role": "user",
                                    "content": post_text,
                                },
                            ],
                            "response_format": {
                                "type": "json_schema",
                                "json_schema": {
                                    "name": "post_analysis",
                                    "strict": True,
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "summary": {
                                                "type": "string"
                                            },
                                            "topic": {
                                                "type": "string",
                                                "enum": topics,
                                            },
                                        },
                                        "required": [
                                            "summary",
                                            "topic",
                                        ],
                                        "additionalProperties": False,
                                    },
                                },
                            },
                        },
                        timeout=60,
                    )

                    response.raise_for_status()

                    content = response.json()["choices"][0]["message"][
                        "content"
                    ]
                    result = json.loads(content)

                    cursor.execute(
                        """
                        UPDATE posts
                        SET
                            summary = %s,
                            topic = %s,
                            ai_processed_at = now()
                        WHERE id = %s
                          AND ai_processed_at IS NULL
                        """,
                        (
                            result["summary"],
                            result["topic"],
                            post_id,
                        ),
                    )

                    processed.append(
                        {
                            "id": post_id,
                            "topic": result["topic"],
                            "summary": result["summary"],
                        }
                    )

                except Exception as error:
                    errors.append(
                        {
                            "id": post_id,
                            "error": str(error),
                        }
                    )

    return {
        "model": MODEL,
        "found": len(posts),
        "processed": len(processed),
        "failed": len(errors),
        "results": processed,
        "errors": errors,
    }