
from docx_generator import convert_markdown_to_docx
import markdown

text = """
Отчёт по теме: Население США (альтернативная версия — с нумерованными списками)
1.	Краткое резюме
2.	Население США (оценка на 1 июля 2023): ~334 233 854 (US Census Bureau). 
3.	Совокупный коэффициент рождаемости (TFR) ≈ 1.6–1.7 — ниже уровня замены. 
4.	Основной прирост — за счёт международной миграции; наблюдается старение населения (доля 65+ растёт). 
5.	
Урбанизация ≈ 82%; смещение в сторону Sun Belt (юг и юго‑запад).
6.	
Ключевые численные показатели (сводка)
7.	Перепись 2020: 331 449 281. 
8.	Медианный возраст: ~38–39 лет. 
9.	Этнический состав (прибл., 2020): негиспаноязычные белые 57–58%, латиноамериканцы 18–19%, афроамериканцы 12–13%, азиаты ~6%. 
10.	
Урбанизация: ~82% городского населения.
11.	
Историческая динамика (переписи 1900–2020) — таблица

| Год  | Население (перепись) |
|-----:|---------------------:|
| 1900 | 76 212 168           |
| 1910 | 92 228 496           |
"""

print("--- DEBUGGING PRE-PROCESSING ---")
# Manually run the pre-processing logic from docx_generator
lines = text.split('\n')
fixed_lines = []
for i, line in enumerate(lines):
    if "|" in line and i > 0 and lines[i-1].strip() and not lines[i-1].strip().startswith("|"):
            if i + 1 < len(lines) and set(lines[i+1].strip()) <= set("|-:| "):
                fixed_lines.append("")
    fixed_lines.append(line)
fixed_text = "\n".join(fixed_lines)

print(f"Pre-processed text segment around table:\n{fixed_text[fixed_text.find('Таблица'):fixed_text.find('| 1910')]}")

print("\n--- DEBUGGING MARKDOWN TO HTML ---")
html = markdown.markdown(fixed_text, extensions=['tables', 'extra', 'fenced_code', 'nl2br'])
if "<table>" in html:
    print("SUCCESS: Table found in HTML.")
else:
    print("FAILURE: No <table> in HTML.")
    print("HTML Fragment around table:")
    start_idx = html.find("Историческая динамика")
    print(html[start_idx:start_idx+500])

print("\n--- GENERATING DOCX ---")
try:
    docx_bytes = convert_markdown_to_docx(text)
    with open("complex_test.docx", "wb") as f:
        f.write(docx_bytes)
    print("Generated complex_test.docx")
except Exception as e:
    print(f"Error generating DOCX: {e}")
