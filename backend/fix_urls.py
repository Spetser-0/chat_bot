with open('C:/Users/Dell/Desktop/spetser-ai/backend/tests/integration/test_storage.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix all deliverable download URLs
content = content.replace(
    'f"/api/v1/deliverables/{deliverable.id}/download"',
    'f"/api/v1/presentations/deliverables/{deliverable.id}/download"'
)
content = content.replace(
    'f"/api/v1/deliverables/{request.id}/download"',
    'f"/api/v1/presentations/deliverables/{request.id}/download"'
)

with open('C:/Users/Dell/Desktop/spetser-ai/backend/tests/integration/test_storage.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed!')