# Модели событий (Event, EventLog, EventNotification)

## Event - основная таблица событий
**Таблица:** `events`

### Структура
| Поле | Тип | Nullable | Default | Описание |
|------|-----|----------|---------|----------|
| id | INTEGER | ❌ | auto | Первичный ключ |
| title | VARCHAR(200) | ❌ | - | Название |
| description | TEXT | ✅ | NULL | Описание |
| start_time | TIMESTAMP | ❌ | - | Время начала |
| end_time | TIMESTAMP | ❌ | - | Время окончания |
| location | VARCHAR(200) | ✅ | NULL | Место |
| visibility | JSONB | ❌ | [] | Роли для просмотра |
| created_by | INTEGER | ✅ | NULL | FK → users.id |
| creator_timezone | VARCHAR(10) | ✅ | UTC+3 | ЧП создателя |
| is_active | BOOLEAN | ✅ | true | Активно |
| updated_at | TIMESTAMP | ✅ | now() | Время обновления |

## 📋 EventLog - логи изменений
**Таблица:** `event_logs`

### Структура
| Поле | Тип | Nullable | Default | Описание |
|------|-----|----------|---------|----------|
| id | INTEGER | ❌ | auto | Первичный ключ |
| event_id | INTEGER | ❌ | - | FK → events.id |
| changed_by | INTEGER | ✅ | NULL | FK → users.id |
| change_type | ENUM | ❌ | - | Тип изменения |
| changes | JSONB | ✅ | NULL | Детали изменений |
| changed_at | TIMESTAMP | ✅ | now() | Время изменения |

## 📋 EventNotification - уведомления
**Таблица:** `event_notifications`

### Структура
| Поле | Тип | Nullable | Default | Описание |
|------|-----|----------|---------|----------|
| id | INTEGER | ❌ | auto | Первичный ключ |
| user_id | INTEGER | ❌ | - | FK → users.id |
| event_id | INTEGER | ❌ | - | FK → events.id |
| notification_type | VARCHAR(20) | ❌ | - | Тип уведомления |
| sent_at | TIMESTAMP | ✅ | now() | Время отправки |
| read_at | TIMESTAMP | ✅ | NULL | Время прочтения |

## 🔗 Связи
```python
# Event
creator = relationship("User", back_populates="created_events")
logs = relationship("EventLog", back_populates="event")
notifications = relationship("EventNotification", back_populates="event")

# EventLog
event = relationship("Event", back_populates="logs")
user = relationship("User")

# EventNotification
user = relationship("User", back_populates="event_notifications")
event = relationship("Event", back_populates="notifications")


# Бизнес-правила: Планирование событий

## Видимость событий
1. Уровни доступа:
   - `all` - видно всем пользователям
   - `participant` - только участникам хакатона
   - `organizer` - только организаторам
   - `mentor` - только менторам
   - `volunteer` - только волонтёрам

## 🔔 Уведомления
1. **Типы уведомлений:**
   - Создание нового события
   - Изменение существующего
   - Отмена события
   - Напоминания (за 10, 15, 30 минут)

2. Настройки пользователя:
   - Отключение по типам
   - Настройка времени напоминаний