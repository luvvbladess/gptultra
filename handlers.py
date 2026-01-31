"""
Обработчики сообщений Telegram бота
"""

import logging
import asyncio
from typing import Optional

from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import (
    SYSTEM_PROMPT, 
    MAX_HISTORY_MESSAGES,
    MAX_TELEGRAM_MESSAGE_LENGTH,
    AVAILABLE_MODELS
)
from openai_client import get_chat_response, encode_image_to_base64, generate_image, edit_image_with_dalle, transcribe_audio
from document_parser import extract_text_from_file
from conversations import conversation_manager
from keyboards import (
    get_main_menu_keyboard,
    get_conversations_keyboard,
    get_conversation_actions_keyboard,
    get_confirm_delete_keyboard,
    get_confirm_clear_keyboard,
    get_cancel_keyboard,
    get_models_keyboard
)


logger = logging.getLogger(__name__)
router = Router()


class AnimatedLoader:
    """Анимированный лоадер с редактированием сообщения"""
    
    def __init__(self, message: Message, base_text: str = "Ищу ответ на Ваш вопрос"):
        self.message = message
        self.base_text = base_text
        self.status_msg = None
        self.running = False
        self.task = None
    
    async def start(self) -> Message:
        """Запускает анимацию"""
        self.status_msg = await self.message.reply(f"{self.base_text}...")
        self.running = True
        self.task = asyncio.create_task(self._animate())
        return self.status_msg
    
    async def _animate(self):
        """Анимация точек"""
        dots = [".", "..", "..."]
        i = 0
        while self.running:
            try:
                await asyncio.sleep(0.8)
                if not self.running:
                    break
                i = (i + 1) % len(dots)
                await self.status_msg.edit_text(f"{self.base_text}{dots[i]}")
            except Exception:
                break
    
    async def stop_with_result(self, result_text: str = None):
        """Останавливает анимацию и заменяет на результат"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        return self.status_msg
    
    async def stop(self):
        """Просто останавливает анимацию"""
        self.running = False
        if self.task:
            self.task.cancel()


# Состояния FSM
class BotStates(StatesGroup):
    waiting_for_rename = State()



@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """Обработчик команды /start"""
    user_id = message.from_user.id
    
    # Создаём первую беседу, если её нет
    if not conversation_manager.get_conversations(user_id):
        conversation_manager.create_conversation(user_id, "Новая беседа")
    
    current_model = conversation_manager.get_user_model(user_id)
    model_name = AVAILABLE_MODELS.get(current_model, current_model)
    
    welcome_text = f"""👋 **Привет!**

Я — AI-ассистент на базе OpenAI GPT.

**Что я умею:**
• 💬 Вести несколько бесед параллельно
• 🖼 Анализировать изображения
• 📄 Читать PDF и DOCX документы
• 🤖 Переключаться между моделями

**Текущая модель:** {model_name}

Используй меню ниже для управления.
Просто напиши сообщение, чтобы начать! 🚀"""
    
    await message.answer(welcome_text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Обработчик команды /help"""
    await show_help(message)


# ============== КНОПКИ МЕНЮ ==============

@router.message(F.text == "📝 Новая беседа")
async def btn_new_conversation(message: Message) -> None:
    """Создание новой беседы"""
    user_id = message.from_user.id
    conv = conversation_manager.create_conversation(user_id)
    
    await message.answer(
        f"✅ Создана новая беседа: **{conv.title}**\n\n"
        "Напиши мне что-нибудь!",
        parse_mode="Markdown"
    )


@router.message(F.text == "📂 Мои беседы")
async def btn_my_conversations(message: Message) -> None:
    """Показать список бесед"""
    user_id = message.from_user.id
    
    conversations = conversation_manager.get_conversations(user_id)
    active = conversation_manager.get_active_conversation(user_id)
    active_id = active.id if active else None
    
    if not conversations:
        text = "У тебя пока нет бесед. Создай первую!"
    else:
        text = f"📂 **Твои беседы** ({len(conversations)}):\n\n"
        text += "Выбери беседу или создай новую:"
    
    await message.answer(
        text,
        reply_markup=get_conversations_keyboard(conversations, active_id),
        parse_mode="Markdown"
    )


