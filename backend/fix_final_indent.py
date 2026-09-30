with open('C:/Users/Dell/Desktop/spetser-ai/backend/app/services/presentation.py', 'rb') as f:
    content = f.read()

# The issue: "return request" has 8 spaces but should have 4 spaces
# Let's check the exact bytes around "return request"
idx = content.find(b'return request')
print(f'Index: {idx}')
for i in range(idx-10, idx+20):
    c = content[i]
    if c < 32 or c >= 127:
        print(f'{i}: {c} (non-printable)')
    else:
        print(f'{i}: {c} = {chr(c)}')

# Fix: replace 8 spaces before 'return request' with 4 spaces
# The pattern is 8 spaces before 'return'
content = content.replace(b'        return request', b'    return request')

with open('C:/Users/Dell/Desktop/spetser-ai/backend/app/services/presentation.py', 'wb') as f:
    f.write(content)

print('Fixed')