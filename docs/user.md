# Модель User

## Основная информация
- **Таблица:** `users`
- **Назначение:** Основная таблица пользователей системы
- **Роли:** participant, organizer, mentor, volunteer

## 🗃️ Структура таблицы
| Поле | Тип | Nullable | Default | Описание |
|------|-----|----------|---------|----------|
| id | INTEGER | ❌ | auto | Первичный ключ |
| telegram_id | BIGINT | ❌ | - | Уникальный ID Telegram |
| username | VARCHAR(100) | ✅ | NULL | Username в Telegram |
| full_name | VARCHAR(200) | ❌ | - | Полное имя |
| role | ENUM | ❌ | - | Роль пользователя |
| timezone | VARCHAR(50) | ✅ | UTC+3 | Часовой пояс |
| is_active | BOOLEAN | ✅ | true | Активен ли |
| participant_status | ENUM | ✅ | NULL | Статус участника |
| profile_text | TEXT | ✅ | NULL | Текст анкеты |
| profile_active | BOOLEAN | ✅ | false | Активна ли анкета |
| team_id | INTEGER | ✅ | NULL | FK → teams.id |

## Связи
```python
# SQLAlchemy relationships
created_events = relationship("Event", back_populates="creator")
team = relationship("Team", back_populates="members")
captained_teams = relationship("Team", foreign_keys="[Team.captain_id]")
mentored_teams = relationship("Team", foreign_keys="[Team.mentor_id]")
event_notifications = relationship("EventNotification", back_populates="user")