@router.message(F.text == "🤖 Модель")
async def btn_select_model(message: Message) -> None:
    """Показать выбор модели"""
    user_id = message.from_user.id
    current_model = conversation_manager.get_user_model(user_id)
    
    await message.answer(
        "🤖 **Выбери модель:**\n\n"
        "Разные модели имеют разные возможности и скорость.",
        reply_markup=get_models_keyboard(current_model),
        parse_mode="Markdown"
    )


@router.message(F.text == "🎨 Редактор")
async def btn_editor_mode(message: Message) -> None:
    """Включить/выключить режим редактирования изображений"""
    user_id = message.from_user.id
    
    is_edit_mode = conversation_manager.is_edit_mode(user_id)
    
    if is_edit_mode:
        # Выключаем режим
        conversation_manager.set_edit_mode(user_id, False)
        await message.answer(
            "🎨 **Режим редактирования выключен**\n\n"
            "Теперь бот работает в обычном режиме.",
            parse_mode="Markdown"
        )
    else:
        # Включаем режим
        conversation_manager.set_edit_mode(user_id, True)
        await message.answer(
            "🎨 **Режим редактирования включён!**\n\n"
            "📸 **Как использовать:**\n"
            "1. Отправь фото, которое хочешь редактировать\n"
            "2. Напиши что изменить (например: \"добавь шляпу\")\n"
            "3. Бот запомнит картинку и можно продолжать редактировать\n\n"
            "💡 Картинка сохраняется до выхода из режима.\n"
            "Нажми 🎨 Редактор ещё раз чтобы выйти.",
            parse_mode="Markdown"
        )


@router.message(F.text == "🖼 DALL-E")
async def btn_dalle_mode(message: Message) -> None:
    """Включить/выключить DALL-E режим генерации"""
    user_id = message.from_user.id
    
    is_dalle_mode = conversation_manager.is_dalle_mode(user_id)
    
    if is_dalle_mode:
        # Выключаем режим
        conversation_manager.set_dalle_mode(user_id, False)
        await message.answer(
            "🖼 **DALL-E режим выключен**\n\n"
            "Теперь бот работает в обычном режиме.",
            parse_mode="Markdown"
        )
    else:
        # Включаем режим
        conversation_manager.set_dalle_mode(user_id, True)
        await message.answer(
            "🖼 **DALL-E режим включён!**\n\n"
            "🎨 **Как использовать:**\n"
            "• Просто напиши что нарисовать\n"
            "• Бот запомнит последнюю картинку\n"
            "• Можешь дописать: \"добавь солнце\" - и он отредактирует\n\n"
            "💡 Первое сообщение = новая картинка\n"
            "Следующие = редактирование\n\n"
            "Нажми 🖼 DALL-E ещё раз чтобы выйти.",
            parse_mode="Markdown"
        )



@router.message(F.text == "🗑 Очистить")
async def btn_clear_current(message: Message) -> None:
    """Очистка текущей беседы"""
    user_id = message.from_user.id
    conv = conversation_manager.get_active_conversation(user_id)
    
    if not conv:
        await message.answer("❌ Нет активной беседы.")
        return
    
    await message.answer(
        f"🧹 Очистить историю беседы **{conv.title}**?\n\n"
        "Все сообщения будут удалены.",
        reply_markup=get_confirm_clear_keyboard(conv.id),
        parse_mode="Markdown"
    )


@router.message(F.text == "ℹ️ Помощь")
async def btn_help(message: Message) -> None:
    """Показать помощь"""
    await show_help(message)


