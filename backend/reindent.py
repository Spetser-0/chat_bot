# Reformat the presentation.py file with consistent 4-space indentation
with open('C:/Users/Dell/Desktop/spetser-ai/backend/app/services/presentation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Track expected indentation
new_lines = []
expected_indent = 0

for line in lines:
    stripped = line.lstrip()
    
    # Calculate current indent
    current_indent = len(line) - len(stripped)
    
    # Skip empty lines
    if not stripped:
        new_lines.append('\n')
        continue
    
    # Adjust expected indent based on keywords
    if stripped.startswith(('def ', 'class ', 'async def ', '@')):
        # Top-level definitions
        expected_indent = 0
    elif stripped.startswith(('    ', '\t')):
        # Already indented, keep relative
        pass
    elif line.rstrip().endswith(':'):
        # Block opener
        pass
    elif stripped.startswith(('return', 'raise', 'yield', 'break', 'continue', 'pass')):
        # Statements at current level
        pass
    elif stripped.startswith(('except:', 'finally:', 'else:', 'elif ')):
        # Dedent for these
        expected_indent = max(0, expected_indent - 4)
    
    # Apply expected indentation
    if expected_indent == 0:
        new_lines.append(stripped)
    else:
        new_lines.append(' ' * expected_indent + stripped)
    
    # Update expected indent for next line
    if stripped.endswith(':'):
        expected_indent += 4

# Write back
with open('C:/Users/Dell/Desktop/spetser-ai/backend/app/services/presentation.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))

print('Reformatted!')