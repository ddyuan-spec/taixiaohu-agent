import requests
import json

BASE_URL = "https://taixiaohu-agent-production.up.railway.app"
session_id = "test_prod_001"

print("=== 测试泰小虎生产环境API ===\n")

# Round 1: 画像收集
print("Round 1: 你好，我今年35岁，男性")
r1 = requests.post(f"{BASE_URL}/api/chat", json={
    "message": "你好，我今年35岁，男性",
    "session_id": session_id
}, timeout=30)
print(f"Status: {r1.status_code}")
if r1.status_code == 200:
    data1 = r1.json()
    print(f"Intent: {data1.get('intent')}")
    print(f"State: {data1.get('state')}")
    print(f"Response: {data1.get('response', '')[:100]}")
else:
    print(f"Error: {r1.text}")

print("\n" + "="*50 + "\n")

# Round 2: 症状描述
print("Round 2: 最近总是失眠，睡不好")
r2 = requests.post(f"{BASE_URL}/api/chat", json={
    "message": "最近总是失眠，睡不好",
    "session_id": session_id
}, timeout=30)
print(f"Status: {r2.status_code}")
if r2.status_code == 200:
    data2 = r2.json()
    print(f"Intent: {data2.get('intent')}")
    print(f"State: {data2.get('state')}")
    print(f"Action: {data2.get('next_action')}")
    print(f"Response: {data2.get('response', '')[:100]}")
else:
    print(f"Error: {r2.text}")

print("\n" + "="*50 + "\n")

# Round 3: 要求推荐产品
print("Round 3: 有什么产品可以推荐吗？")
r3 = requests.post(f"{BASE_URL}/api/chat", json={
    "message": "有什么产品可以推荐吗？",
    "session_id": session_id
}, timeout=30)
print(f"Status: {r3.status_code}")
if r3.status_code == 200:
    data3 = r3.json()
    print(f"Intent: {data3.get('intent')}")
    print(f"State: {data3.get('state')}")
    print(f"Action: {data3.get('next_action')}")
    print(f"Products: {data3.get('recommended_products', [])}")
    print(f"Response: {data3.get('response', '')[:200]}")
else:
    print(f"Error: {r3.text}")

print("\n" + "="*50 + "\n")

# Round 4: 追问产品
print("Round 4: 这个产品有什么副作用吗？")
r4 = requests.post(f"{BASE_URL}/api/chat", json={
    "message": "这个产品有什么副作用吗？",
    "session_id": session_id
}, timeout=30)
print(f"Status: {r4.status_code}")
if r4.status_code == 200:
    data4 = r4.json()
    print(f"Intent: {data4.get('intent')}")
    print(f"State: {data4.get('state')}")
    print(f"Action: {data4.get('next_action')}")
    print(f"Response: {data4.get('response', '')[:200]}")
else:
    print(f"Error: {r4.text}")

print("\n" + "="*50 + "\n")

# 检查对话记录
print("检查对话记录...")
r5 = requests.get(f"{BASE_URL}/api/v2/conversations?limit=10", timeout=10)
if r5.status_code == 200:
    sessions = r5.json().get('sessions', [])
    for s in sessions:
        if session_id in s.get('session_id', ''):
            print(f"找到会话: {s.get('session_id')}")
            print(f"消息数: {s.get('total_messages', 0)}")
            print(f"知识库调用: {s.get('kb_calls', 0)}")
