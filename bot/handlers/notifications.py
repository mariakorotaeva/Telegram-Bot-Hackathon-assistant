import asyncio
from datetime import datetime
from typing import List, Optional
from aiogram import Bot, Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from services.user_service import UserService
from services.notification_service import NotificationService, NotificationType

router = Router()

class NotificationStates(StatesGroup):
    editing_reminders = State()
    editing_types = State()

user_service = UserService()
notification_service = NotificationService()


def get_notification_settings_keyboard(user_id: int, settings_enabled: bool):
    """Создаёт клавиатуру для управления уведомлениями."""
    builder = InlineKeyboardBuilder()
    
    enabled_status = "🔕 Выключить" if settings_enabled else "🔔 Включить"

    builder.button(text=enabled_status, callback_data="toggle_notifications")
    builder.button(text="⏰ Время напоминаний", callback_data="edit_reminders")
    builder.button(text="📋 Типы уведомлений", callback_data="edit_types")
    builder.button(text="🔙 Назад в меню", callback_data="back_to_menu")
    
    builder.adjust(2, 2)
    return builder.as_markup()


def get_reminder_time_keyboard(selected_minutes: List[int]):
    """Создаёт клавиатуру для выбора времени напоминаний."""
    times = [2, 5, 15, 30, 60, 90, 120]
    
    builder = InlineKeyboardBuilder()
    
    for minutes in times:
        hours = minutes // 60
        minutes_remain = minutes % 60
        
        if hours > 0:
            text = f"{hours}ч"
            if minutes_remain > 0:
                text += f" {minutes_remain}м"
        else:
            text = f"{minutes}м"
        
        if minutes in selected_minutes:
            text = f"✅ {text}"
        else:
            text = f"◻️ {text}"
        
        builder.button(text=text, callback_data=f"reminder_{minutes}")
    
    builder.button(text="✅ Готово", callback_data="reminders_done")
    builder.button(text="🔙 Назад", callback_data="notifications_back")
    
    builder.adjust(3, 2, 2)
    return builder.as_markup()


def get_notification_types_keyboard(settings):
    """Создаёт клавиатуру для выбора типов уведомлений."""
    builder = InlineKeyboardBuilder()
    
    new_event_text = "✅ Новые события" if settings.new_event_enabled else "◻️ Новые события"
    builder.button(text=new_event_text, callback_data="toggle_new_events")
    
    updated_text = "✅ Изменения" if settings.event_updated_enabled else "◻️ Изменения"
    builder.button(text=updated_text, callback_data="toggle_event_updates")
    
    cancelled_text = "✅ Отмена" if settings.event_cancelled_enabled else "◻️ Отмена"
    builder.button(text=cancelled_text, callback_data="toggle_event_cancelled")
    
    builder.button(text="✅ Готово", callback_data="types_done")
    builder.button(text="🔙 Назад", callback_data="notifications_back")
    
    builder.adjust(1, 1, 1, 2)
    return builder.as_markup()


@router.callback_query(F.data == "menu_notifications")
async def notifications_menu(callback: CallbackQuery):
    """Меню управления уведомлениями."""
    user_id = callback.from_user.id
    user = await user_service.get_by_tg_id(user_id)

    if not user:
        await callback.answer("❌ Сначала зарегистрируйтесь с помощью /start")
        return
    
    settings = await notification_service.get_or_create_settings(user.id)
    
    status = "✅ Включены" if settings.enabled else "❌ Выключены"
    
    minutes = settings.reminder_minutes or [5, 15, 60]
    times_display = []
    for m in sorted(minutes):
        if m < 60:
            times_display.append(f"{m}м")
        else:
            hours = m // 60
            mins = m % 60
            if mins > 0:
                times_display.append(f"{hours}ч {mins}м")
            else:
                times_display.append(f"{hours}ч")
    
    types_active = []
    if settings.new_event_enabled:
        types_active.append("новые")
    if settings.event_updated_enabled:
        types_active.append("изменения")
    if settings.event_cancelled_enabled:
        types_active.append("отмена")
    
    await callback.message.edit_text(
        f"🔔 <b>Управление уведомлениями</b>\n\n"
        f"Статус: {status}\n\n"
        f"⏰ Напоминания за: {', '.join(times_display)}\n"
        f"📋 Активные уведомления: {', '.join(types_active) if types_active else 'нет'}\n\n"
        f"Здесь вы можете настроить получение уведомлений о событиях хакатона.",
        reply_markup=get_notification_settings_keyboard(user_id, settings.enabled),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "toggle_notifications")
