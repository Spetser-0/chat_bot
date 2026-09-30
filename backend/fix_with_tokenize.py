import tokenize
import io

with open('C:/Users/Dell/Desktop/spetser-ai/backend/app/services/presentation.py', 'rb') as f:
    tokens = list(tokenize.tokenize(io.BytesIO(content).readline))

# Actually, let's just use tokenize to re-indent the file properly
import io
with open('C:/Users/Dell/Desktop/spetser-ai/backend/app/services/presentation.py', 'rb') as f:
    content = f.read()

# Use tokenize to get proper indentation
tokens = list(tokenize.tokenize(io.BytesIO(content).readline))

# Rebuild the source with correct indentation
output = []
prev_token = None
indent_level = 0
for tok in tokens:
    if tok.type == tokenize.INDENT:
        indent_level += 1
    elif tok.type == tokenize.DEDENT:
        indent_level -= 1
    elif tok.type == tokenize.NEWLINE:
        output.append('\n')
        # Add indent for next line
        output.append('    ' * indent_level)
    elif tok.type != tokenize.ENCODING and tok.type != tokenize.ENDMARKER:
        output.append(tok.string)

fixed_source = ''.join(output)

with open('C:/Users/Dell/Desktop/spetser-ai/backend/app/services/presentation.py', 'w', encoding='utf-8') as f:
    f.write(fixed_source)

print('Fixed!')