
from docx_generator import convert_markdown_to_docx
import markdown
from docx import Document

text = """
Отчёт: Население США
1.	Исполнительное резюме (ключевые факты)
2.	Общая численность: порядка 331–333 млн (перепись 2020: ≈331,4 млн; оценка 2022: ≈333,3 млн). 
3.	Среднегодовой прирост в последние десятилетия замедлился; после 2020 рост обеспечивается в основном международной миграцией. 

7.	
Динамика численности (1950–2022) — таблица
Значения округлены, источники: US Census (Decennial Census) и Annual Estimates.
| Год | Население |
|---|---|
| 1950 | 150.7 |

8.	Возрастная структура (приблизительно, последовательность трендов)
9.	Доля детей (0–17): ≈21–23%. 
10.	Доля работоспособного населения (18–64): ≈60–62%. 
"""

print("--- GENERATING DOCX ---")
docx_bytes = convert_markdown_to_docx(text)
with open("repro_v2_debug.docx", "wb") as f:
    f.write(docx_bytes)

print("\n--- INSPECTING STYLES AND ELEMENT ORDER ---")
doc = Document("repro_v2_debug.docx")
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.text.paragraph import Paragraph

for child in doc.element.body.iterchildren():
    if isinstance(child, CT_P):
        p = Paragraph(child, doc)
        t = p.text.strip()
        if t:
            nid = p._element.pPr.numPr.numId.val if p._element.pPr and p._element.pPr.numPr else '-'
            print(f"P: {t[:10]}... | {p.style.name} | ID:{nid}")
    elif isinstance(child, CT_Tbl):
        print("TABLE")

