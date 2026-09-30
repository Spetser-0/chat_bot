with open('C:/Users/Dell/Desktop/spetser-ai/backend/app/services/presentation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Check lines 191-195
for i in range(188, 197):
    line = lines[i]
    print(f'Line {i+1}: {repr(line)}')