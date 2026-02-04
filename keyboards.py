"""
Клавиатуры и меню бота
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from typing import List, Dict

from conversations import Conversation
from config import AVAILABLE_MODELS


def get_main_menu_keyboard(is_dalle_mode: bool = False, is_edit_mode: bool = False, is_template_mode: bool = False) -> ReplyKeyboardMarkup:
    """Главное меню с кнопками. Меняет текст кнопок в зависимости от режима."""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📝 Новая беседа"),
        KeyboardButton(text="📂 Мои беседы")
    )
    
    # Динамические кнопки режимов
    dalle_text = "❌ Выйти из DALL-E" if is_dalle_mode else "🖼 DALL-E"
    editor_text = "❌ Выйти из редактора" if is_edit_mode else "🎨 Редактор"
    template_text = "❌ Выйти из шаблона" if is_template_mode else "📄 Шаблоны"
    
    builder.row(
        KeyboardButton(text="🤖 Модель"),
        KeyboardButton(text=dalle_text)
    )
    builder.row(
        KeyboardButton(text=editor_text),
        KeyboardButton(text=template_text)
    )
    builder.row(
        KeyboardButton(text="✨ Промпты"),
        KeyboardButton(text="🗑 Очистить")
    )
    builder.row(
        KeyboardButton(text="ℹ️ Помощь")
    )
    return builder.as_markup(resize_keyboard=True)


def get_conversations_keyboard(conversations: List[Conversation], active_id: str = None) -> InlineKeyboardMarkup:
    """Клавиатура со списком бесед"""
    builder = InlineKeyboardBuilder()
    
    if not conversations:
        builder.row(InlineKeyboardButton(
            text="📝 Создать первую беседу",
            callback_data="new_conversation"
        ))
    else:
        for conv in conversations:
            # Отмечаем активную беседу
            prefix = "✅ " if conv.id == active_id else ""
            msg_count = len(conv.messages)
            
            builder.row(InlineKeyboardButton(
                text=f"{prefix}{conv.title} ({msg_count} сообщ.)",
                callback_data=f"select_conv:{conv.id}"
            ))
        
        builder.row(InlineKeyboardButton(
            text="➕ Новая беседа",
            callback_data="new_conversation"
        ))
    
    return builder.as_markup()


def get_conversation_actions_keyboard(conv_id: str) -> InlineKeyboardMarkup:
    """Клавиатура действий с беседой"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✏️ Переименовать", callback_data=f"rename_conv:{conv_id}"),
        InlineKeyboardButton(text="🧹 Очистить", callback_data=f"clear_conv:{conv_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_conv:{conv_id}")
    )
    builder.row(
        InlineKeyboardButton(text="« Назад к списку", callback_data="list_conversations")
    )
    
    return builder.as_markup()


def get_confirm_delete_keyboard(conv_id: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete:{conv_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="list_conversations")
    )
    
    return builder.as_markup()


def get_confirm_clear_keyboard(conv_id: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения очистки"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Да, очистить", callback_data=f"confirm_clear:{conv_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="list_conversations")
    )
    
    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура отмены"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action"))
    return builder.as_markup()


def get_models_keyboard(current_model: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора модели"""
    builder = InlineKeyboardBuilder()
    
    for model_id, model_name in AVAILABLE_MODELS.items():
        # Отмечаем текущую модель
        prefix = "✅ " if model_id == current_model else ""
        builder.row(InlineKeyboardButton(
            text=f"{prefix}{model_name}",
            callback_data=f"select_model:{model_id}"
        ))
    
    return builder.as_markup()


def get_custom_prompts_keyboard(prompts: list, active_prompt: str = None) -> InlineKeyboardMarkup:
    """Клавиатура управления кастомными промптами"""
    builder = InlineKeyboardBuilder()
    
    if prompts:
        for i, prompt in enumerate(prompts):
            # Обрезаем длинные промпты для отображения
            short_prompt = prompt[:30] + "..." if len(prompt) > 30 else prompt
            is_active = prompt == active_prompt
            prefix = "✅ " if is_active else ""
            
            builder.row(InlineKeyboardButton(
                text=f"{prefix}Промпт {i+1}: {short_prompt}",
                callback_data=f"toggle_prompt:{i}"
            ))
        
        # Кнопки удаления для каждого промпта
        delete_buttons = []
        for i in range(len(prompts)):
            delete_buttons.append(InlineKeyboardButton(
                text=f"🗑 Удалить {i+1}",
                callback_data=f"delete_prompt:{i}"
            ))
        if delete_buttons:
            builder.row(*delete_buttons)
    else:
        builder.row(InlineKeyboardButton(
            text="📝 Нет сохранённых промптов",
            callback_data="no_action"
        ))
    
    # Кнопка добавления нового промпта (максимум 2)
    builder.row(InlineKeyboardButton(
        text="➕ Добавить промпт" + (" (заменит старый)" if len(prompts) >= 2 else ""),
        callback_data="add_custom_prompt"
    ))
    
    # Кнопка отключения кастомного промпта
    if active_prompt:
        builder.row(InlineKeyboardButton(
            text="🔄 Использовать стандартный промпт",
            callback_data="disable_custom_prompt"
        ))
    
    
    return builder.as_markup()


def get_download_keyboard(response_id: str) -> InlineKeyboardMarkup:
    """Клавиатура для скачивания длинного ответа"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📄 TXT", callback_data=f"dl:txt:{response_id}"),
        InlineKeyboardButton(text="📝 DOCX", callback_data=f"dl:docx:{response_id}")
    )
    
    return builder.as_markup()
