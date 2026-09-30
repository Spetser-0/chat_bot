with open('C:/Users/Dell/Desktop/spetser-ai/backend/app/services/presentation.py', 'rb') as f:
    content = f.read()

# Split into lines
lines = content.split(b'\n')

# Fix line 194 (index 193) - it has 1 space, should be empty
# The issue is line 194 has 1 space instead of being empty
if lines[193] == b' ':
    lines[193] = b''
    print('Fixed line 194 (removed 1 space)')
elif lines[193] == b'':
    print('Line 194 is already empty')
else:
    print(f'Line 194 content: {repr(lines[193])}')

# Also check line 193 (return request) - should have 4 spaces
if lines[192].startswith(b'        '):  # 8 spaces
    lines[192] = b'    ' + lines[192][8:]
    print('Fixed line 193 (reduced indent from 8 to 4)')
elif lines[192].startswith(b'    '):
    print('Line 193 already has 4 spaces')
else:
    print(f'Line 193 has unexpected indent: {repr(lines[192][:20])}')

# Write back
new_content = b'\n'.join(lines)
with open('C:/Users/Dell/Desktop/spetser-ai/backend/app/services/presentation.py', 'wb') as f:
    f.write(b'\n'.join(lines))

print('Fixed!')