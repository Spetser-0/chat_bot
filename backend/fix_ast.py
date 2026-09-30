import ast
import sys

with open('C:/Users/Dell/Desktop/spetser-ai/backend/app/services/presentation.py', 'r', encoding='utf-8') as f:
    source = f.read()

# Parse and unparse to fix indentation
tree = ast.parse(source)

if sys.version_info >= (3, 9):
    fixed = ast.unparse(ast.fix_missing_locations(tree))
    with open('C:/Users/Dell/Desktop/spetser-ai/backend/app/services/presentation.py', 'w', encoding='utf-8') as f:
        f.write(fixed)
    print('Fixed using ast.unparse!')
else:
    # For older Python, use a simple fix: ensure consistent 4-space indentation
    import re
    lines = source.split('\n')
    fixed_lines = []
    for line in lines:
        # Replace leading tabs with 4 spaces
        line = line.expandtabs(4)
        # Ensure consistent 4-space indentation for def/class
        if line.startswith('    '):
            # Already 4 spaces, keep
            pass
        elif line.startswith('\t'):
            line = '    ' + line[1:]
        fixed_lines.append(line)
    fixed = '\n'.join(fixed_lines)
    with open('C:/Users/Dell/Desktop/spetser-ai/backend/app/services/presentation.py', 'w', encoding='utf-8') as f:
        f.write(fixed)
    print('Fixed with regex!')