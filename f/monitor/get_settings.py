import psycopg
import wmill


def main():
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
                SELECT prompt, topics, updated_at
                FROM monitor_settings
                WHERE id = 1
                """
            )

            row = cursor.fetchone()

            if row is None:
                raise ValueError("Настройки не найдены")

            prompt, topics, updated_at = row

            return {
                "prompt": prompt,
                "topics": topics,
                "updated_at": updated_at.isoformat(),
            }