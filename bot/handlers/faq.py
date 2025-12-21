from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command

from bot.services.faq_service import faq_service
from services.user_service import UserService

router = Router()


CATEGORY_TITLES = {
    "general": "📋 Общие вопросы",
    "registration": "📝 Регистрация",
    "technical": "⚙️ Технические вопросы"
}

@router.message(Command("faq"))
@router.message(F.text == "❓ Частые вопросы")
async def show_faq_from_message(message: types.Message):
    """
    Обработчик для команды /faq - доступен только участникам
    """
    user_id = int(message.from_user.id)
    user = await UserService().get_by_tg_id(user_id)
    
    if not user:
        await message.answer("❌ Сначала зарегистрируйтесь с помощью /start")
        return
    
    if user.role != "participant":
        await message.answer(
            "ℹ️ <b>FAQ доступен только участникам хакатона</b>\n\n"
            "Организаторы, менторы и волонтеры могут использовать "
            "другие функции меню.",
            parse_mode="HTML"
        )
        return
    
    categories = faq_service.get_categories()
    
    if not categories:
        await message.answer("📚 FAQ временно недоступен. Попробуйте позже.")
        return
    
    builder = InlineKeyboardBuilder()
    
    for category in categories:
        button_text = CATEGORY_TITLES.get(category, category.capitalize())
        
        builder.button(
            text=button_text,
            callback_data=f"faq_category:{category}"
        )
    
    builder.button(
        text="📚 Все вопросы",
        callback_data="faq_all"
    )
    
    builder.adjust(1)
    
    await message.answer(
        "📚 <b>Часто задаваемые вопросы</b>\n\n"
        "Выберите категорию:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("faq_category:"))
async def show_category_questions(callback: types.CallbackQuery):
    """
    Показывает вопросы выбранной категории
    """
    category = callback.data.split(":")[1]
    questions = faq_service.get_questions_by_category(category)
    
    if not questions:
        await callback.answer("В этой категории пока нет вопросов", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    
    for index, qa in enumerate(questions):
        question_text = qa["question"]
        if len(question_text) > 40:
            question_text = question_text[:37] + "..."
        
        builder.button(
            text=f"• {question_text}",
            callback_data=f"faq_answer:{category}:{index}"
        )
    
    builder.button(
        text="🔙 К категориям",
        callback_data="participant_faq"
    )
    
    builder.adjust(1)
    
    category_title = CATEGORY_TITLES.get(category, category.capitalize())
    
    await callback.message.edit_text(
        f"📁 <b>Категория:</b> {category_title}\n\n"
        f"Выберите вопрос:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "faq_all")
async def show_all_questions(callback: types.CallbackQuery):
    """
    Показывает все вопросы из всех категорий
    """
    all_questions = faq_service.get_all_questions()
    
    if not all_questions:
        await callback.answer("Вопросы не найдены", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    
    for question_item in all_questions:
        question_text = question_item["question"]
        if len(question_text) > 40:
            question_text = question_text[:37] + "..."
        
        category_icons = {
            "general": "📋",
            "registration": "📝",
            "technical": "⚙️"
        }
        
        icon = category_icons.get(question_item["category"], "❓")
        
        builder.button(
            text=f"{icon} {question_text}",
            callback_data=f"faq_answer_id:{question_item['id']}"
        )
    
    builder.button(
        text="🔙 К категориям",
        callback_data="participant_faq"
    )
    
    builder.adjust(1)
    
    await callback.message.edit_text(
        "📚 <b>Все часто задаваемые вопросы</b>\n\n"
        "Выберите вопрос:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("faq_answer:"))
async def show_answer(callback: types.CallbackQuery):
    """
    Показывает ответ на выбранный вопрос
    """
    _, category, index_str = callback.data.split(":")
    index = int(index_str)
    
    questions = faq_service.get_questions_by_category(category)
    
    if index >= len(questions):
        await callback.answer("Вопрос не найден", show_alert=True)
        return
    
    qa = questions[index]
    
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔙 К вопросам категории",
        callback_data=f"faq_category:{category}"
    )
    builder.button(
        text="📚 К списку категорий",
        callback_data="participant_faq"
    )
    
    builder.adjust(1)
    
    category_title = CATEGORY_TITLES.get(category, category.capitalize())
    
    await callback.message.edit_text(
        f"📁 <b>Категория:</b> {category_title}\n\n"
        f"❓ <b>Вопрос:</b>\n{qa['question']}\n\n"
        f"💡 <b>Ответ:</b>\n{qa['answer']}",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("faq_answer_id:"))
async def show_answer_by_id(callback: types.CallbackQuery):
    """
    Показывает ответ на вопрос по ID (для "Все вопросы")
    """
    question_id = callback.data.split(":")[1]
    
    all_questions = faq_service.get_all_questions()
    question_item = next((q for q in all_questions if q["id"] == question_id), None)
    
    if not question_item:
        await callback.answer("Вопрос не найден", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔙 К списку вопросов",
        callback_data="faq_all"
    )
    builder.button(
        text="📚 К списку категорий",
        callback_data="participant_faq"
    )
    
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"❓ <b>Вопрос:</b>\n{question_item['question']}\n\n"
        f"💡 <b>Ответ:</b>\n{question_item['answer']}",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

def back_to_menu_keyboard():
    """
    Создает клавиатуру с кнопкой "Назад в меню"
    """
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")]
        ]
    )