
import markdown

text = """
6) Прогнозы (ориентировочно)
- Краткосрочно (до 2030): рост населения будет медленным...
- Долгосрочно (2050): по разным сценариям...
Таблица — ориентировочный сценарный прогноз
| Год | Низкий сценарий (млн) | Базовый сценарий (млн) | Высокий сценарий (млн) |
|----:|----------------------:|-----------------------:|-----------------------:|
| 2030 | ~337–340 | ~340–345 | ~345–350 |
| 2040 | ~345–355 | ~355–370 | ~370–390 |
| 2050 | ~355–370 | ~375–395 | ~390–420 |
"""

print("--- TESTING ORIGINAL TEXT ---")
html = markdown.markdown(text, extensions=['tables', 'extra', 'fenced_code', 'nl2br'])
print(html)

if "<table>" not in html:
    print("\nFAIL: Table not found in HTML output!")
else:
    print("\nSUCCESS: Table found.")

print("\n--- TESTING WITH EXTRA NEWLINE ---")
# Try adding a newline before the table
text_fixed = text.replace("Таблица", "\n\nТаблица").replace("| Год", "\n| Год")
html_fixed = markdown.markdown(text_fixed, extensions=['tables', 'extra', 'fenced_code', 'nl2br'])
# print(html_fixed)

if "<table>" in html_fixed:
    print("\nFIXED: Table found after adding newlines.")
