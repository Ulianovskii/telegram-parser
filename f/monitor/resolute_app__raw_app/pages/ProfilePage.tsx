import React from "react";

export default function ProfilePage() {
  return (
    <>
      <header className="header">
        <div>
          <h1>Профиль</h1>
          <p>Подписка и отслеживаемые каналы</p>
        </div>
      </header>
      <section className="settingsBlock profilePlaceholder">
        <h2>Настройки профиля</h2>
        <p>Тариф и управление каналами пока не подключены.</p>
      </section>
    </>
  );
}
