from aiogram import Router, F, html
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from typing import List
from datetime import datetime

from services.user_service import UserService
from services.task_service import TaskService

router = Router()

class TaskStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_assignee = State()
    waiting_for_edit_choice = State()
    waiting_for_edit_field = State()
    waiting_for_edit_value = State()
    waiting_for_task_selection = State()


def get_organizer_tasks_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Создать задачу", callback_data="org_create_task")
    builder.button(text="✏️ Редактировать задачу", callback_data="org_edit_task")
    builder.button(text="📊 Статистика задач", callback_data="org_tasks_stats")
    builder.button(text="🔙 Назад в меню", callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()

@router.callback_query(F.data == "admin_manage_tasks")
async def manage_tasks(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    user = await UserService().get_by_tg_id(user_id)
    
    if not user or user.role != "organizer":
        await callback.answer("❌ Эта функция доступна только организаторам", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📋 <b>Управление задачами волонтёров</b>\n\n"
        "Выберите действие:",
        reply_markup=get_organizer_tasks_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

def back_to_tasks_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад к управлению задачами", callback_data="admin_manage_tasks")
    return builder.as_markup()

def back_to_stats_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад к статистике", callback_data="org_tasks_stats")
    return builder.as_markup()

@router.callback_query(F.data == "org_create_task")
async def create_task_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(TaskStates.waiting_for_title)
    await callback.message.edit_text(
        "📝 <b>Создание новой задачи</b>\n\n"
        "Введите название задачи:",
        reply_markup=back_to_tasks_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(TaskStates.waiting_for_title)
async def process_task_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(TaskStates.waiting_for_description)
    await message.answer(
        "📝 Теперь введите описание задачи:",
        reply_markup=back_to_tasks_menu_keyboard()
    )

@router.message(TaskStates.waiting_for_description)
async def process_task_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    
    # Получаем всех волонтеров из БД
    users = await UserService().get_all()
    volunteers = []
    
    for user in users:
        if user.role == "volunteer":
            volunteers.append((str(user.telegram_id), user.full_name or f"Волонтер {user.telegram_id}"))
    
    builder = InlineKeyboardBuilder()
    
    builder.button(text="👥 Всем волонтёрам", callback_data="assign_to:all")
    
    if volunteers:
        for uid, name in volunteers:
            builder.button(text=f"👤 {name}", callback_data=f"assign_to:{uid}")
    
    builder.button(text="🔙 Назад", callback_data="org_create_task")
    builder.adjust(1)
    
    await state.set_state(TaskStates.waiting_for_assignee)
    
    if volunteers:
        await message.answer(
            "👥 <b>Выберите, кому назначить задачу:</b>",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "👥 <b>Назначить задачу:</b>\n\n"
            "На данный момент нет зарегистрированных волонтёров. "
            "Вы можете назначить задачу 'всем волонтёрам' - она будет доступна, "
            "когда волонтёры зарегистрируются.",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )

@router.callback_query(F.data.startswith("assign_to:"), TaskStates.waiting_for_assignee)
async def process_task_assignee(callback: CallbackQuery, state: FSMContext):
    assignee = callback.data.split(":")[1]
    task_data = await state.get_data()
    
    # Создаем задачу через TaskService
    try:
        task = await TaskService().create_task(
            title=task_data["title"],
            description=task_data["description"],
            assigned_to=assignee,
            created_by=str(callback.from_user.id)
        )
    except Exception as e:
        await callback.answer(f"❌ Ошибка при создании задачи: {e}", show_alert=True)
        return
    
    await state.clear()
    
    # Получаем информацию о волонтерах для отображения
    users = await UserService().get_all()
    volunteers_count = sum(1 for user in users if user.role == "volunteer")
    
    if assignee == "all":
        if volunteers_count > 0:
            assign_text = f"всем волонтёрам ({volunteers_count} чел.)"
        else:
            assign_text = "всем волонтёрам (пока 0 чел.)"
    else:
        # Ищем волонтера по ID
        volunteer = await UserService().get_by_tg_id(assignee)
        volunteer_name = volunteer.full_name if volunteer else f"Волонтер {assignee}"
        assign_text = f"волонтёру {volunteer_name}"
    
    await callback.message.edit_text(
        f"✅ <b>Задача создана!</b>\n\n"
        f"📌 <b>Название:</b> {task.title}\n"
        f"📝 <b>Описание:</b> {task.description}\n"
        f"👥 <b>Назначена:</b> {assign_text}\n"
        f"🆔 <b>ID задачи:</b> {task.telegram_id}",
        reply_markup=get_organizer_tasks_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

def get_tasks_list_keyboard(action: str, tasks: List):
    """Создает клавиатуру со списком задач"""
    builder = InlineKeyboardBuilder()
    
    for task in tasks:
        if len(task.title) > 30:
            display_title = task.title[:27] + "..."
        else:
            display_title = task.title
        builder.button(text=f"📌 {display_title}", callback_data=f"{action}:{task.telegram_id}")
    
    builder.button(text="🔙 Назад", callback_data="admin_manage_tasks")
    builder.adjust(1)
    return builder.as_markup()

@router.callback_query(F.data == "org_edit_task")
async def edit_task_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    
    # Получаем задачи текущего организатора
    organizer_id = str(callback.from_user.id)
    tasks = await TaskService().get_organizer_tasks(organizer_id)
    
    if not tasks:
        await callback.message.edit_text(
            "📭 <b>Нет созданных задач</b>",
            reply_markup=back_to_tasks_menu_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "✏️ <b>Редактирование задачи</b>\n\n"
        "Выберите задачу для редактирования:",
        reply_markup=get_tasks_list_keyboard("edit_task", tasks),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("edit_task:"))
async def edit_task_selected(callback: CallbackQuery, state: FSMContext):
    task_telegram_id = callback.data.split(":")[1]
    task = await TaskService().get_task_by_telegram_id(task_telegram_id)
    
    if not task:
        await callback.answer("❌ Задача не найдена", show_alert=True)
        return
    
    # Сохраняем task_id в состоянии
    await state.update_data(editing_task_id=task_telegram_id)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Изменить название", callback_data="edit_field:title")
    builder.button(text="📋 Изменить описание", callback_data="edit_field:description")
    builder.button(text="👥 Изменить назначение", callback_data="edit_field:assignee")
    builder.button(text="🗑️ Удалить задачу", callback_data="edit_field:delete")
    builder.button(text="🔙 Назад", callback_data="org_edit_task")
    builder.adjust(1)
    
    # Формируем текст назначения
    if task.assigned_to == "all":
        assign_text = "всем волонтёрам"
    else:
        volunteer = await UserService().get_by_tg_id(task.assigned_to)
        volunteer_name = volunteer.full_name if volunteer else f"Волонтер {task.assigned_to}"
        assign_text = f"волонтёру {volunteer_name}"
    
    await callback.message.edit_text(
        f"✏️ <b>Редактирование задачи</b>\n\n"
        f"📌 <b>Название:</b> {task.title}\n"
        f"📝 <b>Описание:</b> {task.description}\n"
        f"👥 <b>Назначена:</b> {assign_text}\n\n"
        f"<i>Выберите что изменить:</i>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("edit_field:"))
async def edit_field_selected(callback: CallbackQuery, state: FSMContext):
    field = callback.data.split(":")[1]
    task_data = await state.get_data()
    task_telegram_id = task_data.get("editing_task_id")
    
    if not task_telegram_id:
        await callback.answer("❌ Не удалось найти задачу для редактирования", show_alert=True)
        return
    
    if field == "delete":
        # Удаляем задачу
        success = await TaskService().delete_task(task_telegram_id)
        if success:
            await state.clear()
            await callback.message.edit_text(
                "✅ <b>Задача удалена</b>",
                reply_markup=get_organizer_tasks_menu(),
                parse_mode="HTML"
            )
        else:
            await callback.answer("❌ Задача не найдена", show_alert=True)
        return
    
    # Сохраняем данные для редактирования
    await state.update_data(
        editing_task_id=task_telegram_id,
        editing_field=field
    )
    
    field_names = {
        "title": "название",
        "description": "описание",
        "assignee": "назначение"
    }
    
    # Предлагаем ввести новое значение
    field_name = field_names.get(field, field)
    
    if field == "assignee":
        # Для назначения показываем список волонтёров
        users = await UserService().get_all()
        volunteers = []
        
        for user in users:
            if user.role == "volunteer":
                volunteers.append((str(user.telegram_id), user.full_name or f"Волонтер {user.telegram_id}"))
        
        builder = InlineKeyboardBuilder()
        builder.button(text="👥 Всем волонтёрам", callback_data=f"set_assignee:all")
        
        # Добавляем волонтёров, если они есть
        if volunteers:
            for uid, name in volunteers:
                builder.button(text=f"👤 {name}", callback_data=f"set_assignee:{uid}")
        
        builder.button(text="🔙 Назад", callback_data=f"edit_task:{task_telegram_id}")
        builder.adjust(1)
        
        volunteers_count = len(volunteers)
        message_text = "👥 <b>Выберите нового исполнителя для задачи:</b>"
        if volunteers_count == 0:
            message_text += "\n\nНа данный момент нет зарегистрированных волонтёров. " \
                           "Вы можете назначить задачу 'всем волонтёрам' - она будет " \
                           "доступна, когда волонтёры зарегистрируются."
        
        await callback.message.edit_text(
            message_text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    else:
        # Для названия и описания просим ввести текст
        await state.set_state(TaskStates.waiting_for_edit_value)
        task = await TaskService().get_task_by_telegram_id(task_telegram_id)
        current_value = getattr(task, field, "")
        await callback.message.edit_text(
            f"✏️ Введите новое {field_name} (текущее: {current_value}):",
            reply_markup=back_to_tasks_menu_keyboard()
        )
    
    await callback.answer()

# Новый хендлер для установки назначения через кнопки
@router.callback_query(F.data.startswith("set_assignee:"))
async def set_assignee_selected(callback: CallbackQuery, state: FSMContext):
    assignee = callback.data.split(":")[1]
    task_data = await state.get_data()
    task_telegram_id = task_data.get("editing_task_id")
    
    if not task_telegram_id:
        await callback.answer("❌ Задача не найдена", show_alert=True)
        await state.clear()
        return
    
    # Обновляем задачу
    updated_task = await TaskService().update_task(
        telegram_id=task_telegram_id,
        assigned_to=assignee
    )
    
    if not updated_task:
        await callback.answer("❌ Ошибка при обновлении задачи", show_alert=True)
        await state.clear()
        return
    
    await state.clear()
    
    # Показываем обновлённую задачу
    task = await TaskService().get_task_by_telegram_id(task_telegram_id)
    
    if assignee == "all":
        assign_text = "всем волонтёрам"
    else:
        volunteer = await UserService().get_by_tg_id(assignee)
        volunteer_name = volunteer.full_name if volunteer else f"Волонтер {assignee}"
        assign_text = f"волонтёру {volunteer_name}"
    
    await callback.message.edit_text(
        f"✅ <b>Задача обновлена!</b>\n\n"
        f"📌 <b>Название:</b> {task.title}\n"
        f"📝 <b>Описание:</b> {task.description}\n"
        f"👥 <b>Назначена:</b> {assign_text}",
        reply_markup=get_organizer_tasks_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

# Хендлер для текстового ввода (название и описание)
@router.message(TaskStates.waiting_for_edit_value)
async def process_edit_value(message: Message, state: FSMContext):
    task_data = await state.get_data()
    task_telegram_id = task_data.get("editing_task_id")
    field = task_data.get("editing_field")
    
    if not task_telegram_id or not field:
        await message.answer("❌ Ошибка редактирования. Попробуйте снова.")
        await state.clear()
        return
    
    # Обновляем задачу
    update_data = {field: message.text}
    updated_task = await TaskService().update_task(
        telegram_id=task_telegram_id,
        **update_data
    )
    
    if not updated_task:
        await message.answer("❌ Ошибка при обновлении задачи")
        await state.clear()
        return
    
    await state.clear()
    
    # Показываем обновлённую задачу
    task = await TaskService().get_task_by_telegram_id(task_telegram_id)
    
    if task.assigned_to == "all":
        assign_text = "всем волонтёрам"
    else:
        volunteer = await UserService().get_by_tg_id(task.assigned_to)
        volunteer_name = volunteer.full_name if volunteer else f"Волонтер {task.assigned_to}"
        assign_text = f"волонтёру {volunteer_name}"
    
    await message.answer(
        f"✅ <b>Задача обновлена!</b>\n\n"
        f"📌 <b>Название:</b> {task.title}\n"
        f"📝 <b>Описание:</b> {task.description}\n"
        f"👥 <b>Назначена:</b> {assign_text}",
        reply_markup=get_organizer_tasks_menu(),
        parse_mode="HTML"
    )

# --- Статистика задач ---

@router.callback_query(F.data == "org_tasks_stats")
async def show_tasks_stats(callback: CallbackQuery):
    organizer_id = str(callback.from_user.id)
    stats = await TaskService().get_tasks_statistics(organizer_id)
    tasks = await TaskService().get_organizer_tasks(organizer_id)
    
    if not tasks:
        await callback.message.edit_text(
            "📭 <b>Нет созданных задач</b>",
            reply_markup=get_organizer_tasks_menu(),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    # Формируем список задач
    tasks_list_text = ""
    for task in tasks:
        if task.assigned_to == "all":
            assigned = "👥 Всем"
        else:
            volunteer = await UserService().get_by_tg_id(task.assigned_to)
            volunteer_name = volunteer.full_name if volunteer else f"Волонтер {task.assigned_to}"
            assigned = f"👤 {volunteer_name}"
        
        # Определяем статус
        if task.assigned_to == "all":
            # Получаем всех волонтеров
            users = await UserService().get_all()
            all_volunteers = [str(user.telegram_id) for user in users if user.role == "volunteer"]
            completed_count = len(set(task.completed_by) & set(all_volunteers))
            
            if completed_count == len(all_volunteers) and all_volunteers:
                status = "✅"
            elif completed_count > 0:
                status = "🟡"
            else:
                status = "❌"
        else:
            status = "✅" if task.assigned_to in task.completed_by else "❌"
        
        tasks_list_text += f"{status} {task.title} ({assigned})\n"
    
    builder = InlineKeyboardBuilder()
    for task in tasks:
        if len(task.title) > 25:
            display_title = task.title[:22] + "..."
        else:
            display_title = task.title
        builder.button(text=f"📄 {display_title}", callback_data=f"view_task:{task.telegram_id}")
    
    builder.button(text="🔙 Назад", callback_data="admin_manage_tasks")
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"📊 <b>Статистика задач</b>\n\n"
        f"📈 <b>Всего задач:</b> {stats['total_tasks']}\n"
        f"✅ <b>Выполнено:</b> {stats['completed_tasks']}\n"
        f"❌ <b>Не выполнено:</b> {stats['not_completed_tasks']}\n"
        f"📊 <b>Процент выполнения:</b> {stats['completion_rate']}%\n"
        f"👤 <b>Персональных задач:</b> {stats['personal_tasks']}\n"
        f"👥 <b>Групповых задач:</b> {stats['group_tasks']}\n\n"
        f"<b>Список задач:</b>\n{tasks_list_text}\n"
        f"<i>Выберите задачу для просмотра деталей:</i>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("view_task:"))
async def view_task_details(callback: CallbackQuery):
    task_telegram_id = callback.data.split(":")[1]
    task = await TaskService().get_task_by_telegram_id(task_telegram_id)
    
    if not task:
        await callback.answer("❌ Задача не найдена", show_alert=True)
        return
    
    # Формируем текст назначения
    if task.assigned_to == "all":
        assign_text = "👥 <b>Назначена:</b> всем волонтёрам\n"
        users = await UserService().get_all()
        assigned_volunteers = [user.full_name for user in users if user.role == "volunteer"]
        if assigned_volunteers:
            assign_text += f"<b>Волонтёры:</b> {', '.join(assigned_volunteers)}\n"
        else:
            assign_text += "<b>Волонтёры:</b> пока нет зарегистрированных\n"
    else:
        volunteer = await UserService().get_by_tg_id(task.assigned_to)
        volunteer_name = volunteer.full_name if volunteer else f"Волонтер {task.assigned_to}"
        assign_text = f"👤 <b>Назначена:</b> {volunteer_name}\n"
    
    # Статус выполнения
    if task.assigned_to == "all":
        users = await UserService().get_all()
        all_volunteers = [str(user.telegram_id) for user in users if user.role == "volunteer"]
        completed_count = len(set(task.completed_by) & set(all_volunteers))
        if all_volunteers:
            status_text = f"🟡 <b>Статус:</b> выполнено {completed_count}/{len(all_volunteers)} волонтёрами"
            if completed_count == len(all_volunteers):
                status_text = "✅ <b>Статус:</b> выполнено всеми волонтёрами"
            elif completed_count == 0:
                status_text = "❌ <b>Статус:</b> не выполнено"
        else:
            status_text = "⏳ <b>Статус:</b> ожидание волонтёров"
    else:
        if task.assigned_to in task.completed_by:
            status_text = "✅ <b>Статус:</b> выполнено"
        else:
            status_text = "❌ <b>Статус:</b> не выполнено"
    
    created_at = datetime.fromisoformat(task.created_at) if isinstance(task.created_at, str) else task.created_at
    
    await callback.message.edit_text(
        f"📄 <b>Детали задачи</b>\n\n"
        f"📌 <b>Название:</b> {task.title}\n"
        f"📝 <b>Описание:</b> {task.description}\n"
        f"{assign_text}"
        f"{status_text}\n"
        f"📅 <b>Создана:</b> {created_at.strftime('%d.%m.%Y %H:%M')}",
        reply_markup=back_to_stats_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

# --- Меню волонтёра ---

def get_volunteer_tasks_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Текущие задачи", callback_data="volunteer_current_tasks")
    builder.button(text="✅ Выполненные задачи", callback_data="volunteer_completed_tasks")
    builder.button(text="🔙 Назад в меню", callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()

@router.callback_query(F.data == "volunteer_tasks")
async def volunteer_tasks_menu(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    user = await UserService().get_by_tg_id(user_id)
    
    if not user or user.role != "volunteer":
        await callback.answer("❌ Эта функция доступна только волонтёрам", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📋 <b>Мои задачи</b>\n\n"
        "Выберите действие:",
        reply_markup=get_volunteer_tasks_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "volunteer_current_tasks")
async def show_volunteer_current_tasks(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    user = await UserService().get_by_tg_id(user_id)
    
    if not user or user.role != "volunteer":
        await callback.answer("❌ Эта функция доступна только волонтёрам", show_alert=True)
        return
    
    # Получаем активные задачи волонтера
    active_tasks = await TaskService().get_volunteer_active_tasks(user_id)
    
    if not active_tasks:
        await callback.message.edit_text(
            "🎉 <b>У вас нет текущих задач!</b>\n\n"
            "Ожидайте, когда организатор создаст для вас задачи.",
            reply_markup=get_volunteer_tasks_menu(),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    # Разделяем на персональные и групповые
    personal_tasks = [task for task in active_tasks if task.assigned_to == user_id]
    group_tasks = [task for task in active_tasks if task.assigned_to == "all"]
    
    # Формируем текст
    tasks_text = ""
    
    if personal_tasks:
        tasks_text += "👤 <b>Персональные задачи:</b>\n"
        for task in personal_tasks:
            tasks_text += f"❌ {task.title}\n"
    
    if group_tasks:
        tasks_text += "\n👥 <b>Задачи для всех волонтёров:</b>\n"
        for task in group_tasks:
            tasks_text += f"❌ {task.title}\n"
    
    builder = InlineKeyboardBuilder()
    
    # Показываем кнопку "Пометить задачу выполненной" только если есть невыполненные задачи
    if active_tasks:
        builder.button(text="✅ Пометить задачу выполненной", callback_data="mark_task_complete")
    
    builder.button(text="🔙 Назад", callback_data="volunteer_tasks")
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"📋 <b>Текущие задачи</b>\n\n{tasks_text}",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "mark_task_complete")
async def mark_task_complete_menu(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    
    # Получаем невыполненные задачи
    uncompleted_tasks = await TaskService().get_volunteer_active_tasks(user_id)
    
    if not uncompleted_tasks:
        await callback.answer("🎉 У вас нет невыполненных задач!", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    for task in uncompleted_tasks:
        builder.button(text=f"📌 {task.title}", callback_data=f"complete_task:{task.telegram_id}")
    
    builder.button(text="🔙 Назад", callback_data="volunteer_current_tasks")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "✅ <b>Выберите задачу для отметки как выполненную:</b>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("complete_task:"))
async def complete_task(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    task_telegram_id = callback.data.split(":")[1]
    
    task = await TaskService().get_task_by_telegram_id(task_telegram_id)
    if not task:
        await callback.answer("❌ Задача не найдена", show_alert=True)
        return
    
    # Проверяем, назначена ли задача этому волонтёру
    if not await TaskService().is_task_assigned_to(task_telegram_id, user_id):
        await callback.answer("❌ Эта задача не назначена вам", show_alert=True)
        return
    
    # Проверяем, не выполнена ли уже задача
    if await TaskService().is_task_completed_by(task_telegram_id, user_id):
        await callback.answer("✅ Вы уже выполнили эту задачу", show_alert=True)
        return
    
    # Помечаем задачу как выполненную
    success = await TaskService().mark_task_completed(task_telegram_id, user_id)
    
    if success:
        await callback.message.edit_text(
            f"✅ <b>Задача отмечена как выполненная!</b>\n\n"
            f"📌 <b>Название:</b> {task.title}",
            reply_markup=get_volunteer_tasks_menu(),
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Ошибка при отметке задачи", show_alert=True)
    
    await callback.answer()

@router.callback_query(F.data == "volunteer_completed_tasks")
async def show_volunteer_completed_tasks(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    user = await UserService().get_by_tg_id(user_id)
    
    if not user or user.role != "volunteer":
        await callback.answer("❌ Эта функция доступна только волонтёрам", show_alert=True)
        return
    
    # Получаем выполненные задачи
    completed_tasks = await TaskService().get_volunteer_completed_tasks(user_id)
    
    if not completed_tasks:
        await callback.message.edit_text(
            "📭 <b>У вас нет выполненных задач</b>",
            reply_markup=get_volunteer_tasks_menu(),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    # Формируем текст
    tasks_text = "✅ <b>Выполненные задачи:</b>\n\n"
    for task in completed_tasks:
        tasks_text += f"✅ {task.title}\n"
        if len(task.description) > 50:
            tasks_text += f"   <i>{task.description[:47]}...</i>\n\n"
        else:
            tasks_text += f"   <i>{task.description}</i>\n\n"
    
    await callback.message.edit_text(
        tasks_text,
        reply_markup=get_volunteer_tasks_menu(),
        parse_mode="HTML"
    )
    await callback.answer()