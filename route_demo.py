from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
import secrets

app = FastAPI()


# Отдаёт страницу с полем ввода и кнопкой.
@app.get("/")
async def page():
    return HTMLResponse("""
        <h1>Учебная страница</h1>

        <input id="name" placeholder="Введите имя">
        <button onclick="loadMessage()">Отправить</button>

        <p id="result">Здесь появится ответ</p>

        <script>
            // Берёт имя из поля, передаёт его серверу и показывает ответ.
            async function loadMessage() {
                const name = document.getElementById("name").value;

                const response = await fetch(
                    "/api/message?name=" + encodeURIComponent(name)
                );

                const data = await response.json();

                document.getElementById("result").textContent = data.message+ ". Ваш visitor_id: " + data.visitor_id_from_cookie;
            }
        </script>
    """)


@app.get("/api/message")
async def get_message(
    name: str,
    request: Request,
    response: Response,
):
    visitor_id = request.cookies.get("visitor_id")

    if visitor_id is None:
        visitor_id = secrets.token_hex(4)

        response.set_cookie(
            key="visitor_id",
            value=visitor_id,
            max_age=86400,
        )

    return {
        "message": "Привет, " + name,
        "visitor_id_from_cookie": visitor_id,
    }