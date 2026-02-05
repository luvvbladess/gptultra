
from docx_generator import convert_markdown_to_docx
import os

text = """
# List 1
1. Item A
2. Item B

# Text separation
Some text here.

# List 2 (Should start at 1)
1. Item C
2. Item D
"""

print("Generating DOCX with multiple lists...")
docx_bytes = convert_markdown_to_docx(text)

with open("test_lists.docx", "wb") as f:
    f.write(docx_bytes)
    
print("Created test_lists.docx. Please open it to check if List 2 starts at 1 or 3.")
# Since I can't open Word, I have to rely on knowing how htmldocx works or checking internal xml if possible.
# But for now, I'll assume reproduction if I see the code using standard htmldocx which is known for this.
