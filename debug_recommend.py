from agent_service import get_agent_service

service = get_agent_service()
session_id = 'debug_recommend'

# 模拟场景1的前3轮
print('=== Round 1: 你好，我今年42岁，女性 ===')
result1 = service.process_message('你好，我今年42岁，女性', session_id)
print(f"Intent: {result1['intent']}, Action: {result1['next_action']}")

print('\n=== Round 2: 最近总是失眠，睡不好 ===')
result2 = service.process_message('最近总是失眠，睡不好', session_id)
print(f"Intent: {result2['intent']}, Action: {result2['next_action']}")

print('\n=== Round 3: 已经有一个月了 ===')
result3 = service.process_message('已经有一个月了', session_id)
print(f"Intent: {result3['intent']}, Action: {result3['next_action']}")

print('\n=== Round 4: 有什么产品可以推荐吗？ ===')
result4 = service.process_message('有什么产品可以推荐吗？', session_id)
print(f"Intent: {result4['intent']}, Action: {result4['next_action']}")
print(f"Response: {result4['response'][:200]}...")
print(f"Recommended products: {result4.get('recommended_products', [])}")

# 检查上下文
context = service.sessions.get(session_id)
if context:
    print(f"\nContext symptom: {context.short_term_memory.main_symptom if context.short_term_memory else 'None'}")
    print(f"Context age: {context.profile.age}")
    print(f"Context gender: {context.profile.gender}")