async def show_help(message: Message) -> None:
    """Выводит справку"""
    user_id = message.from_user.id
    current_model = conversation_manager.get_user_model(user_id)
    model_name = AVAILABLE_MODELS.get(current_model, current_model)
    
    help_text = f"""📖 **Справка**

**Команды:**
• `/start` — начать работу
• `/help` — показать справку

**Меню:**
• 📝 **Новая беседа** — создать новую беседу
• 📂 **Мои беседы** — список всех бесед
• 🤖 **Модель** — сменить модель AI
• 🗑 **Очистить** — очистить историю
• ℹ️ **Помощь** — эта справка

**Доступные модели:**
• ⚡ GPT-5 Nano — быстрая
• 🔹 GPT-5 Mini — баланс
• 🔷 GPT-5.2 — умная
• 💎 GPT-5.2 Pro — максимум

**Текущая модель:** {model_name}

**Возможности:**
• Веду несколько бесед с отдельной историей
• Анализирую фото (отправь картинку)
• Читаю PDF и DOCX файлы"""
    
    await message.answer(help_text, parse_mode="Markdown")


# ============== CALLBACK HANDLERS ==============

@router.callback_query(F.data == "new_conversation")
async def callback_new_conversation(callback: CallbackQuery) -> None:
    """Создание новой беседы через inline кнопку"""
    user_id = callback.from_user.id
    conv = conversation_manager.create_conversation(user_id)
    
    await callback.message.edit_text(
        f"✅ Создана новая беседа: **{conv.title}**\n\n"
        "Напиши мне что-нибудь!",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "list_conversations")
async def callback_list_conversations(callback: CallbackQuery) -> None:
    """Показать список бесед"""
    user_id = callback.from_user.id
    
    conversations = conversation_manager.get_conversations(user_id)
    active = conversation_manager.get_active_conversation(user_id)
    active_id = active.id if active else None
    
    text = f"📂 **Твои беседы** ({len(conversations)}):\n\n"
    text += "Выбери беседу или создай новую:"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_conversations_keyboard(conversations, active_id),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("select_conv:"))
async def callback_select_conversation(callback: CallbackQuery) -> None:
    """Выбор беседы"""
    user_id = callback.from_user.id
    conv_id = callback.data.split(":")[1]
    
    conv = conversation_manager.set_active_conversation(user_id, conv_id)
    
    if conv:
        await callback.message.edit_text(
            f"📝 **{conv.title}**\n\n"
            f"Сообщений в истории: {len(conv.messages)}\n\n"
            "Что хочешь сделать?",
            reply_markup=get_conversation_actions_keyboard(conv_id),
            parse_mode="Markdown"
        )
    else:
        await callback.answer("❌ Беседа не найдена", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data.startswith("select_model:"))
async def callback_select_model(callback: CallbackQuery) -> None:
    """Выбор модели"""
    user_id = callback.from_user.id
    model_id = callback.data.split(":")[1]
    
    if model_id in AVAILABLE_MODELS:
        conversation_manager.set_user_model(user_id, model_id)
        model_name = AVAILABLE_MODELS[model_id]
        
        await callback.message.edit_text(
            f"✅ Модель изменена на: **{model_name}**\n\n"
            "Новые сообщения будут обрабатываться этой моделью.",
            parse_mode="Markdown"
        )
        await callback.answer(f"Выбрана модель: {model_id}")
    else:
        await callback.answer("❌ Модель не найдена", show_alert=True)


