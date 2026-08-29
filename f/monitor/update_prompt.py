import psycopg
import wmill


def main(prompt: str):
    prompt = prompt.strip()

    if not prompt:
        raise ValueError("Промт не может быть пустым")

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
                    prompt = %s,
                    updated_at = now()
                WHERE id = 1
                RETURNING updated_at
                """,
                (prompt,),
            )

            updated_at = cursor.fetchone()[0]

    return {
        "prompt": prompt,
        "updated_at": updated_at.isoformat(),
    }