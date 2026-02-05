"""
Модуль для генерации DOCX документов из Markdown/текста.
Использует связку markdown -> html -> docx для поддержки таблиц и форматирования.
"""

import io
import markdown
from typing import Optional
import markdown
from docx import Document
from docx.oxml.shared import OxmlElement
from docx.oxml.ns import qn
from htmldocx import HtmlToDocx

def create_list_numbering(doc, abstract_num_id=1):
    """
    Creates a new numbering definition (w:num) that points to the given abstractNumId.
    Returns the new numId.
    """
    # Get the numbering part
    try:
        numbering_part = doc.part.numbering_part
    except NotImplementedError:
        # Happens in some simplified docx structures or testing
        return None
        
    # Generate a new numId
    # Simply finding the max and adding 1 is a safe strategy usually, 
    # but python-docx doesn't expose a clean add_num method that returns ID easily.
    # We'll use the internal _next_numId if available or manual calculation.
    
    # Access the numbering element
    numbering_element = numbering_part.numbering_definitions._numbering
    
    # Find next available ID
    current_ids = [int(num.numId) for num in numbering_element.num_lst]
    next_num_id = max(current_ids, default=0) + 1
    
    # Create new <w:num w:numId="X">
    num = OxmlElement('w:num')
    num.set(qn('w:numId'), str(next_num_id))
    
    # <w:abstractNumId w:val="Y"/>
    abstractNumId = OxmlElement('w:abstractNumId')
    abstractNumId.set(qn('w:val'), str(abstract_num_id))
    num.append(abstractNumId)
    
    # Add to numbering part
    numbering_element.append(num)
    
    return next_num_id

def fix_numbered_lists(doc):
    """
    Post-process the document to reset numbering for separate lists.
    htmldocx typically uses 'List Number' style for <ol>.
    We detect breaks in list paragraphs and force a new numId.
    """
    last_style = None
    current_num_id = None
    
    # Basic abstractNumId for 'List Number' in default template is often 1 or similar.
    # Ideally we find it from the style.
    # For now, we'll try to find the standard bullet/numbering definitions.
    # If we can't find specific ones, this might be tricky.
    
    # Strategy:
    # 1. Inspect 'List Number' style to find its default numId
    # 2. Get abstractNumId from that numId
    # 3. Use that abstractNumId to create new nums
    
    list_style_name = 'List Number' # Default in htmldocx for <ol>
    abstract_num_id = None
    
    try:
        styles = doc.styles
        if list_style_name in styles:
            style = styles[list_style_name]
            if hasattr(style, '_element') and style._element.pPr is not None and style._element.pPr.numPr is not None:
                default_num_id = style._element.pPr.numPr.numId.val
                # Now finding abstractNumId from numbering part
                numbering_part = doc.part.numbering_part
                num = numbering_part.numbering_definitions._numbering.get_num(default_num_id)
                if num is not None:
                    abstract_num_id = num.abstractNumId.val
    except Exception as e:
        # Fallback or error - just log/ignore
        pass
        
    if abstract_num_id is None:
        # Fallback: assume abstractNumId=1 if we can't find it (risky but often true for standard template)
        # Or better: search for ANY abstractNum with numbering
        # Let's skip optimization and try best effort if we found it.
        # If not found, we might break things, so return.
        # Check if we can find any num in the document part
        try:
             # Just explicitly use a known abstractNum if possible? No.
             pass
        except:
             return

    # If still None, try to pick one from used paragraphs?
    # Let's verify on the fly.
    
    for i, p in enumerate(doc.paragraphs):
        # Check if this is a List Number paragraph
        if p.style.name == list_style_name:
            # If previous was NOT List Number, this is a START of a new list
            if last_style != list_style_name:
                # We need a NEW numbering ID
                # If we haven't found abstract_num_id yet, try to find it from THIS paragraph's effective numbering
                # (though usually it's in the style)
                
                if abstract_num_id is None:
                     # Try to get it from style again implicitly if we missed it?
                     # Or assuming standard Word template: 
                     # abstractNumId 0 -> often bullets
                     # abstractNumId 1 -> often numbers
                     # This is a gamble.
                     # Let's try to assume 1 if we failed to look it up.
                     abstract_num_id = 1
                
                current_num_id = create_list_numbering(doc, abstract_num_id)
            
            # Apply the current_num_id to this paragraph
            if current_num_id is not None:
                pPr = p._element.get_or_add_pPr()
                numPr = pPr.get_or_add_numPr()
                numId = numPr.get_or_add_numId()
                numId.set(qn('w:val'), str(current_num_id))
                
                # Ensure level is 0 (or keep existing?)
                # htmldocx might set level. We should preserve or set to 0.
                ilvl = numPr.get_or_add_ilvl()
                ilvl.set(qn('w:val'), '0') # Assuming top level for now
                
        last_style = p.style.name


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
    
    # 5. Исправляем нумерацию списков (сброс нумерации для новых списков)
    try:
        fix_numbered_lists(doc)
    except Exception as e:
        # Не ломаем генерацию, если фикс не сработал
        print(f"List fix warning: {e}")

    # 6. Сохраняем в байты
    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    
    return file_stream.read()