async def toggle_notifications(callback: CallbackQuery):
    """Переключает общую доступность уведомлений."""
    user_id = callback.from_user.id
    user = await user_service.get_by_tg_id(user_id)
    
    if not user:
        await callback.answer("❌ Сначала зарегистрируйтесь с помощью /start")
        return
    
    settings = await notification_service.toggle_enabled(user.id)
    
    await callback.message.edit_text(
        f"{'✅ Уведомления включены' if settings.enabled else '❌ Уведомления выключены'}!",
        parse_mode="HTML"
    )
    
    await asyncio.sleep(1)
    await notifications_menu(callback)


@router.callback_query(F.data == "edit_reminders")
async def edit_reminders(callback: CallbackQuery, state: FSMContext):
    """Редактирование времени напоминаний."""
    user_id = callback.from_user.id
    user = await user_service.get_by_tg_id(user_id)
    
    if not user:
        await callback.answer("❌ Сначала зарегистрируйтесь с помощью /start")
        return
    
    settings = await notification_service.get_or_create_settings(user.id)
    
    await state.set_state(NotificationStates.editing_reminders)
    await state.update_data(
        selected_minutes=(settings.reminder_minutes or [5, 15, 60]).copy(),
        user_id=user.id
    )
    
    await callback.message.edit_text(
        "⏰ <b>Настройка времени напоминаний</b>\n\n"
        "Выберите за сколько времени до события будут приходить уведомления:\n"
        "(Можно выбрать несколько вариантов)",
        reply_markup=get_reminder_time_keyboard(settings.reminder_minutes or [5, 15, 60]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("reminder_"), NotificationStates.editing_reminders)
async def toggle_reminder_time(callback: CallbackQuery, state: FSMContext):
    """Переключает выбранное время напоминания."""
    minutes = int(callback.data.replace("reminder_", ""))
    
    data = await state.get_data()
    selected_minutes = data.get("selected_minutes", [])
    
    if minutes in selected_minutes:
        selected_minutes.remove(minutes)
    else:
        selected_minutes.append(minutes)
    
    await state.update_data(selected_minutes=selected_minutes)
    
    await callback.message.edit_reply_markup(
        reply_markup=get_reminder_time_keyboard(selected_minutes)
    )
    await callback.answer()


@router.callback_query(F.data == "reminders_done", NotificationStates.editing_reminders)
async def save_reminders(callback: CallbackQuery, state: FSMContext):
    """Сохраняет выбранное время напоминаний."""
    data = await state.get_data()
    selected_minutes = data.get("selected_minutes", [15, 60])
    user_id = data.get("user_id")
    
    if user_id:
        settings = await notification_service.update_reminder_times(user_id, selected_minutes)
        
        await state.clear()
        
        await callback.message.edit_text(
            f"✅ Время напоминаний сохранено: {', '.join(str(m) for m in selected_minutes)} минут",
            parse_mode="HTML"
        )
        
        await asyncio.sleep(1)
        await notifications_menu(callback)
    else:
        await callback.answer("Ошибка: пользователь не найден")


@router.callback_query(F.data == "edit_types")
async def edit_notification_types(callback: CallbackQuery, state: FSMContext):
    """Редактирование типов уведомлений."""
    user_id = callback.from_user.id
    user = await user_service.get_by_tg_id(user_id)
    
    if not user:
        await callback.answer("❌ Сначала зарегистрируйтесь с помощью /start")
        return
    
    settings = await notification_service.get_or_create_settings(user.id)
    
    await state.set_state(NotificationStates.editing_types)
    await state.update_data(user_id=user.id)
    
    await callback.message.edit_text(
        "📋 <b>Настройка типов уведомлений</b>\n\n"
        "Выберите какие уведомления вы хотите получать:\n\n",
        reply_markup=get_notification_types_keyboard(settings),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "toggle_new_events")
async def toggle_new_events_handler(callback: CallbackQuery, state: FSMContext):
    """Переключает уведомления о новых событиях."""
    data = await state.get_data()
    user_id = data.get("user_id")

    if user_id:
        settings = await notification_service.toggle_new_events(user_id)
    
        await callback.message.edit_reply_markup(
            reply_markup=get_notification_types_keyboard(settings)
        )
        await callback.answer()
    else:
        await callback.answer("Ошибка: пользователь не найден")


@router.callback_query(F.data == "toggle_event_updates")
async def toggle_event_updates_handler(callback: CallbackQuery, state: FSMContext):
    """Переключает уведомления об изменениях событий."""
    data = await state.get_data()
    user_id = data.get("user_id")

    if user_id:
        settings = await notification_service.toggle_event_updates(user_id)
    
        await callback.message.edit_reply_markup(
            reply_markup=get_notification_types_keyboard(settings)
        )
        await callback.answer()
    else:
        await callback.answer("Ошибка: пользователь не найден")
    


@router.callback_query(F.data == "toggle_event_cancelled")
async def toggle_event_cancelled_handler(callback: CallbackQuery, state: FSMContext):
    """Переключает уведомления об отмене событий."""
    data = await state.get_data()
    user_id = data.get("user_id")
    
    if user_id:
        settings = await notification_service.toggle_event_cancelled(user_id)
    
        await callback.message.edit_reply_markup(
            reply_markup=get_notification_types_keyboard(settings)
        )
        await callback.answer()
    else:
        await callback.answer("Ошибка: пользователь не найден")


@router.callback_query(F.data == "types_done", NotificationStates.editing_types)
async def save_notification_types(callback: CallbackQuery, state: FSMContext):
    """Сохраняет настройки типов уведомлений."""
    await state.clear()
    
    await callback.message.edit_text(
        "✅ Настройки типов уведомлений сохранены!",
        parse_mode="HTML"
    )
    
    await asyncio.sleep(1)
    await notifications_menu(callback)


@router.callback_query(F.data == "notifications_back")
async def back_to_notifications(callback: CallbackQuery, state: FSMContext):
    """Возврат в меню уведомлений."""
    await state.clear()
    await notifications_menu(callback)


# Ниже идут функции для отправки уведомлений о событиях
# Они пока остаются без изменений, так как требуют schedule_service
# который у вас может быть не реализован с БД

# async def send_notification(
#     bot: Bot,
#     user_id: str,
#     title: str,
#     message: str,
#     notification_type: NotificationType = NotificationType.SCHEDULE_REMINDER,
#     user_role: str = "participant"
# ):
#     try:
#         settings = notifications_storage["settings"].get(user_id, get_default_notification_settings(user_role))
        
#         if not settings.get("enabled", True):
#             return False
        
#         if notification_type == NotificationType.NEW_EVENT and not settings.get("new_event_enabled", True):
#             return False
#         elif notification_type == NotificationType.EVENT_UPDATED and not settings.get("event_updated_enabled", True):
#             return False
#         elif notification_type == NotificationType.EVENT_CANCELLED and not settings.get("event_cancelled_enabled", True):
#             return False
        
#         await bot.send_message(
#             user_id,
#             f"<b>{title}</b>\n\n{message}",
#             parse_mode="HTML"
#         )
#         return True
#     except Exception as e:
#         print(f"Error sending notification to {user_id}: {e}")
#         return False

# async def check_and_send_reminders(bot: Bot, temp_users_storage: Dict):
#     current_time_utc = datetime.utcnow()
    
#     for user_id, user_data in temp_users_storage.items():
#         settings = notifications_storage["settings"].get(user_id, get_default_notification_settings())
        
#         if not settings.get("enabled", True):
#             continue
            
#         role = user_data.get("role", "participant")
#         user_timezone = user_data.get("timezone", "UTC+3")
        
#         events = schedule_service.get_events_for_role(role, user_timezone)
        
#         for event in events:
#             creator_tz = event.get('creator_timezone', 'UTC+3')
#             creator_offset = TIMEZONE_OFFSETS.get(creator_tz, 3)
            
#             event_time_utc = event['start_time'] - timedelta(hours=creator_offset)
            
#             time_diff_seconds = (event_time_utc - current_time_utc).total_seconds()
            
#             if time_diff_seconds <= 0:
#                 continue
            
#             reminder_minutes = settings.get("reminder_minutes", get_default_notification_settings()["reminder_minutes"])
            
#             for reminder_mins in reminder_minutes:
#                 reminder_seconds = reminder_mins * 60
                
#                 seconds_from_reminder = time_diff_seconds - reminder_seconds
                
#                 if -30 <= seconds_from_reminder <= 0:
#                     sent_key = f"{event['id']}:{reminder_mins}"
#                     user_sent = notifications_storage["sent_reminders"].setdefault(user_id, set())
                    
#                     if sent_key not in user_sent:
#                         start_str = event['start_time'].strftime("%d.%m.%Y %H:%M")
#                         message = f"<b>{event['title']}</b>\n🕒 Начало: {start_str}\n"
                        
#                         if event.get("location"):
#                             message += f"📍 Место: {event['location']}\n"
                        
#                         if event.get("description"):
#                             desc = event['description'][:200]
#                             if len(event['description']) > 200:
#                                 desc += "..."
#                             message += f"\n{desc}\n"
                        
#                         try:
#                             await bot.send_message(
#                                 user_id,
#                                 f"🔔 <b>Напоминание: через {reminder_mins} минут</b>\n\n{message}",
#                                 parse_mode="HTML"
#                             )
#                             user_sent.add(sent_key)
#                         except Exception:
#                             pass

# async def schedule_reminder_checker(bot: Bot, temp_users_storage: Dict):
#     while True:
#         try:
#             await check_and_send_reminders(bot, temp_users_storage)
#         except Exception as e:
#             print(f"Error in reminder checker: {e}")
        
#         await asyncio.sleep(30)