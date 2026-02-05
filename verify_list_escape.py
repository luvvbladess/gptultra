
import markdown
import re

text = """
1. List Item 1
2. List Item 2

Text

10. List Item 10
"""

def preprocess(md):
    lines = md.split('\n')
    new_lines = []
    for line in lines:
        # Escape numbering: "1. " -> "1\. "
        # We capture leading whitespace (\s*), the number (\d+), and the dot.
        # We replace with group1 + group2 + "\."
        new_line = re.sub(r'^(\s*)(\d+)\.', r'\1\2\\.', line)
        new_lines.append(new_line)
    return "\n".join(new_lines)

escaped = preprocess(text)
print("--- Escaped Markdown ---")
print(escaped)

html = markdown.markdown(escaped)
print("\n--- HTML Output ---")
print(html)

if "<ol>" in html:
    print("RESULT: FAIL")
else:
    print("RESULT: SUCCESS")
