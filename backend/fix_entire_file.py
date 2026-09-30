import re

with open('C:/Users/Dell/Desktop/spetser-ai/backend/app/services/presentation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Properly re-indent the entire file
# Strategy: Parse the structure and apply correct indentation
new_lines = []
indent_level = 0

# Stack to track blocks
block_stack = []

for line in lines:
    stripped = line.strip()
    
    if not stripped:
        new_lines.append('')
        continue
    
    # Handle dedent keywords
    if stripped.startswith(('except:', 'finally:', 'else:', 'elif ')):
        indent_level = max(0, indent_level - 4)
    elif stripped.startswith('except '):
        indent_level = max(0, indent_level - 4)
    elif stripped.startswith('else:'):
        indent_level = max(0, indent_level - 4)
    
    # Apply current indent
    new_line = ' ' * indent_level + stripped
    
    # Check for block openers
    if stripped.endswith(':'):
        # Check if it's a control flow that increases indent
        stripped_start = stripped.lstrip()
        if stripped_start.startswith(('def ', 'class ', 'async def ', 'if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except ', 'finally:', 'with ', 'async with ', 'async for ')):
            indent_level += 4
    
    # Check for dedent after certain statements
    # (already handled above for else/elif/except/finally)
    
    new_lines.append(' ' * indent_level + stripped)

# Write back
with open('C:/Users/Dell/Desktop/spetser-ai/backend/app/services/presentation.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))

print('Re-indented!')