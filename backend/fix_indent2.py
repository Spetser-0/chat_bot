with open('C:/Users/Dell/Desktop/spetser-ai/backend/app/services/presentation.py', 'rb') as f:
    content = f.read()

idx = content.find(b'return request')
print('Index:', idx)

# Print chars around return
for i in range(idx-15, idx+15):
    c = content[i]
    if c < 32 or c >= 127:
        print(f'{i}: {c} (non-printable)')
    else:
        print(f'{i}: {c} = {chr(c)}')

# Fix: replace 8 spaces before return with 4 spaces
content = content.replace(b'    return request', b'    return request')

with open('C:/Users/Dell/Desktop/spetser-ai/backend/app/services/presentation.py', 'wb') as f:
    f.write(content)

print('Fixed')