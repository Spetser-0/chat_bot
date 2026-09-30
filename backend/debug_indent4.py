with open('C:/Users/Dell/Desktop/spetser-ai/backend/app/services/presentation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Print lines around 190-200
for i in range(180, 200):
    line = lines[i]
    # Show leading spaces count
    leading = len(line) - len(line.lstrip())
    print(f'Line {i+1:3d} (indent={leading}): {repr(line.rstrip())}')