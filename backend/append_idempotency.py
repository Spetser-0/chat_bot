with open('C:/Users/Dell/Desktop/spetser-ai/backend/idempotency_tests_content.py', 'r', encoding='utf-8') as f:
    new_tests = f.read()

with open('C:/Users/Dell/Desktop/spetser-ai/backend/tests/integration/test_presentation.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'class TestIdempotency:' in content:
    print('Tests already exist')
else:
    marker = 'async def test_unauthorized_access_denied'
    idx = content.rfind(marker)
    if idx != -1:
        idx2 = content.find('\n\nclass ', idx)
        if idx2 == -1:
            idx2 = len(content)
        content = content[:idx2] + '\n\n' + new_tests
        with open('C:/Users/Dell/Desktop/spetser-ai/backend/tests/integration/test_presentation.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print('Tests appended successfully!')
    else:
        print('Could not find test_unauthorized_access_denied')