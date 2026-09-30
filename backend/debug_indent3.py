with open('C:/Users/Dell/Desktop/spetser-ai/backend/app/services/presentation.py', 'rb') as f:
    content = f.read()

# Check for tabs
tab_indices = [i for i, c in enumerate(content) if c == 9]  # ASCII 9 = tab
print(f'Tab characters found at indices: {tab_indices[:50]}')
print(f'Total tabs: {len(tab_indices)}')

# Check lines around return request
idx = content.find(b'return request')
print(f'return request at index: {idx}')

# Show context with line numbers
lines = content.split(b'\n')
for i, line in enumerate(lines):
    if b'return request' in line:
        print(f'Line {i+1}: {repr(line)}')
    if b'async def process_request' in line:
        print(f'Line {i+1}: {repr(line)}')
    if b'async def create_request' in line:
        print(f'Line {i+1}: {repr(line)}')