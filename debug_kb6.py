from agent_service import get_agent_service

service = get_agent_service()

# 模拟完整对话流程
session_id = 'debug_session_4'

# 第一轮：建立健康咨询意图
print('=== Round 1: 失眠症状 ===')
result1 = service.process_message('我最近总是失眠', session_id)
print(f"Intent: {result1['intent']}, Action: {result1['next_action']}, State: {result1['state']}")

# 获取上下文
context = service.sessions.get(session_id)
if context:
    print(f"Context symptom: {context.short_term_memory.main_symptom if context.short_term_memory else 'None'}")
    print(f"Context intent: {context.current_intent}")
else:
    print("Context not found!")

# 第二轮：用户要求推荐
print('\n=== Round 2: 要求推荐 ===')
# 先检查调用前的状态
print(f"Before process_message: _current_kb_calls={service._current_kb_calls}")

result2 = service.process_message('有什么产品推荐吗', session_id)
print(f"Intent: {result2['intent']}, Action: {result2['next_action']}, State: {result2['state']}")
print(f"Recommended products: {result2.get('recommended_products', [])}")
