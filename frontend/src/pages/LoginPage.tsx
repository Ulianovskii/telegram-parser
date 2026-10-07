export function LoginPage() {
  return (
    <main>
      <h1>Вход</h1>

      <form>
        <label>
          Логин
          <input name="username" autoComplete="username" />
        </label>

        <label>
          Пароль
          <input
            name="password"
            type="password"
            autoComplete="current-password"
          />
        </label>

        <button type="submit">Войти</button>
      </form>
    </main>
  )
}