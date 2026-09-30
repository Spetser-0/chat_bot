with open('C:/Users/Dell/Desktop/spetser-ai/backend/app/services/presentation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Check line 193
line = lines[192]  # 0-indexed
print(f'Line 193: {repr(line)}')
print(f'Length: {len(line)}')
for i, c in enumerate(line):
    o = ord(c)
    ch = chr(o) if 32 <= o < 127 else '?'
    print(f'  {i}: {o} = {ch}')