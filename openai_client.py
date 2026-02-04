"""
Клиент для работы с OpenAI API
"""

import base64
import logging
from typing import List, Optional, Tuple

from openai import AsyncOpenAI

from config import (
    OPENAI_API_KEY,
    DEFAULT_MODEL,
    OPENAI_VISION_MODEL,
    IMAGE_MODEL,
    MAX_TOKENS,
    SYSTEM_PROMPT
)


logger = logging.getLogger(__name__)

# Инициализация клиента OpenAI
client = AsyncOpenAI(api_key=OPENAI_API_KEY)


async def transcribe_audio(audio_bytes: bytes, file_format: str = "ogg") -> str:
    """
    Транскрибирует аудио в текст с помощью Whisper.
    
    Args:
        audio_bytes: Байты аудиофайла
        file_format: Формат файла (ogg, mp3, wav и т.д.)
        
    Returns:
        Распознанный текст
    """
    try:
        import io
        
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = f"audio.{file_format}"
        
        response = await client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="ru"
        )
        
        return response.text
    except Exception as e:
        logger.error(f"Whisper error: {e}")
        return f"❌ Ошибка распознавания: {str(e)}"


async def get_chat_response(
    messages: List[dict],
    model: str = None,
    image_base64: Optional[str] = None,
    image_mime_type: str = "image/jpeg"
) -> str:
    """
    Получает ответ от OpenAI.
    
    Args:
        messages: История сообщений в формате OpenAI API
        model: Модель для использования (если None, используется DEFAULT_MODEL)
        image_base64: Base64-закодированное изображение (опционально)
        image_mime_type: MIME-тип изображения
        
    Returns:
        Ответ от модели
    """
    try:
        # Если есть изображение, добавляем его к последнему сообщению
        if image_base64:
            # Модифицируем последнее сообщение пользователя
            last_msg = messages[-1]
            text_content = last_msg.get("content", "Опиши это изображение подробно.")
            
            last_msg["content"] = [
                {
                    "type": "text",
                    "text": text_content if text_content else "Опиши это изображение подробно."
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{image_mime_type};base64,{image_base64}"
                    }
                }
            ]
            use_model = OPENAI_VISION_MODEL
        else:
            use_model = model or DEFAULT_MODEL
        
        # Проверяем, нужен ли Responses API (для gpt-5.2-pro)
        if use_model == "gpt-5.2-pro":
            # Используем Responses API
            # Преобразуем messages в формат input для responses
            input_messages = []
            for msg in messages:
                input_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            response = await client.responses.create(
                model=use_model,
                input=input_messages,
                reasoning={"effort": "medium"}
            )
            
            # Извлекаем текст из response
            if response.output:
                for item in response.output:
                    if item.type == "message" and item.content:
                        for content_item in item.content:
                            if content_item.type == "output_text":
                                return content_item.text
            return "Не удалось получить ответ"
        else:
            # Используем обычный Chat Completions API
            logger.info("Using standard Chat Completions API")
            response = await client.chat.completions.create(
                model=use_model,
                messages=messages,
                max_completion_tokens=MAX_TOKENS
            )
            
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content or "Пустой ответ"
                logger.info(f"OpenAI response received: {len(content)} chars")
                return content
            return "Не удалось получить ответ"
        
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return f"❌ Ошибка OpenAI: {str(e)}"


async def get_simple_response(user_message: str, model: str = None) -> str:
    """
    Получает простой ответ без истории.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message}
    ]
    return await get_chat_response(messages, model=model)


async def generate_image(prompt: str, size: str = "1024x1024", quality: str = "standard") -> Tuple[Optional[str], Optional[str]]:
    """
    Генерирует изображение с помощью DALL-E 3.
    
    Args:
        prompt: Описание изображения
        size: Размер изображения (1024x1024, 1024x1792, 1792x1024)
        quality: Качество (standard, hd)
        
    Returns:
        Tuple[url изображения, revised_prompt] или (None, error_message)
    """
    try:
        response = await client.images.generate(
            model=IMAGE_MODEL,
            prompt=prompt,
            size=size,
            quality=quality,
            n=1
        )
        
        if response.data and len(response.data) > 0:
            image_url = response.data[0].url
            revised_prompt = response.data[0].revised_prompt
            return image_url, revised_prompt
        
        return None, "Не удалось сгенерировать изображение"
        
    except Exception as e:
        logger.error(f"DALL-E error: {e}")
        return None, f"❌ Ошибка генерации: {str(e)}"


def encode_image_to_base64(image_data: bytes) -> str:
    """
    Кодирует изображение в base64.
    """
    return base64.b64encode(image_data).decode('utf-8')


async def edit_image_with_dalle(
    image_bytes: bytes,
    prompt: str,
    size: str = "1024x1024"
) -> Tuple[Optional[str], Optional[str]]:
    """
    Редактирует изображение с помощью DALL-E 3 (через gpt-image-1).
    
    Args:
        image_bytes: Исходное изображение в байтах
        prompt: Описание желаемых изменений
        size: Размер результата
        
    Returns:
        Tuple[url изображения, описание] или (None, error_message)
    """
    try:
        import io
        
        # Создаём file-like объект с правильным именем файла
        image_file = io.BytesIO(image_bytes)
        image_file.name = "image.png"  # Устанавливаем имя файла для определения MIME типа
        
        # Используем новый API редактирования изображений
        response = await client.images.edit(
            model="gpt-image-1",
            image=image_file,
            prompt=prompt,
            size=size,
            n=1
        )
        
        if response.data and len(response.data) > 0:
            # gpt-image-1 возвращает b64_json
            b64_data = response.data[0].b64_json
            if b64_data:
                # Декодируем и возвращаем как data URL
                return f"data:image/png;base64,{b64_data}", prompt
            elif response.data[0].url:
                return response.data[0].url, prompt
        
        return None, "Не удалось отредактировать изображение"
        
    except Exception as e:
        logger.error(f"Image edit error: {e}")
        return None, f"❌ Ошибка редактирования: {str(e)}"

