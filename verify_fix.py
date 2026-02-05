
from docx_generator import convert_markdown_to_docx
import zipfile
import io
import re

text = """
1. List 1 Item 1
2. List 1 Item 2

Break text.

1. List 2 Item 1 (Should be 1)
2. List 2 Item 2

| Table | Header |
|---|---|
| Cell | Value |

1. List 3 Item 1 (Should be 1)
"""

print("Generating DOCX...")
try:
    print("Calling convert_markdown_to_docx...")
    docx_bytes = convert_markdown_to_docx(text)
    print("Conversion done.")
    with open("verify_fix_output_v2.docx", "wb") as f:
        f.write(docx_bytes)
    print("File saved.")

except Exception as e:
    print(f"CRITICAL FAIL: {e}")
    exit(1)

print("Analyzing XML for lvlOverride...")
with zipfile.ZipFile(io.BytesIO(docx_bytes)) as z:
    num_xml = z.read('word/numbering.xml').decode('utf-8')
    doc_xml = z.read('word/document.xml').decode('utf-8')

    # Find all num definitions
    # Find all num definitions - using non-greedy checking
    # Note: findall with grouping returns the group. We want the whole match.
    nums = re.findall(r'(<w:num w:numId="\d+">.*?</w:num>)', num_xml, re.DOTALL)
    
    print("\n--- Numbering Definitions ---")
    for num_block in nums:
        # Safer regex
        nid_match = re.search(r'w:numId="(\d+)"', num_block)
        if not nid_match:
             # Try with namespace prefix if needed or standard
             nid_match = re.search(r'numId="(\d+)"', num_block)
        
        nid = nid_match.group(1) if nid_match else "UNKNOWN"
        
        override = re.search(r'<w:lvlOverride w:ilvl="0"><w:startOverride w:val="1"/></w:lvlOverride>', num_block)
        
        status = "HAS OVERRIDE" if override else "NO OVERRIDE"
        print(f"numId={nid}: {status}")


    print("\n--- Paragraph Usage ---")
    # Simple text scan to check IDs used
    p_iter = re.finditer(r'<w:p .*?>(.*?)</w:p>', doc_xml, re.DOTALL)
    for p_match in p_iter:
        p_content = p_match.group(1)
        text_match = re.search(r'<w:t>(.*?)</w:t>', p_content)
        txt = text_match.group(1) if text_match else "???"
        
        num_match = re.search(r'<w:numId w:val="(\d+)"/>', p_content)
        nid = num_match.group(1) if num_match else "None"
        
        if "List" in txt:
            print(f"Item: '{txt}' -> numId={nid}")

