from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from playwright.sync_api import sync_playwright


app = FastAPI(title="Browser Worker")

PROFILE_DIR = (
    Path(__file__).resolve().parent.parent
    / ".browser-data"
    / "telegram"
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/telegram/{channel}/posts")
def read_channel(channel: str):
    channel = channel.removeprefix("@")
    posts = []

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=True,
            timezone_id="Europe/Moscow",
        )

        page = context.pages[0]
        page.goto(f"https://web.telegram.org/k/#@{channel}")
        page.wait_for_timeout(10_000)

        messages = page.locator(".bubble")
        count = messages.count()

        for index in range(count):
            bubble = messages.nth(index)
            raw_message_id = bubble.get_attribute("data-mid")

            if raw_message_id is None:
                continue

            text = bubble.evaluate(
                """
                bubble => {
                    const message = bubble.querySelector(".message");

                    if (!message) {
                        return "";
                    }

                    const clone = message.cloneNode(true);

                    clone.querySelectorAll(
                        ".time, .views, .reactions, .bubble-info"
                    ).forEach(element => element.remove());

                    return clone.innerText.trim();
                }
                """
            )

            if not text:
                continue

            time_element = bubble.locator(".time-inner")
            published_at = None

            if time_element.count() > 0:
                title = time_element.first.get_attribute("title")

                if title:
                    date_text = title.splitlines()[0]

                    published_at = (
                        datetime.strptime(
                            date_text,
                            "%d %B %Y, %H:%M:%S",
                        )
                        .replace(tzinfo=ZoneInfo("Europe/Moscow"))
                        .isoformat()
                    )

            message_id = int(raw_message_id) % (2**32)

            posts.append(
                {
                    "channel_username": channel,
                    "message_id": message_id,
                    "post_url": f"https://t.me/{channel}/{message_id}",
                    "post_text": text,
                    "published_at": published_at,
                }
            )

        context.close()

    return {
        "channel": channel,
        "count": len(posts),
        "posts": posts,
    }