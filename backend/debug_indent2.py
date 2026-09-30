with open('C:/Users/Dell/Desktop/spetser-ai/backend/app/services/presentation.py', 'rb') as f:
    content = f.read()

idx = content.find(b'async def process_request')
print('Index:', idx)
for i in range(idx-20, idx+30):
    c = content[i]
    if c < 32 or c >= 127:
        print(f'{i}: {c} (non-printable)')
    else:
        print(f'{i}: {c} = {chr(c)}')