"""
Модуль для извлечения текста из документов (DOCX, PDF)
"""

import io
from typing import Optional

from docx import Document
import fitz  # PyMuPDF


async def extract_text_from_docx(file_data: bytes) -> str:
    """
    Извлекает текст из DOCX файла.
    
    Args:
        file_data: Байты файла DOCX
        
    Returns:
        Извлеченный текст
    """
    try:
        doc = Document(io.BytesIO(file_data))
        text_parts = []
        
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text)
        
        # Также извлекаем текст из таблиц
        for table in doc.tables:
            for row in table.rows:
                row_text = []
                for cell in row.cells:
                    if cell.text.strip():
                        row_text.append(cell.text.strip())
                if row_text:
                    text_parts.append(" | ".join(row_text))
        
        return "\n".join(text_parts)
    except Exception as e:
        return f"Ошибка при чтении DOCX: {str(e)}"


async def extract_text_from_pdf(file_data: bytes) -> str:
    """
    Извлекает текст из PDF файла.
    
    Args:
        file_data: Байты файла PDF
        
    Returns:
        Извлеченный текст
    """
    try:
        text_parts = []
        
        # Открываем PDF из байтов
        pdf_document = fitz.open(stream=file_data, filetype="pdf")
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            text = page.get_text()
            if text.strip():
                text_parts.append(f"--- Страница {page_num + 1} ---\n{text}")
        
        pdf_document.close()
        
        return "\n\n".join(text_parts)
    except Exception as e:
        return f"Ошибка при чтении PDF: {str(e)}"


async def extract_text_from_txt(file_data: bytes) -> str:
    """
    Извлекает текст из TXT файла с автоопределением кодировки.
    
    Args:
        file_data: Байты файла TXT
        
    Returns:
        Извлеченный текст
    """
    # Пробуем разные кодировки
    encodings = ['utf-8', 'utf-8-sig', 'cp1251', 'cp1252', 'latin-1', 'iso-8859-1', 'koi8-r']
    
    for encoding in encodings:
        try:
            return file_data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    
    # Если ничего не подошло, декодируем с ошибками
    return file_data.decode('utf-8', errors='replace')


async def extract_text_from_file(file_data: bytes, file_name: str) -> Optional[str]:
    """
    Определяет тип файла и извлекает текст.
    
    Args:
        file_data: Байты файла
        file_name: Имя файла
        
    Returns:
        Извлеченный текст или None, если формат не поддерживается
    """
    file_name_lower = file_name.lower()
    
    if file_name_lower.endswith('.docx'):
        return await extract_text_from_docx(file_data)
    elif file_name_lower.endswith('.pdf'):
        return await extract_text_from_pdf(file_data)
    elif file_name_lower.endswith('.txt'):
        return await extract_text_from_txt(file_data)
    else:
        return None