@router.callback_query(F.data.startswith("rename_conv:"))
async def callback_rename_conversation(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать переименование беседы"""
    conv_id = callback.data.split(":")[1]
    
    await state.set_state(BotStates.waiting_for_rename)
    await state.update_data(conv_id=conv_id)
    
    await callback.message.edit_text(
        "✏️ Введи новое название для беседы:",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_action")
async def callback_cancel_action(callback: CallbackQuery, state: FSMContext) -> None:
    """Отмена действия"""
    await state.clear()
    
    user_id = callback.from_user.id
    conversations = conversation_manager.get_conversations(user_id)
    active = conversation_manager.get_active_conversation(user_id)
    active_id = active.id if active else None
    
    await callback.message.edit_text(
        "❌ Действие отменено.\n\n📂 Твои беседы:",
        reply_markup=get_conversations_keyboard(conversations, active_id)
    )
    await callback.answer()


@router.message(BotStates.waiting_for_rename)
async def process_rename(message: Message, state: FSMContext) -> None:
    """Обработка нового названия беседы"""
    user_id = message.from_user.id
    data = await state.get_data()
    conv_id = data.get("conv_id")
    
    new_title = message.text.strip()[:50]  # Ограничиваем длину
    
    if conversation_manager.rename_conversation(user_id, conv_id, new_title):
        await message.answer(f"✅ Беседа переименована в: **{new_title}**", parse_mode="Markdown")
    else:
        await message.answer("❌ Не удалось переименовать беседу.")
    
    await state.clear()


@router.callback_query(F.data.startswith("clear_conv:"))
async def callback_clear_conversation(callback: CallbackQuery) -> None:
    """Запрос на очистку беседы"""
    conv_id = callback.data.split(":")[1]
    
    await callback.message.edit_text(
        "🧹 Очистить всю историю этой беседы?\n\n"
        "⚠️ Все сообщения будут удалены!",
        reply_markup=get_confirm_clear_keyboard(conv_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_clear:"))
async def callback_confirm_clear(callback: CallbackQuery) -> None:
    """Подтверждение очистки беседы"""
    user_id = callback.from_user.id
    conv_id = callback.data.split(":")[1]
    
    if conversation_manager.clear_conversation(user_id, conv_id):
        await callback.message.edit_text("✅ История беседы очищена!")
    else:
        await callback.message.edit_text("❌ Не удалось очистить беседу.")
    
    await callback.answer()


@router.callback_query(F.data.startswith("delete_conv:"))
async def callback_delete_conversation(callback: CallbackQuery) -> None:
    """Запрос на удаление беседы"""
    conv_id = callback.data.split(":")[1]
    
    await callback.message.edit_text(
        "🗑 Удалить эту беседу?\n\n"
        "⚠️ Это действие нельзя отменить!",
        reply_markup=get_confirm_delete_keyboard(conv_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete:"))
async def callback_confirm_delete(callback: CallbackQuery) -> None:
    """Подтверждение удаления беседы"""
    user_id = callback.from_user.id
    conv_id = callback.data.split(":")[1]
    
    if conversation_manager.delete_conversation(user_id, conv_id):
        # Создаём новую беседу если удалили последнюю
        if not conversation_manager.get_conversations(user_id):
            conversation_manager.create_conversation(user_id, "Новая беседа")
        
        await callback.message.edit_text("✅ Беседа удалена!")
    else:
        await callback.message.edit_text("❌ Не удалось удалить беседу.")
    
    await callback.answer()


# ============== ОБРАБОТЧИКИ КОНТЕНТА ==============

import re
from aiogram.enums import ParseMode


def convert_markdown_to_html(text: str) -> str:
    """
    Конвертирует Markdown в HTML для Telegram.
    Поддерживает: жирный, курсив, код, блоки кода.
    """
    # Сначала обрабатываем блоки кода (чтобы не затронуть их содержимое)
    code_blocks = []
    
    def save_code_block(match):
        lang = match.group(1) or ""
        code = match.group(2)
        # Экранируем HTML в коде
        code = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if lang:
            code_blocks.append(f'<pre><code class="language-{lang}">{code}</code></pre>')
        else:
            code_blocks.append(f'<pre><code>{code}</code></pre>')
        return f"<<<CODE_BLOCK_{len(code_blocks) - 1}>>>"
    
    # Блоки кода ```language\ncode```
    text = re.sub(r'```(\w*)\n?(.*?)```', save_code_block, text, flags=re.DOTALL)
    
    # Инлайн код `code`
    inline_codes = []
    def save_inline_code(match):
        code = match.group(1)
        code = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        inline_codes.append(f'<code>{code}</code>')
        return f"<<<INLINE_CODE_{len(inline_codes) - 1}>>>"
    
    text = re.sub(r'`([^`]+)`', save_inline_code, text)
    
    # Экранируем HTML в остальном тексте
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    # Жирный текст **text** или *text*
    text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'(?<![*\w])\*([^*\n]+)\*(?![*\w])', r'<b>\1</b>', text)
    
    # Курсив _text_
    text = re.sub(r'(?<![_\w])_([^_\n]+)_(?![_\w])', r'<i>\1</i>', text)
    
    # Зачёркнутый ~text~
    text = re.sub(r'~([^~]+)~', r'<s>\1</s>', text)
    
    # Спойлер ||text||
    text = re.sub(r'\|\|([^|]+)\|\|', r'<tg-spoiler>\1</tg-spoiler>', text)
    
    # Подчёркнутый __text__
    text = re.sub(r'__([^_]+)__', r'<u>\1</u>', text)
    
    # Восстанавливаем блоки кода
    for i, block in enumerate(code_blocks):
        text = text.replace(f"&lt;&lt;&lt;CODE_BLOCK_{i}&gt;&gt;&gt;", block)
    
    for i, code in enumerate(inline_codes):
        text = text.replace(f"&lt;&lt;&lt;INLINE_CODE_{i}&gt;&gt;&gt;", code)
    
    return text


async def send_response(message: Message, response: str) -> None:
    """Отправляет ответ с HTML форматированием, если слишком длинный — в файле"""
    if len(response) <= MAX_TELEGRAM_MESSAGE_LENGTH:
        try:
            # Пробуем отправить с HTML форматированием
            html_response = convert_markdown_to_html(response)
            await message.reply(html_response, parse_mode=ParseMode.HTML)
        except Exception as e:
            # Если форматирование сломалось, отправляем без него
            logger.warning(f"HTML parse error: {e}")
            try:
                await message.reply(response)
            except Exception:
                # Если и так не получилось, отправляем файлом
                file_bytes = response.encode('utf-8')
                file = BufferedInputFile(file_bytes, filename="response.txt")
                await message.reply_document(
                    document=file,
                    caption="📄 Не удалось отформатировать, отправляю файлом."
                )
    else:
        # Отправляем как файл
        file_bytes = response.encode('utf-8')
        file = BufferedInputFile(file_bytes, filename="response.txt")
        await message.reply_document(
            document=file,
            caption="📄 Ответ слишком длинный, отправляю файлом."
        )


@router.message(F.photo)
async def handle_photo(message: Message, bot: Bot) -> None:
    """Обработчик фотографий"""
    user_id = message.from_user.id
    
    # Получаем фото максимального размера
    photo = message.photo[-1]
    
    # Показываем индикатор
    await bot.send_chat_action(message.chat.id, "typing")
    
    # Скачиваем фото
    file = await bot.get_file(photo.file_id)
    file_data = await bot.download_file(file.file_path)
    image_bytes = file_data.read()
    
    # Проверяем режим редактирования
    if conversation_manager.is_edit_mode(user_id):
        # Сохраняем изображение для редактирования
        conversation_manager.set_user_image(user_id, image_bytes)
        
        # Если есть подпись - сразу редактируем
        if message.caption:
            await bot.send_chat_action(message.chat.id, "upload_photo")
            status_msg = await message.reply("🎨 Редактирую изображение...")
            
            result_url, result_text = await edit_image_with_dalle(image_bytes, message.caption)
            
            if result_url:
                try:
                    # Если это data URL, декодируем
                    if result_url.startswith("data:"):
                        import base64
                        b64_data = result_url.split(",")[1]
                        edited_bytes = base64.b64decode(b64_data)
                    else:
                        # Скачиваем по URL
                        import aiohttp
                        async with aiohttp.ClientSession() as session:
                            async with session.get(result_url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                                edited_bytes = await resp.read()
                    
                    # Сохраняем отредактированное изображение как новое
                    conversation_manager.set_user_image(user_id, edited_bytes)
                    
                    result_photo = BufferedInputFile(edited_bytes, filename="edited.png")
                    await status_msg.delete()
                    await message.reply_photo(
                        photo=result_photo,
                        caption=f"✅ Готово! Отредактировано по запросу:\n{message.caption[:200]}"
                    )
                except Exception as e:
                    logger.error(f"Error sending edited image: {e}")
                    await status_msg.edit_text(f"❌ Ошибка: {str(e)[:100]}")
            else:
                await status_msg.edit_text(result_text or "❌ Ошибка редактирования")
        else:
            await message.reply(
                "✅ Изображение сохранено!\n\n"
                "Теперь напиши что нужно изменить, например:\n"
                "• добавь солнечные очки\n"
                "• сделай фон синим\n"
                "• добавь шляпу"
            )
        return
    
    # Обычный режим - анализ изображения
    image_base64 = encode_image_to_base64(image_bytes)
    
    # Определяем MIME-тип
    mime_type = "image/jpeg"
    if file.file_path and file.file_path.lower().endswith('.png'):
        mime_type = "image/png"
    
    # Получаем подпись (если есть)
    user_text = message.caption or "Опиши это изображение подробно."
    
    # Добавляем в историю
    conversation_manager.add_message(user_id, "user", f"[Изображение] {user_text}", MAX_HISTORY_MESSAGES)
    
    # Получаем историю и модель
    messages = conversation_manager.get_messages_for_api(user_id, SYSTEM_PROMPT)
    model = conversation_manager.get_user_model(user_id)
    
    # Получаем ответ (для изображений используется vision модель)
    response = await get_chat_response(messages, model=model, image_base64=image_base64, image_mime_type=mime_type)
    
    # Сохраняем ответ
    conversation_manager.add_message(user_id, "assistant", response, MAX_HISTORY_MESSAGES)
    
    # Отправляем
    await send_response(message, response)


@router.message(F.document)
async def handle_document(message: Message, bot: Bot) -> None:
    """Обработчик документов (PDF, DOCX, TXT)"""
    user_id = message.from_user.id
    document = message.document
    file_name = document.file_name or "document"
    
    # Проверяем формат файла
    supported_formats = ('.pdf', '.docx', '.txt')
    if not any(file_name.lower().endswith(ext) for ext in supported_formats):
        await message.reply(
            "⚠️ Поддерживаются форматы: PDF, DOCX, TXT\n"
            "Отправь документ в одном из этих форматов."
        )
        return
    
    # Показываем индикатор загрузки
    status_msg = await message.reply("📥 Загружаю файл...")
    
    # Скачиваем документ
    file = await bot.get_file(document.file_id)
    file_data = await bot.download_file(file.file_path)
    file_bytes = file_data.read()
    
    # Обновляем статус
    await status_msg.edit_text("⚙️ Обрабатываю файл...")
    
    # Извлекаем текст
    extracted_text = await extract_text_from_file(file_bytes, file_name)
    
    if not extracted_text:
        await status_msg.edit_text("❌ Не удалось извлечь текст из документа.")
        return
    
    # Обрезаем текст, если он слишком длинный
    max_chars = 15000
    if len(extracted_text) > max_chars:
        extracted_text = extracted_text[:max_chars] + "\n\n[... текст обрезан ...]"
    
    # Анимированный лоадер для ответа
    await status_msg.edit_text("Ищу ответ на Ваш вопрос...")
    
    # Формируем запрос
    user_question = message.caption or "Сделай краткое резюме этого документа."
    prompt = f"Содержимое документа '{file_name}':\n\n{extracted_text}\n\nВопрос: {user_question}"
    
    # Добавляем в историю
    conversation_manager.add_message(user_id, "user", f"[Документ: {file_name}] {user_question}", MAX_HISTORY_MESSAGES)
    
    # Показываем индикатор
    await bot.send_chat_action(message.chat.id, "typing")
    
    # Получаем историю и модель
    messages = conversation_manager.get_messages_for_api(user_id, SYSTEM_PROMPT)
    messages[-1]["content"] = prompt  # Заменяем на полный промпт с документом
    model = conversation_manager.get_user_model(user_id)
    
    # Получаем ответ
    response = await get_chat_response(messages, model=model)
    
    # Сохраняем ответ
    conversation_manager.add_message(user_id, "assistant", response, MAX_HISTORY_MESSAGES)
    
    # Редактируем сообщение с ответом
    await send_response_edit(status_msg, message, response)


async def send_response_edit(status_msg: Message, original_msg: Message, response: str) -> None:
    """Редактирует статусное сообщение с финальным ответом"""
    from aiogram.enums import ParseMode
    
    if len(response) <= MAX_TELEGRAM_MESSAGE_LENGTH:
        try:
            html_response = convert_markdown_to_html(response)
            await status_msg.edit_text(html_response, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.warning(f"HTML edit error: {e}")
            try:
                await status_msg.edit_text(response)
            except Exception:
                # Если редактирование не сработало, отправляем как файл
                await status_msg.delete()
                file_bytes = response.encode('utf-8')
                file = BufferedInputFile(file_bytes, filename="response.txt")
                await original_msg.reply_document(
                    document=file,
                    caption="📄 Ответ слишком сложный, отправляю файлом."
                )
    else:
        # Отправляем как файл
        await status_msg.delete()
        file_bytes = response.encode('utf-8')
        file = BufferedInputFile(file_bytes, filename="response.txt")
        await original_msg.reply_document(
            document=file,
            caption="📄 Ответ слишком длинный, отправляю файлом."
        )


@router.message(F.voice)
async def handle_voice(message: Message, bot: Bot) -> None:
    """Обработчик голосовых сообщений"""
    user_id = message.from_user.id
    
    # Статус загрузки
    status_msg = await message.reply("🎤 Загружаю голосовое сообщение...")
    
    # Скачиваем голосовое
    file = await bot.get_file(message.voice.file_id)
    file_data = await bot.download_file(file.file_path)
    audio_bytes = file_data.read()
    
    # Транскрибируем
    await status_msg.edit_text("🔊 Распознаю речь...")
    
    transcribed_text = await transcribe_audio(audio_bytes, "ogg")
    
    if transcribed_text.startswith("❌"):
        await status_msg.edit_text(transcribed_text)
        return
    
    # Показываем распознанный текст
    await status_msg.edit_text(f"📝 Распознано: _{transcribed_text}_\n\nИщу ответ на Ваш вопрос...", parse_mode="Markdown")
    
    await bot.send_chat_action(message.chat.id, "typing")
    
    # Добавляем в историю
    conversation_manager.add_message(user_id, "user", transcribed_text, MAX_HISTORY_MESSAGES)
    
    # Получаем историю и модель
    messages = conversation_manager.get_messages_for_api(user_id, SYSTEM_PROMPT)
    model = conversation_manager.get_user_model(user_id)
    
    # Получаем ответ
    response = await get_chat_response(messages, model=model)
    
    # Сохраняем ответ
    conversation_manager.add_message(user_id, "assistant", response, MAX_HISTORY_MESSAGES)
    
    # Редактируем сообщение с ответом
    await send_response_edit(status_msg, message, response)


@router.message(F.text)
async def handle_text(message: Message, bot: Bot) -> None:
    """Обработчик текстовых сообщений"""
    user_id = message.from_user.id
    user_text = message.text
    
    # Игнорируем пустые сообщения
    if not user_text or not user_text.strip():
        return
    
    # Проверяем режим редактирования
    if conversation_manager.is_edit_mode(user_id):
        saved_image = conversation_manager.get_user_image(user_id)
        
        if saved_image:
            # Редактируем сохранённое изображение
            await bot.send_chat_action(message.chat.id, "upload_photo")
            status_msg = await message.reply("🎨 Редактирую изображение...")
            
            result_url, result_text = await edit_image_with_dalle(saved_image, user_text)
            
            if result_url:
                try:
                    # Если это data URL, декодируем
                    if result_url.startswith("data:"):
                        import base64
                        b64_data = result_url.split(",")[1]
                        edited_bytes = base64.b64decode(b64_data)
                    else:
                        # Скачиваем по URL
                        import aiohttp
                        async with aiohttp.ClientSession() as session:
                            async with session.get(result_url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                                edited_bytes = await resp.read()
                    
                    # Сохраняем отредактированное изображение как новое
                    conversation_manager.set_user_image(user_id, edited_bytes)
                    
                    result_photo = BufferedInputFile(edited_bytes, filename="edited.png")
                    await status_msg.delete()
                    await message.reply_photo(
                        photo=result_photo,
                        caption=f"✅ Готово: {user_text[:200]}\n\n💡 Можешь продолжить редактировать или отправить новое фото."
                    )
                except Exception as e:
                    logger.error(f"Error sending edited image: {e}")
                    try:
                        await status_msg.edit_text(f"❌ Ошибка: {str(e)[:100]}")
                    except Exception:
                        await message.reply(f"❌ Ошибка: {str(e)[:100]}")
            else:
                try:
                    await status_msg.edit_text(result_text or "❌ Ошибка редактирования")
                except Exception:
                    await message.reply(result_text or "❌ Ошибка редактирования")
            return
        else:
            await message.reply(
                "📸 Сначала отправь фото для редактирования!\n\n"
                "Отправь изображение, которое хочешь редактировать."
            )
            return
    
    # Проверяем DALL-E режим
    if conversation_manager.is_dalle_mode(user_id):
        await bot.send_chat_action(message.chat.id, "upload_photo")
        
        # Проверяем, есть ли сохранённое изображение
        saved_dalle_image = conversation_manager.get_dalle_image(user_id)
        
        if saved_dalle_image:
            # Редактируем существующее изображение
            status_msg = await message.reply("🎨 Редактирую изображение...")
            
            result_url, result_text = await edit_image_with_dalle(saved_dalle_image, user_text)
            
            if result_url:
                try:
                    if result_url.startswith("data:"):
                        import base64
                        b64_data = result_url.split(",")[1]
                        edited_bytes = base64.b64decode(b64_data)
                    else:
                        import aiohttp
                        async with aiohttp.ClientSession() as session:
                            async with session.get(result_url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                                edited_bytes = await resp.read()
                    
                    # Сохраняем новое изображение
                    conversation_manager.set_dalle_image(user_id, edited_bytes)
                    
                    result_photo = BufferedInputFile(edited_bytes, filename="dalle_edited.png")
                    await status_msg.delete()
                    await message.reply_photo(
                        photo=result_photo,
                        caption=f"✅ {user_text[:200]}\n\n💡 Продолжай редактировать или напиши новый промпт для новой картинки"
                    )
                except Exception as e:
                    logger.error(f"Error sending edited DALL-E image: {e}")
                    await status_msg.edit_text(f"❌ Ошибка: {str(e)[:100]}")
            else:
                await status_msg.edit_text(result_text or "❌ Ошибка редактирования")
        else:
            # Генерируем новое изображение
            status_msg = await message.reply("🖼 Генерирую изображение...")
            
            image_url, result = await generate_image(user_text)
            
            if image_url:
                try:
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.get(image_url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                            if resp.status == 200:
                                image_data = await resp.read()
                            else:
                                raise Exception(f"HTTP {resp.status}")
                    
                    # Сохраняем для последующего редактирования
                    conversation_manager.set_dalle_image(user_id, image_data)
                    
                    photo = BufferedInputFile(image_data, filename="dalle_generated.png")
                    
                    caption = f"🖼 {user_text[:150]}"
                    if result and result != user_text:
                        caption += f"\n\n📝 Промпт DALL-E: {result[:150]}"
                    caption += "\n\n💡 Напиши что изменить, чтобы отредактировать"
                    
                    await status_msg.delete()
                    await message.reply_photo(photo=photo, caption=caption)
                    
                except Exception as e:
                    logger.error(f"Error sending DALL-E image: {e}")
                    await status_msg.edit_text(f"❌ Ошибка: {str(e)[:100]}")
            else:
                await status_msg.edit_text(result or "❌ Не удалось сгенерировать")
        return
    
    # Обычный текстовый запрос - показываем анимированный статус
    status_msg = await message.reply("Ищу ответ на Ваш вопрос...")
    
    await bot.send_chat_action(message.chat.id, "typing")
    
    # Добавляем сообщение в историю
    conversation_manager.add_message(user_id, "user", user_text, MAX_HISTORY_MESSAGES)
    
    # Получаем историю и модель пользователя
    messages = conversation_manager.get_messages_for_api(user_id, SYSTEM_PROMPT)
    model = conversation_manager.get_user_model(user_id)
    
    # Получаем ответ
    response = await get_chat_response(messages, model=model)
    
    # Сохраняем ответ в историю
    conversation_manager.add_message(user_id, "assistant", response, MAX_HISTORY_MESSAGES)
    
    # Редактируем статусное сообщение с ответом
    await send_response_edit(status_msg, message, response)


