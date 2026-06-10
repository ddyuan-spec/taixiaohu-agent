from agent_service import get_agent_service

service = get_agent_service()
session_id = 'debug_round5'

# 模拟场景3的前4轮
print('=== Round 1: 我最近总是失眠 ===')
result1 = service.process_message('我最近总是失眠', session_id)
print(f"Intent: {result1['intent']}, Action: {result1['next_action']}")

print('\n=== Round 2: 有什么方法可以改善？ ===')
result2 = service.process_message('有什么方法可以改善？', session_id)
print(f"Intent: {result2['intent']}, Action: {result2['next_action']}")

print('\n=== Round 3: 我先不想买产品，有其他建议吗？ ===')
result3 = service.process_message('我先不想买产品，有其他建议吗？', session_id)
print(f"Intent: {result3['intent']}, Action: {result3['next_action']}")

print('\n=== Round 4: 那泰吉眠是什么产品？ ===')
result4 = service.process_message('那泰吉眠是什么产品？', session_id)
print(f"Intent: {result4['intent']}, Action: {result4['next_action']}")
print(f"Response: {result4['response'][:100]}...")

print('\n=== Round 5: 有什么功效？ ===')
result5 = service.process_message('有什么功效？', session_id)
print(f"Intent: {result5['intent']}, Action: {result5['next_action']}")
print(f"Response: {result5['response']}")

# 检查上下文
context = service.sessions.get(session_id)
if context:
    print(f"\nContext symptom: {context.short_term_memory.main_symptom if context.short_term_memory else 'None'}")
    print(f"Context intent: {context.current_intent}")
