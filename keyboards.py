"""
Клавиатуры и меню бота
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from typing import List, Dict

from conversations import Conversation
from config import AVAILABLE_MODELS


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню с кнопками"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📝 Новая беседа"),
        KeyboardButton(text="📂 Мои беседы")
    )
    builder.row(
        KeyboardButton(text="🤖 Модель"),
        KeyboardButton(text="🖼 DALL-E")
    )
    builder.row(
        KeyboardButton(text="🎨 Редактор"),
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
