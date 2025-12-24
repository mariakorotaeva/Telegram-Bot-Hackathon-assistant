# bot/handlers/command.py
"""
Обработчики для работы с командами
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from services.user_service import UserService
from services.team_service import TeamService
from models.user import UserRole


router = Router()

class AddMemberState(StatesGroup):
    username = State()

class DeleteMemberState(StatesGroup):
    username = State()

def back_to_team_menu_keyboard():
    """Клавиатура с кнопкой назад в меню команды"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="team_menu")
    return builder.as_markup()

def back_to_main_menu_keyboard():
    """Клавиатура с кнопкой назад в главное меню"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад в меню", callback_data="back_to_menu")
    return builder.as_markup()

def get_team_main_menu(is_captain: bool = False, has_team: bool = False):
    """Главное меню команды"""
    builder = InlineKeyboardBuilder()
    
    if has_team:
        if is_captain:
            # builder.button(text="✏️ Название команды", callback_data="team_edit_name")
            builder.button(text="👥 Участники команды", callback_data="team_manage_members")
            builder.button(text="🗑️ Удалить команду", callback_data="team_delete")
        builder.button(text="🔙 Назад в меню", callback_data="back_to_menu")
        builder.adjust(1)
    else:
        builder.button(text="➕ Создать команду", callback_data="team_create")
        builder.button(text="🔙 Назад в меню", callback_data="back_to_menu")
        builder.adjust(1)
    
    return builder.as_markup()

@router.callback_query(F.data == "participant_team_search")
async def team_search_main(callback: CallbackQuery):
    """Главное меню поиска команды"""
    user_id = int(callback.from_user.id)
    user = await UserService().get_by_tg_id(user_id)
    
    if not user:
        await callback.answer("❌ Сначала зарегистрируйтесь с помощью /start", show_alert=True)
        return
    
    team_service = TeamService()
    team = await team_service.get_user_team(user_id)
    is_captain = await team_service.is_user_captain(user_id) if team else False
    
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Анкеты", callback_data="team_profiles_stub")
    builder.button(text="👥 Мои команды", callback_data="team_menu")
    builder.button(text="🔙 Назад в меню", callback_data="back_to_menu")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "👥 <b>Поиск команды</b>\n\n"
        "Выберите опцию:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "team_menu")
async def team_menu(callback: CallbackQuery):
    """Меню управления командой"""
    user_id = int(callback.from_user.id)
    user = await UserService().get_by_tg_id(user_id)
    
    team_service = TeamService()
    team = await team_service.get_user_team(user.id)
    is_captain = await team_service.is_user_captain(user.id) if team else False
    
    if team:
        if is_captain:
            members = await team_service.team_repo.get_team_members(team.id)
            text = (
                f"👥 <b>Управление командой</b>\n\n"
                f"Название: <b>{team.name}</b>\n"
                f"Участников: {len(members)}\n\n"
                f"Вы являетесь капитаном команды."
            )
        else:
            members = await team_service.team_repo.get_team_members(team.id)
            
            members_list = []
            for member in members:
                role = "👑 Капитан" if member.id == team.captain_id else "👤 Участник"
                tg_username = f"@{member.username}" if member.username else "без username"
                members_list.append(f"• {member.full_name} ({role})\n   {tg_username}")
            
            members_text = "\n\n".join(members_list) if members_list else "Нет участников"
            
            text = (
                f"👥 <b>Ваша команда</b>\n\n"
                f"Название: <b>{team.name}</b>\n\n"
                f"<b>Участники:</b>\n{members_text}"
            )
    else:
        text = (
            "👥 <b>Мои команды</b>\n\n"
            "У вас пока нет команды.\n\n"
            "Вы можете создать команду, если хотите стать капитаном. "
            "Если нет, попросите капитана добавить вас."
        )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_team_main_menu(is_captain=is_captain, has_team=bool(team)),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "team_add_member")
async def team_member_delete(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddMemberState.username)
    await callback.message.edit_text(
        "Введите username пользователя, которого желаете добавить:",
        reply_markup=back_to_main_menu_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "team_delete_member")
async def team_member_delete(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DeleteMemberState.username)
    await callback.message.edit_text(
        "Введите username пользователя, которого желаете удалить:",
        reply_markup=back_to_main_menu_keyboard(),
        parse_mode="HTML"
    )
    #await callback.answer()

@router.message(AddMemberState.username)
async def team_member_add_process_name(message: Message, state: FSMContext):
    await state.clear()

    user_id = int(message.from_user.id)
    user = await UserService().get_by_tg_id(user_id)

    user_to_add = await UserService().get_by_tg_username(message.text)
    if not user_to_add:
        await message.answer(f"❌ Пользователь @{message.text} не найден!", show_alert=True)
        return

    in_team = await TeamService().is_user_in_team(user_to_add.id)
    if in_team:
        await message.answer(f"❌ Пользователь @{message.text} уже состоит в команде!", show_alert=True)
        return

    success, msg = await TeamService().join_team(user_to_add.id, user.team_id)
    if success:
        await message.answer(f"Пользователь @{message.text} успешно добавлен в команду!", show_alert=True)
    else:
        await message.answer(f"Ошибка добавления пользователя @{message.text}: {msg}")
    

@router.message(DeleteMemberState.username)
async def team_member_delete_process_name(message: Message, state: FSMContext):
    await state.clear()

    user_id = int(message.from_user.id)
    user = await UserService().get_by_tg_id(user_id)

    user_to_delete = await UserService().get_by_tg_username(message.text)
    if not user_to_delete:
        await message.answer(f"❌ Пользователь @{message.text} не найден!", show_alert=True)
        return

    in_team = await TeamService().is_user_in_team(user_to_delete.id)
    if not in_team or user_to_delete.team_id != user.team_id:
        await message.answer(f"❌ Пользователь @{message.text} не состоит в команде!", show_alert=True)
        return

    success, msg = await TeamService().leave_team(user_to_delete.id)
    if success:
        await message.answer(f"Пользователь @{message.text} успешно удален из команды!", show_alert=True)
    else:
        await message.answer(f"Ошибка удаления пользователя @{message.text}: {msg}")



@router.callback_query(F.data == "team_create")
async def team_create(callback: CallbackQuery, state: FSMContext):
    """Создание команды"""
    user_id = int(callback.from_user.id)
    
    team_service = TeamService()
    
    user = await UserService().get_by_tg_id(user_id)
    if not user:
        await callback.answer("❌ Сначала зарегистрируйтесь с помощью /start", show_alert=True)
        return
    
    existing_team = await team_service.get_user_team(user.id)
    if existing_team:
        await callback.answer("❌ Вы уже состоите в команде!", show_alert=True)
        return
    
    if await team_service.is_user_captain(user.id):
        await callback.answer("❌ Вы уже являетесь капитаном команды!", show_alert=True)
        return
    
    await state.update_data(creating_team=True, user_telegram_id=user_id)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="team_menu")
    
    await callback.message.edit_text(
        "👥 <b>Создание команды</b>\n\n"
        "Пожалуйста, введите название для вашей новой команды:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(F.text)
async def process_team_name(message: Message, state: FSMContext):
    """Обработка названия команды"""
    user_id = int(message.from_user.id)
    user = await UserService().get_by_tg_id(user_id)
    data = await state.get_data()
    
    team_name = message.text.strip()
    
    if len(team_name) > 100:
        await message.answer(
            "❌ Название команды слишком длинное.\n"
        )
        return
    
    team_service = TeamService()
    success, team, message_text = await team_service.create_team(user.id, team_name)
    
    if success:
        await message.answer(
            f"✅ Команда создана!\n\n"
            f"Теперь вы капитан команды <b>{team_name}</b>.\n",
            parse_mode="HTML"
        )
        
        builder = InlineKeyboardBuilder()
        builder.button(text="👥 Управление командой", callback_data="team_menu")
        builder.button(text="🔙 Назад в меню", callback_data="back_to_menu")
        builder.adjust(1)
        
        await message.answer(
            "ЭЭээ",
            reply_markup=builder.as_markup()
        )
    else:
        await message.answer(f"❌ {message_text}")
    
    await state.clear()

@router.callback_query(F.data == "team_view")
async def team_view(callback: CallbackQuery):
    """Просмотр информации о команде (для участника)"""
    user_id = int(callback.from_user.id)
    user = await UserService().get_by_tg_id(user_id)
    team_service = TeamService()
    team = await team_service.get_user_team(user.id)
    
    if not team:
        await callback.answer("❌ У вас нет команды!", show_alert=True)
        return
    
    # Получаем участников команды
    members = await team_service.team_repo.get_team_members(team.id)
    
    # Формируем подробную информацию о команде
    captain = await team_service.user_repo.get_by_id(team.captain_id)
    captain_tg = f"@{captain.username}" if captain.username else "без username"
    
    members_list = []
    for member in members:
        role = "👑 Капитан" if member.id == team.captain_id else "👤 Участник"
        tg_username = f"@{member.username}" if member.username else "без username"
        members_list.append(f"• {member.full_name} ({role})\n   Telegram: {tg_username}")
    
    members_text = "\n\n".join(members_list) if members_list else "Нет участников"
    
    # Информация о менторе, если есть
    mentor_info = ""
    if team.mentor_id:
        mentor = await team_service.user_repo.get_by_id(team.mentor_id)
        if mentor:
            mentor_tg = f"@{mentor.username}" if mentor.username else "без username"
            mentor_info = f"\n\n🧠 <b>Ментор:</b>\n{mentor.full_name}\nTelegram: {mentor_tg}"
    
    text = (
        f"👥 <b>Информация о команде</b>\n\n"
        f"🏷️ <b>Название:</b> {team.name}\n"
        f"👑 <b>Капитан:</b>\n{captain.full_name}\nTelegram: {captain_tg}\n"
        f"👥 <b>Участники ({team.member_count}/5):</b>\n{members_text}"
        f"{mentor_info}"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="team_menu")
    
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "team_edit_name")
async def team_edit_name(callback: CallbackQuery, state: FSMContext):
    """Изменение названия команды"""
    user_id = int(callback.from_user.id)
    user = await UserService().get_by_tg_id(user_id)
    
    team_service = TeamService()
    team = await team_service.team_repo.get_team_by_captain(user.id)
    
    if not team:
        await callback.answer("❌ Вы не являетесь капитаном команды!", show_alert=True)
        return
    
    await state.update_data(editing_team_name=True, current_team_id=team.id)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="team_menu")
    
    await callback.message.edit_text(
        f"✏️ <b>Изменение названия команды</b>\n\n"
        f"Текущее название: <b>{team.name}</b>\n\n"
        f"Введите новое название для команды:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "team_manage_members")
async def team_manage_members(callback: CallbackQuery):
    """Управление участниками команды (заглушка)"""
    user_id = int(callback.from_user.id)
    user = await UserService().get_by_tg_id(user_id)
    
    # Проверяем, является ли пользователь капитаном
    team_service = TeamService()
    team = await team_service.team_repo.get_team_by_captain(user.id)
    
    if not team:
        await callback.answer("❌ Вы не являетесь капитаном команды!", show_alert=True)
        return
    
    # Получаем участников команды
    members = await team_service.team_repo.get_team_members(team.id)
    
    members_list = []
    for member in members:
        if member.id == team.captain_id:
            members_list.append(f"👑 {member.full_name} (Капитан)")
        else:
            members_list.append(f"👤 {member.full_name}")
    
    members_text = "\n".join(members_list) if members_list else "Нет участников"
    
    text = (
        f"👥 <b>Управление участниками</b>\n\n"
        f"Команда: <b>{team.name}</b>\n\n"
        f"<b>Текущие участники:</b>\n{members_text}\n\n"
        f"Эта функция находится в разработке.\n"
        f"Скоро здесь появится возможность добавлять и удалять участников."
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить Участника", callback_data="team_add_member")
    builder.button(text="Удалить Участника", callback_data="team_delete_member")
    builder.button(text="🔙 Назад", callback_data="team_menu")
    builder.adjust(1)
    
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "team_delete")
async def team_delete(callback: CallbackQuery):
    """Подтверждение удаления команды"""
    user_id = int(callback.from_user.id)
    user = await UserService().get_by_tg_id(user_id)
    
    # Проверяем, является ли пользователь капитаном
    team = await TeamService().team_repo.get_team_by_captain(user.id)

    
    if not team:
        await callback.answer("❌ Вы не являетесь капитаном команды!", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить команду", callback_data=f"team_delete_confirm:{team.id}")
    builder.button(text="❌ Нет, отменить", callback_data="team_menu")
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"🗑️ <b>Удаление команды</b>\n\n"
        f"Вы уверены, что хотите удалить команду <b>'{team.name}'</b>?\n\n"
        f"⚠️ <b>Внимание:</b> Это действие нельзя отменить. "
        f"Все участники команды будут удалены из неё.",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("team_delete_confirm:"))
async def team_delete_confirm(callback: CallbackQuery):
    """Подтвержденное удаление команды"""
    user_id = int(callback.from_user.id)
    team_id = int(callback.data.split(":")[1])

    user = await UserService().get_by_tg_id(user_id)
    
    # Проверяем, является ли пользователь капитаном этой команды
    team = await TeamService().get_team_by_captain(user.id)
    
    if not team or team.id != team_id:
        await callback.answer("❌ Вы не являетесь капитаном этой команды!", show_alert=True)
        return
    
    # Удаляем команду
    success, message_text = await TeamService().dissolve_team(user.id)
    
    if success:
        text = f"✅ {message_text}"
    else:
        text = f"❌ {message_text}"
    
    await callback.message.edit_text(
        text,
        reply_markup=back_to_main_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

# @router.callback_query(F.data == "team_profiles_stub")
# async def profile_menu_view(callback: CallbackQuery):
#     builder = InlineKeyboardBuilder()
#     builder.button(text="Моя анкета", callback_data=f"my_profile_view")
#     builder.button(text="Смотреть чужие анкеты", callback_data="other_profiles_view")
#     builder.adjust(1)
    
#     await callback.message.edit_text(
#         f"🗑️ <b>Удаление команды</b>\n\n"
#         f"Вы уверены, что хотите удалить команду <b>'{team.name}'</b>?\n\n"
#         f"⚠️ <b>Внимание:</b> Это действие нельзя отменить. "
#         f"Все участники команды будут удалены из неё.",
#         reply_markup=builder.as_markup(),
#         parse_mode="HTML"
#     )
#     await callback.answer()