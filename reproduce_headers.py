
import markdown
import re
from htmldocx import HtmlToDocx
from docx import Document

text = """
Normal text.
### 1. This is a header (No blank line before)

Normal text.
"""

def test_markdown():
    # Simulate the preprocessing in docx_generator
    lines = text.split('\n')
    fixed_lines = []
    for line in lines:
        # The list escaping regex
        line = re.sub(r'^(\s*)(\d+)\.', r'\1\2\\.', line)
        fixed_lines.append(line)
    
    preprocessed_text = "\n".join(fixed_lines)
    print(f"--- Preprocessed ---\n{preprocessed_text}")
    
    html = markdown.markdown(preprocessed_text, extensions=['tables', 'extra', 'fenced_code', 'nl2br'])
    print(f"\n--- HTML Output ---\n{html}")
    
    if "<h3>" in html:
        print("\nPass: Header detected in HTML")
    else:
        print("\nFail: Header NOT detected in HTML")

test_markdown()
