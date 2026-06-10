import requests
import json

BASE_URL = "https://taixiaohu-agent-production.up.railway.app"
session_id = "test_fix_001"

print("=== 验证修复效果 ===\n")

# Round 1: 画像收集
print("Round 1: 你好，我今年35岁，男性")
r1 = requests.post(f"{BASE_URL}/api/chat", json={
    "message": "你好，我今年35岁，男性",
    "session_id": session_id
}, timeout=30)
data1 = r1.json()
print(f"Intent: {data1.get('intent')}, State: {data1.get('state')}")
print(f"Response: {data1.get('response', '')[:80]}...")

print("\n" + "="*60 + "\n")

# Round 2: 症状描述
print("Round 2: 最近总是失眠，睡不好")
r2 = requests.post(f"{BASE_URL}/api/chat", json={
    "message": "最近总是失眠，睡不好",
    "session_id": session_id
}, timeout=30)
data2 = r2.json()
print(f"Intent: {data2.get('intent')}, State: {data2.get('state')}")
print(f"Response: {data2.get('response', '')[:80]}...")

print("\n" + "="*60 + "\n")

# Round 3: 要求推荐产品
print("Round 3: 有什么产品可以推荐吗？")
r3 = requests.post(f"{BASE_URL}/api/chat", json={
    "message": "有什么产品可以推荐吗？",
    "session_id": session_id
}, timeout=30)
data3 = r3.json()
print(f"Intent: {data3.get('intent')}, State: {data3.get('state')}")
print(f"Action: {data3.get('next_action')}")
print(f"Products: {data3.get('recommended_products', [])}")
print(f"Response: {data3.get('response', '')[:150]}...")

print("\n" + "="*60 + "\n")

# Round 4: 追问产品（使用指代词"这个产品"）
print("Round 4: 这个产品有什么副作用吗？（测试指代词修复）")
r4 = requests.post(f"{BASE_URL}/api/chat", json={
    "message": "这个产品有什么副作用吗？",
    "session_id": session_id
}, timeout=30)
data4 = r4.json()
print(f"Intent: {data4.get('intent')}, State: {data4.get('state')}")
print(f"Action: {data4.get('next_action')}")
print(f"Response: {data4.get('response', '')}")

# 验证是否成功识别产品
if "抱歉" in data4.get('response', '') or "没有找到" in data4.get('response', ''):
    print("\n❌ 修复失败：仍然无法识别指代产品")
else:
    print("\n✅ 修复成功：正确识别指代产品并回答")

print("\n" + "="*60 + "\n")

# 检查对话记录和知识库调用统计
print("检查对话记录...")
r5 = requests.get(f"{BASE_URL}/api/v2/conversations?limit=10", timeout=10)
if r5.status_code == 200:
    sessions = r5.json().get('sessions', [])
    for s in sessions:
        if session_id in s.get('session_id', ''):
            print(f"✅ 找到会话: {s.get('session_id')}")
            print(f"   消息数: {s.get('total_messages', 0)}")
            print(f"   知识库调用: {s.get('kb_calls', 0)}")
            if s.get('kb_calls', 0) > 0:
                print("✅ 知识库调用统计正常")
            else:
                print("❌ 知识库调用统计仍为0")
