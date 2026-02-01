"""
Менеджер бесед пользователей
Хранит историю сообщений для каждой беседы и настройки пользователя
"""

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime

from config import DEFAULT_MODEL


@dataclass
class Message:
    """Сообщение в беседе"""
    role: str  # 'user' или 'assistant'
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass  
class Conversation:
    """Беседа с историей сообщений"""
    id: str
    title: str
    messages: List[Message] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "messages": [{"role": m.role, "content": m.content, "timestamp": m.timestamp} for m in self.messages],
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Conversation":
        messages = [Message(**m) for m in data.get("messages", [])]
        return cls(
            id=data["id"],
            title=data["title"],
            messages=messages,
            created_at=data.get("created_at", datetime.now().isoformat())
        )


class ConversationManager:
    """Менеджер бесед для всех пользователей"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # user_id -> {conversation_id -> Conversation}
        self._conversations: Dict[int, Dict[str, Conversation]] = {}
        # user_id -> active_conversation_id
        self._active_conversations: Dict[int, str] = {}
        # user_id -> selected_model
        self._user_models: Dict[int, str] = {}
        # user_id -> edit_mode (True/False)
        self._edit_mode: Dict[int, bool] = {}
        # user_id -> stored image bytes for editing
        self._user_images: Dict[int, bytes] = {}
        
    def _get_user_file(self, user_id: int) -> str:
        return os.path.join(self.data_dir, f"user_{user_id}.json")
    
    def _load_user_data(self, user_id: int) -> None:
        """Загружает данные пользователя из файла"""
        if user_id in self._conversations:
            return
            
        file_path = self._get_user_file(user_id)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                self._conversations[user_id] = {}
                for conv_data in data.get("conversations", []):
                    conv = Conversation.from_dict(conv_data)
                    self._conversations[user_id][conv.id] = conv
                    
                self._active_conversations[user_id] = data.get("active_conversation_id")
                self._user_models[user_id] = data.get("selected_model", DEFAULT_MODEL)
                # Загружаем кастомные промпты
                if not hasattr(self, '_custom_prompts'):
                    self._custom_prompts = {}
                self._custom_prompts[user_id] = data.get("custom_prompts", [])
            except Exception:
                self._conversations[user_id] = {}
                self._active_conversations[user_id] = None
                self._user_models[user_id] = DEFAULT_MODEL
        else:
            self._conversations[user_id] = {}
            self._active_conversations[user_id] = None
            self._user_models[user_id] = DEFAULT_MODEL
    
    def _save_user_data(self, user_id: int) -> None:
        """Сохраняет данные пользователя в файл"""
        file_path = self._get_user_file(user_id)
        data = {
            "conversations": [conv.to_dict() for conv in self._conversations.get(user_id, {}).values()],
            "active_conversation_id": self._active_conversations.get(user_id),
            "selected_model": self._user_models.get(user_id, DEFAULT_MODEL)
        }
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    # ===== Методы для работы с моделями =====
    
    def get_user_model(self, user_id: int) -> str:
        """Получает выбранную модель пользователя"""
        self._load_user_data(user_id)
        return self._user_models.get(user_id, DEFAULT_MODEL)
    
    def set_user_model(self, user_id: int, model: str) -> None:
        """Устанавливает модель для пользователя"""
        self._load_user_data(user_id)
        self._user_models[user_id] = model
        self._save_user_data(user_id)
    
    # ===== Методы для режима редактирования =====
    
    def is_edit_mode(self, user_id: int) -> bool:
        """Проверяет, включён ли режим редактирования"""
        return self._edit_mode.get(user_id, False)
    
    def set_edit_mode(self, user_id: int, enabled: bool) -> None:
        """Включает/выключает режим редактирования"""
        self._edit_mode[user_id] = enabled
        if not enabled:
            # При выключении режима очищаем сохранённое изображение
            self._user_images.pop(user_id, None)
    
    def get_user_image(self, user_id: int) -> Optional[bytes]:
        """Получает сохранённое изображение пользователя"""
        return self._user_images.get(user_id)
    
    def set_user_image(self, user_id: int, image_bytes: bytes) -> None:
        """Сохраняет изображение пользователя для редактирования"""
        self._user_images[user_id] = image_bytes
    
    def clear_user_image(self, user_id: int) -> None:
        """Очищает сохранённое изображение"""
        self._user_images.pop(user_id, None)
    
    # ===== Методы для DALL-E режима =====
    
    def is_dalle_mode(self, user_id: int) -> bool:
        """Проверяет, включён ли DALL-E режим"""
        return getattr(self, '_dalle_mode', {}).get(user_id, False)
    
    def set_dalle_mode(self, user_id: int, enabled: bool) -> None:
        """Включает/выключает DALL-E режим"""
        if not hasattr(self, '_dalle_mode'):
            self._dalle_mode = {}
        if not hasattr(self, '_dalle_images'):
            self._dalle_images = {}
        
        self._dalle_mode[user_id] = enabled
        if not enabled:
            self._dalle_images.pop(user_id, None)
    
    def get_dalle_image(self, user_id: int) -> Optional[bytes]:
        """Получает последнее сгенерированное DALL-E изображение"""
        if not hasattr(self, '_dalle_images'):
            self._dalle_images = {}
        return self._dalle_images.get(user_id)
    
    def set_dalle_image(self, user_id: int, image_bytes: bytes) -> None:
        """Сохраняет сгенерированное изображение"""
        if not hasattr(self, '_dalle_images'):
            self._dalle_images = {}
        self._dalle_images[user_id] = image_bytes

    # ===== Методы для режима шаблонов документов =====
    
    def is_template_mode(self, user_id: int) -> bool:
        """Проверяет, включён ли режим шаблонов"""
        if not hasattr(self, '_template_mode'):
            self._template_mode = {}
        return self._template_mode.get(user_id, False)
    
    def set_template_mode(self, user_id: int, enabled: bool) -> None:
        """Включает/выключает режим шаблонов"""
        if not hasattr(self, '_template_mode'):
            self._template_mode = {}
        if not hasattr(self, '_template_docs'):
            self._template_docs = {}
        if not hasattr(self, '_template_names'):
            self._template_names = {}
        
        self._template_mode[user_id] = enabled
        if not enabled:
            self._template_docs.pop(user_id, None)
            self._template_names.pop(user_id, None)
    
    def get_template_doc(self, user_id: int) -> Optional[bytes]:
        """Получает сохранённый шаблон документа"""
        if not hasattr(self, '_template_docs'):
            self._template_docs = {}
        return self._template_docs.get(user_id)
    
    def get_template_name(self, user_id: int) -> Optional[str]:
        """Получает имя сохранённого шаблона"""
        if not hasattr(self, '_template_names'):
            self._template_names = {}
        return self._template_names.get(user_id)
    
    def set_template_doc(self, user_id: int, doc_bytes: bytes, filename: str) -> None:
        """Сохраняет шаблон документа"""
        if not hasattr(self, '_template_docs'):
            self._template_docs = {}
        if not hasattr(self, '_template_names'):
            self._template_names = {}
        self._template_docs[user_id] = doc_bytes
        self._template_names[user_id] = filename

    # ===== Методы для кастомных промптов =====
    
    def get_custom_prompts(self, user_id: int) -> List[str]:
        """Получает список кастомных промптов пользователя (максимум 2)"""
        self._load_user_data(user_id)
        if not hasattr(self, '_custom_prompts'):
            self._custom_prompts = {}
        return self._custom_prompts.get(user_id, [])
    
    def add_custom_prompt(self, user_id: int, prompt: str) -> int:
        """
        Добавляет кастомный промпт пользователю.
        Если уже 2 промпта, старейший заменяется на новый.
        Возвращает индекс добавленного/заменённого промпта (1 или 2).
        """
        self._load_user_data(user_id)
        if not hasattr(self, '_custom_prompts'):
            self._custom_prompts = {}
        
        if user_id not in self._custom_prompts:
            self._custom_prompts[user_id] = []
        
        prompts = self._custom_prompts[user_id]
        
        if len(prompts) < 2:
            # Есть место - просто добавляем
            prompts.append(prompt)
            self._save_custom_prompts(user_id)
            return len(prompts)
        else:
            # Все слоты заняты - заменяем самый старый (первый)
            prompts.pop(0)
            prompts.append(prompt)
            self._save_custom_prompts(user_id)
            return 2  # Новый всегда становится вторым
    
    def get_active_custom_prompt(self, user_id: int) -> Optional[str]:
        """Получает активный кастомный промпт (если выбран)"""
        if not hasattr(self, '_active_custom_prompt'):
            self._active_custom_prompt = {}
        return self._active_custom_prompt.get(user_id)
    
    def set_active_custom_prompt(self, user_id: int, index: Optional[int]) -> None:
        """Устанавливает активный кастомный промпт по индексу (0, 1) или None для отключения"""
        if not hasattr(self, '_active_custom_prompt'):
            self._active_custom_prompt = {}
        
        if index is None:
            self._active_custom_prompt.pop(user_id, None)
        else:
            prompts = self.get_custom_prompts(user_id)
            if 0 <= index < len(prompts):
                self._active_custom_prompt[user_id] = prompts[index]
    
    def delete_custom_prompt(self, user_id: int, index: int) -> bool:
        """Удаляет кастомный промпт по индексу (0 или 1)"""
        if not hasattr(self, '_custom_prompts'):
            self._custom_prompts = {}
        
        prompts = self._custom_prompts.get(user_id, [])
        if 0 <= index < len(prompts):
            prompts.pop(index)
            # Если удалили активный промпт, сбрасываем
            if hasattr(self, '_active_custom_prompt') and user_id in self._active_custom_prompt:
                if self._active_custom_prompt[user_id] not in prompts:
                    self._active_custom_prompt.pop(user_id, None)
            self._save_custom_prompts(user_id)
            return True
        return False
    
    def _save_custom_prompts(self, user_id: int) -> None:
        """Сохраняет кастомные промпты в файл пользователя"""
        # Загружаем текущие данные и добавляем промпты
        file_path = self._get_user_file(user_id)
        data = {}
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                pass
        
        data["custom_prompts"] = self._custom_prompts.get(user_id, [])
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    
    # ===== Методы для работы с беседами =====
    
    def get_conversations(self, user_id: int) -> List[Conversation]:
        """Получает список всех бесед пользователя"""
        self._load_user_data(user_id)
        return list(self._conversations.get(user_id, {}).values())
    
    def get_active_conversation(self, user_id: int) -> Optional[Conversation]:
        """Получает активную беседу пользователя"""
        self._load_user_data(user_id)
        active_id = self._active_conversations.get(user_id)
        if active_id and user_id in self._conversations:
            return self._conversations[user_id].get(active_id)
        return None
    
    def create_conversation(self, user_id: int, title: str = None) -> Conversation:
        """Создаёт новую беседу"""
        self._load_user_data(user_id)
        
        # Генерируем ID
        conv_id = f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Генерируем название
        if not title:
            count = len(self._conversations.get(user_id, {})) + 1
            title = f"Беседа #{count}"
        
        conversation = Conversation(id=conv_id, title=title)
        
        if user_id not in self._conversations:
            self._conversations[user_id] = {}
        
        self._conversations[user_id][conv_id] = conversation
        self._active_conversations[user_id] = conv_id
        
        self._save_user_data(user_id)
        return conversation
    
    def set_active_conversation(self, user_id: int, conv_id: str) -> Optional[Conversation]:
        """Устанавливает активную беседу"""
        self._load_user_data(user_id)
        
        if user_id in self._conversations and conv_id in self._conversations[user_id]:
            self._active_conversations[user_id] = conv_id
            self._save_user_data(user_id)
            return self._conversations[user_id][conv_id]
        return None
    
    def delete_conversation(self, user_id: int, conv_id: str) -> bool:
        """Удаляет беседу"""
        self._load_user_data(user_id)
        
        if user_id in self._conversations and conv_id in self._conversations[user_id]:
            del self._conversations[user_id][conv_id]
            
            # Если удалили активную беседу, сбрасываем
            if self._active_conversations.get(user_id) == conv_id:
                self._active_conversations[user_id] = None
            
            self._save_user_data(user_id)
            return True
        return False
    
    def clear_conversation(self, user_id: int, conv_id: str) -> bool:
        """Очищает историю беседы"""
        self._load_user_data(user_id)
        
        if user_id in self._conversations and conv_id in self._conversations[user_id]:
            self._conversations[user_id][conv_id].messages = []
            self._save_user_data(user_id)
            return True
        return False
    
    def add_message(self, user_id: int, role: str, content: str, max_messages: int = 20) -> None:
        """Добавляет сообщение в активную беседу"""
        self._load_user_data(user_id)
        
        conv = self.get_active_conversation(user_id)
        if not conv:
            conv = self.create_conversation(user_id)
        
        message = Message(role=role, content=content)
        conv.messages.append(message)
        
        # Ограничиваем количество сообщений
        if len(conv.messages) > max_messages:
            conv.messages = conv.messages[-max_messages:]
        
        self._save_user_data(user_id)
    
    def get_messages_for_api(self, user_id: int, system_prompt: str) -> List[dict]:
        """Получает сообщения в формате OpenAI API"""
        conv = self.get_active_conversation(user_id)
        
        messages = [{"role": "system", "content": system_prompt}]
        
        if conv:
            for msg in conv.messages:
                messages.append({"role": msg.role, "content": msg.content})
        
        return messages
    
    def rename_conversation(self, user_id: int, conv_id: str, new_title: str) -> bool:
        """Переименовывает беседу"""
        self._load_user_data(user_id)
        
        if user_id in self._conversations and conv_id in self._conversations[user_id]:
            self._conversations[user_id][conv_id].title = new_title
            self._save_user_data(user_id)
            return True
        return False


# Глобальный экземпляр менеджера
conversation_manager = ConversationManager()
