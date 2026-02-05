"""
Модуль для генерации DOCX документов из Markdown/текста.
Использует связку markdown -> html -> docx для поддержки таблиц и форматирования.
"""

import io
import markdown
from docx import Document
from htmldocx import HtmlToDocx

def convert_markdown_to_docx(markdown_text: str) -> bytes:
    """
    Конвертирует Markdown текст в DOCX документ.
    
    Args:
        markdown_text: Исходный текст в формате Markdown
        
    Returns:
        Байты сгенерированного DOCX файла
    """
    # 0. Препроцессинг текста
    # Часто бывает, что перед таблицей нет отступа, и markdown не видит её.
    # Добавляем перенос строки перед строками, начинающимися с "|"
    lines = markdown_text.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # Если строка похожа на начало таблицы (содержит | и не пустая), а предыдущая не пустая - добавляем отступ
        if "|" in line and i > 0 and lines[i-1].strip() and not lines[i-1].strip().startswith("|"):
             # Проверяем, что это действительно таблица (наличие разделителя ---|--- на следующей строке)
             if i + 1 < len(lines) and set(lines[i+1].strip()) <= set("|-:| "):
                 fixed_lines.append("")
        
        fixed_lines.append(line)
        
    markdown_text = "\n".join(fixed_lines)

    # 1. Конвертируем Markdown в HTML
    # Используем расширения для поддержки таблиц и других элементов
    html_text = markdown.markdown(
        markdown_text, 
        extensions=['tables', 'extra', 'fenced_code', 'nl2br']
    )
    
    # 2. Создаем документ и парсер
    doc = Document()
    new_parser = HtmlToDocx()
    
    # 3. Парсим HTML и добавляем в документ
    # Оборачиваем в try-except на случай проблем с парсингом сложного HTML
    try:
        new_parser.add_html_to_document(html_text, doc)
    except Exception as e:
        # В случае ошибки добавляем текст как есть, но сигнализируем об ошибке в лог (или просто добавляем параграф)
        doc.add_paragraph("Ошибка при конвертации форматирования. Исходный текст:")
        doc.add_paragraph(markdown_text)
    
    # 4. Сохраняем в байты
    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    
    return file_stream.read()
