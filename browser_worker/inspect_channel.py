import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


PROFILE_DIR = (
    Path(__file__).resolve().parent.parent
    / ".browser-data"
    / "telegram"
)


def main(channel: str):
    channel = channel.removeprefix("@")

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport=None,
            args=["--start-maximized"],
        )

        page = context.pages[0]
        page.goto(f"https://web.telegram.org/k/#@{channel}")
        page.wait_for_timeout(10_000)

        messages = page.locator(".bubble")
        count = messages.count()

        print(f"Найдено сообщений на странице: {count}")

        for index in range(max(0, count - 10), count):
            bubble = messages.nth(index)
            raw_message_id = bubble.get_attribute("data-mid")

            if raw_message_id is None:
                continue

            text_element = bubble.locator(".message")

            if text_element.count() == 0:
                continue

            text = text_element.first.inner_text().strip()

            time_element = bubble.locator(".time")

            if time_element.count() > 0:
                print(
                    time_element.first.evaluate(
                        "element => element.outerHTML"
                    )
                )

            if not text:
                continue

            message_id = int(raw_message_id) % (2**32)
            post_url = f"https://t.me/{channel}/{message_id}"

            print(f"\n--- Пост {message_id} ---")
            print(f"Ссылка: {post_url}")
            print(f"Текст: {text}")

        input("\nНажми Enter, чтобы закрыть браузер: ")
        context.close()


if __name__ == "__main__":
    channel_name = sys.argv[1] if len(sys.argv) > 1 else "durov"
    main(channel_name)