from pathlib import Path

from playwright.sync_api import sync_playwright


PROFILE_DIR = (
    Path(__file__).resolve().parent.parent
    / ".browser-data"
    / "telegram"
)


def main():
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport=None,
            args=["--start-maximized"],
        )

        page = context.pages[0]
        page.goto("https://web.telegram.org/k/")

        input(
            "Войди в Telegram, дождись появления списка чатов "
            "и нажми Enter здесь: "
        )

        context.close()


if __name__ == "__main__":
    main()