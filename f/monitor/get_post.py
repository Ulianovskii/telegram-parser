import requests
from datetime import datetime, timezone


def main(name: str = "Андрей", post_id: int = 1):
    print(f"Запрашиваем публикацию №{post_id} для пользователя {name}")

    response = requests.get(
        f"https://jsonplaceholder.typicode.com/posts/{post_id}",
        timeout=10,
    )
    response.raise_for_status()

    post = response.json()

    return {
        "requested_by": name,
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "post": {
            "id": post["id"],
            "title": post["title"],
            "text": post["body"],
        },
    }