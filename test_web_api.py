import sys, os
smart_dir = r'C:\Users\13364\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a16b62a291cd733e969550c\smart_agent'
sys.path.insert(0, smart_dir)
os.chdir(smart_dir)

from web_interface import app
app.testing = True
client = app.test_client()

# 模拟前台对话
sid = 'web_browser_test'

# Round 1: 用户说失眠
print('=== Round 1: 你好，我最近失眠 ===')
r1 = client.post('/api/chat', json={'message': '你好，我最近失眠', 'session_id': sid})
data1 = r1.get_json()
print('Success:', data1.get('success'))
print('Intent:', data1.get('intent'))
print('State:', data1.get('state'))
print('Action:', data1.get('next_action'))
print('Response:', data1.get('response', '')[:100])
print('Products:', data1.get('recommended_products', []))

# Round 2: 用户要求推荐
print('\n=== Round 2: 有什么产品推荐吗 ===')
r2 = client.post('/api/chat', json={'message': '有什么产品推荐吗', 'session_id': sid})
data2 = r2.get_json()
print('Success:', data2.get('success'))
print('Intent:', data2.get('intent'))
print('State:', data2.get('state'))
print('Action:', data2.get('next_action'))
print('Response:', data2.get('response', '')[:200])
print('Products:', data2.get('recommended_products', []))

# 检查对话记录
print('\n=== 对话记录 ===')
r3 = client.get('/api/v2/conversations?limit=10')
data3 = r3.get_json()
for s in data3.get('sessions', []):
    if 'web_browser_test' in s.get('session_id', ''):
        print('Session:', s.get('session_id'))
        print('Messages:', s.get('total_messages'))

# 检查知识库调用记录
print('\n=== 知识库调用记录 ===')
r4 = client.get('/api/v2/kb/call-records?limit=10')
data4 = r4.get_json()
for rec in data4.get('records', []):
    if 'web_browser_test' in rec.get('session_id', ''):
        print('Query:', rec.get('query'))
        print('Products:', rec.get('product_names'))
        print('Results:', rec.get('results_count'))
