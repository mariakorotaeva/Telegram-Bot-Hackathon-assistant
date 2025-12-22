# bot/handlers/profiles.py
"""
Обработчики для работы с анкетами участников
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

from services.user_service import UserService
from services.team_service import TeamService

router = Router()

def back_to_profiles_menu_keyboard():
    """Клавиатура с кнопкой назад в меню анкет"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="profiles_menu")
    return builder.as_markup()

def back_to_main_menu_keyboard():
    """Клавиатура с кнопкой назад в главное меню"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад в меню", callback_data="back_to_menu")
    return builder.as_markup()

def get_profiles_main_menu():
    """Главное меню анкет"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="👀 Смотреть другие анкеты", callback_data="view_profiles")
    builder.button(text="📝 Моя анкета", callback_data="my_profile")
    builder.button(text="🔙 Назад в меню", callback_data="back_to_menu")
    builder.adjust(1)
    
    return builder.as_markup()

@router.callback_query(F.data == "team_profiles_stub")
async def team_profiles_main(callback: CallbackQuery):
    """Главное меню анкет (вместо заглушки)"""
    await callback.message.edit_text(
        "📝 <b>Анкеты участников</b>\n\n"
        "Здесь вы можете:\n"
        "• Просматривать анкеты других участников\n"
        "• Создать и редактировать свою анкету",
        reply_markup=get_profiles_main_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "profiles_menu")
async def profiles_menu(callback: CallbackQuery):
    """Меню анкет (переход обратно)"""
    await team_profiles_main(callback)

