import React from "react";

type Props = { onLogin: () => void };

export default function LoginPage({ onLogin }: Props) {
  return (
    <main>
      <h1>Вход в приложение</h1>
      <p>При первом входе аккаунт создаётся автоматически.</p>
      <button type="button" onClick={onLogin}>
        Войти через Telegram
      </button>
    </main>
  );
}
