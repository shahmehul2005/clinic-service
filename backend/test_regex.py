import re

text = """
(function=check_availability>{"clinic_id": "99407cf6-b39c-4382-9346-6bf07f121f47", "date_str": "2026-07-15"}</function>
Kya aapko koi date pasand aati hai?
<function=book_slot>{"date_str": "2026-07-16"}</function>
Another text here.
(function=book_slot>{"date_str": "2026-07-17"}</function)
"""

# Regex test
cleaned = re.sub(r'[\(<]function=.*?</function[\)>]?', '', text, flags=re.DOTALL)
print("CLEANED TEXT:")
print(cleaned)

# Regex extraction test for fallback
matches = re.finditer(r'[\(<]function=(\w+)>(.*?)</function[\)>]?', text, re.DOTALL)
print("\nEXTRACTED:")
for match in matches:
    print(match.group(1), match.group(2))