@router.callback_query(F.data == "view_profiles")
async def view_profiles(callback: CallbackQuery):
    """Просмотр анкет других участников"""
    user_id = int(callback.from_user.id)
    user_service = UserService()
    
    # Получаем 5 случайных активных анкет
    profiles = await user_service.get_random_active_profiles(
        limit=5, 
        exclude_user_id=user_id
    )
    
    if not profiles:
        builder = InlineKeyboardBuilder()
        builder.button(text="🔄 Попробовать еще", callback_data="view_profiles")
        builder.button(text="🔙 Назад", callback_data="profiles_menu")
        builder.adjust(1)
        
        await callback.message.edit_text(
            "👀 <b>Анкеты участников</b>\n\n"
            "К сожалению, сейчас нет активных анкет других участников.\n\n"
            "Попробуйте позже или создайте свою анкету!",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    # Формируем сообщение с анкетами
    profiles_text = []
    for i, profile_user in enumerate(profiles, 1):
        if profile_user.profile_text:
            preview = profile_user.profile_text.strip()
            if len(preview) > 150:
                preview = preview[:150] + "..."
        else:
            preview = "Анкета пустая"
        
        tg_username = f"@{profile_user.username}" if profile_user.username else "без username"
        
        profile_info = (
            f"<b>{i}. {profile_user.full_name}</b>\n"
            f"📱 Telegram: {tg_username}\n"
            f"📝 <i>{preview}</i>\n"
            f"─────────────────"
        )
        profiles_text.append(profile_info)
    
    full_text = (
        "👀 <b>Активные анкеты участников</b>\n\n"
        "Вот случайные анкеты других участников, которые ищут команду:\n\n"
    ) + "\n\n".join(profiles_text)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Выслать ещё анкеты", callback_data="view_more_profiles")
    builder.button(text="🔙 Назад", callback_data="profiles_menu")
    builder.adjust(1)
    
    await callback.message.edit_text(
        full_text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "view_more_profiles")
async def view_more_profiles(callback: CallbackQuery):
    """Показывает ещё 5 случайных анкет"""
    await view_profiles(callback)

@router.callback_query(F.data == "my_profile")
async def my_profile(callback: CallbackQuery):
    """Моя анкета"""
    user_id = int(callback.from_user.id)
    user_service = UserService()
    user = await user_service.get_by_tg_id(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    # Проверяем, есть ли у пользователя команда
    team_service = TeamService()
    has_team = await team_service.is_user_in_team(user_id)
    
    # Формируем текст анкеты
    if not user.profile_text or not user.profile_text.strip():
        profile_text = "<i>Анкета пустая</i>"
        is_empty = True
    else:
        profile_text = user.profile_text.strip()
        is_empty = False
    
    if is_empty:
        status_text = "❌ Неактивна (анкета пустая)"
    else:
        if user.is_profile_active and not has_team:
            status_text = "✅ Активна (видят другие участники)"
        elif has_team:
            status_text = "❌ Неактивна (вы состоите в команде)"
        else:
            status_text = "❌ Неактивна"
    
    text = (
        f"📝 <b>Моя анкета</b>\n\n"
        f"<b>Статус:</b> {status_text}\n\n"
        f"<b>Текст анкеты:</b>\n"
        f"{profile_text}"
    )
    
    builder = InlineKeyboardBuilder()
    
    if is_empty:
        builder.button(text="✏️ Создать анкету", callback_data="edit_profile")
    else:
        if has_team:
            # Если в команде, можно только редактировать, но нельзя активировать
            builder.button(text="✏️ Редактировать анкету", callback_data="edit_profile")
        else:
            if user.is_profile_active:
                builder.button(text="⏸️ Сделать неактивной", callback_data="toggle_profile_active")
            else:
                builder.button(text="▶️ Сделать активной", callback_data="toggle_profile_active")
            
            builder.button(text="✏️ Редактировать анкету", callback_data="edit_profile")
    
    builder.button(text="🔙 Назад", callback_data="profiles_menu")
    
    if has_team:
        builder.adjust(1)
    else:
        builder.adjust(2, 1)
    
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "toggle_profile_active")
async def toggle_profile_active(callback: CallbackQuery):
    """Переключает активность анкеты"""
    user_id = int(callback.from_user.id)
    user_service = UserService()
    user = await user_service.get_by_tg_id(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    # Проверяем, есть ли у пользователя команда
    team_service = TeamService()
    has_team = await team_service.is_user_in_team(user_id)
    
    if has_team:
        await callback.answer("❌ Нельзя активировать анкету, если вы в команде!", show_alert=True)
        return
    
    if not user.profile_text or not user.profile_text.strip():
        await callback.answer("❌ Нельзя активировать пустую анкету!", show_alert=True)
        return
    
    # Меняем статус через сервис
    new_active_status = not user.is_profile_active
    success = await user_service.set_profile_active(user.id, new_active_status)
    
    if success:
        status_word = "активной" if new_active_status else "неактивной"
        await callback.answer(f"✅ Анкета сделана {status_word}", show_alert=True)
        await my_profile(callback)  # Обновляем отображение
    else:
        await callback.answer("❌ Ошибка при изменении статуса", show_alert=True)

@router.callback_query(F.data == "edit_profile")
async def edit_profile_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования анкеты"""
    user_id = int(callback.from_user.id)
    user_service = UserService()
    user = await user_service.get_by_tg_id(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    current_text = user.profile_text if user.profile_text else ""
    
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="my_profile")
    
    await state.update_data(editing_profile=True)
    
    if current_text:
        message_text = (
            f"✏️ <b>Редактирование анкеты</b>\n\n"
            f"<b>Текущий текст:</b>\n"
            f"{current_text}\n\n"
            f"Введите новый текст анкеты (макс. 2000 символов):"
        )
    else:
        message_text = (
            f"✏️ <b>Создание анкеты</b>\n\n"
            f"Введите текст вашей анкеты (макс. 2000 символов).\n\n"
            f"<b>Что можно написать:</b>\n"
            f"• О себе и своём опыте\n"
            f"• Навыки и технологии\n"
            f"• Роль, которую хотите в команде\n"
            f"• Интересы и темы проектов"
        )
    
    await callback.message.edit_text(
        message_text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(F.text)
async def process_profile_text(message: Message, state: FSMContext):
    """Обработка текста анкеты"""
    data = await state.get_data()
    
    if not data.get('editing_profile'):
        return
    
    user_id = int(message.from_user.id)
    user_service = UserService()
    user = await user_service.get_by_tg_id(user_id)
    
    if not user:
        await message.answer("❌ Пользователь не найден")
        await state.clear()
        return
    
    text = message.text.strip()
    
    # Проверка длины
    if len(text) > 2000:
        await message.answer(
            "❌ Текст слишком длинный (макс. 2000 символов).\n"
            "Пожалуйста, введите более короткий текст:"
        )
        return
    
    if len(text) < 10:
        await message.answer(
            "❌ Текст слишком короткий (мин. 10 символов).\n"
            "Пожалуйста, напишите подробнее о себе:"
        )
        return
    
    # Обновляем анкету через сервис
    success = await user_service.update_user_profile(user.id, text)
    
    if success:
        # Автоматически делаем анкету неактивной после редактирования
        await user_service.set_profile_active(user.id, False)
        
        await message.answer(
            "✅ Анкета сохранена!\n\n"
            "Теперь вы можете активировать её, чтобы другие участники могли её видеть.",
            reply_markup=back_to_profiles_menu_keyboard()
        )
    else:
        await message.answer(
            "❌ Ошибка при сохранении анкеты",
            reply_markup=back_to_profiles_menu_keyboard()
        )
    
    await state.clear()