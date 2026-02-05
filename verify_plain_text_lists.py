
from docx_generator import convert_markdown_to_docx
import zipfile
import io
import re

text = """
1. List Item 1
2. List Item 2

| Col 1 | Col 2 |
|---|---|
| Val 1 | Val 2 |

1. List 2 Item 1
"""

print("Generating DOCX...")
try:
    docx_bytes = convert_markdown_to_docx(text)
    with open("verify_plain_lists.docx", "wb") as f:
        f.write(docx_bytes)
    print("DOCX generated.")
except Exception as e:
    print(f"CRITICAL FAIL: {e}")
    exit(1)

print("Analyzing XML...")
with zipfile.ZipFile(io.BytesIO(docx_bytes)) as z:
    doc_xml = z.read('word/document.xml').decode('utf-8')

    # valid plain text implementation should NOT have numPr for these lines
    # and should contain the literal text "1. List Item"
    
    if 'w:numPr' in doc_xml:
        # It's possible some other things use numPr, but let's check closely around our text
        print("WARNING: numPr found in document. Checking context...")
    
    # Check for specific text existence
    if "1. List Item 1" in doc_xml:
        print("SUCCESS: Found literal '1. List Item 1' in XML.")
    else:
        print("FAIL: Did not find literal '1. List Item 1'.")

    # Check for numbering properties on the list item paragraphs
    # We look for the paragraph containing the text, then check if it has numPr
    # This is a bit rough with regex but sufficient for verification
    
    # Find paragraph containing "List Item 1"
    p_match = re.search(r'<w:p[ >].*?List Item 1.*?</w:p>', doc_xml, re.DOTALL)
    if p_match:
        p_content = p_match.group(0)
        if '<w:numPr>' in p_content:
             print("FAIL: Paragraph 'List Item 1' triggers numbering (numPr found).")
        else:
             print("SUCCESS: Paragraph 'List Item 1' is plain text (no numPr).")
    else:
        print("FAIL: Could not find paragraph content.")

