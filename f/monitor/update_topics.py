import psycopg
import wmill


def main(topics: list[str]):
    clean_topics = []

    for topic in topics:
        topic = topic.strip().lower()

        if topic and topic not in clean_topics:
            clean_topics.append(topic)

    if not clean_topics:
        raise ValueError("Нужно указать хотя бы одну тематику")

    database = wmill.get_resource("f/monitor/postgres")

    with psycopg.connect(
        host=database["host"],
        port=database.get("port", 5432),
        dbname=database["dbname"],
        user=database["user"],
        password=database["password"],
        sslmode=database.get("sslmode", "disable"),
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE monitor_settings
                SET
                    topics = %s,
                    updated_at = now()
                WHERE id = 1
                RETURNING updated_at
                """,
                (clean_topics,),
            )

            updated_at = cursor.fetchone()[0]

    return {
        "topics": clean_topics,
        "updated_at": updated_at.isoformat(),
    }