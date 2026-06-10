from agent_service import get_agent_service

service = get_agent_service()
session_id = 'debug_scenario1'

# Round 1
result1 = service.process_message('我今年45岁，女性', session_id)
print(f"Round 1: Intent={result1['intent']}")

# Round 2: 失眠
result2 = service.process_message('最近总是失眠，晚上睡不着', session_id)
print(f"Round 2: Intent={result2['intent']}")
context = service.sessions.get(session_id)
print(f"  Context intent: {context.current_intent}")
print(f"  Symptom: {context.short_term_memory.main_symptom if context.short_term_memory else 'None'}")

# Round 3: 两周
result3 = service.process_message('已经持续两周了', session_id)
print(f"Round 3: Intent={result3['intent']}, Action={result3['next_action']}")
context = service.sessions.get(session_id)
print(f"  Context intent: {context.current_intent}")

# Round 4: 推荐
result4 = service.process_message('有什么产品可以推荐吗？', session_id)
print(f"Round 4: Intent={result4['intent']}, Action={result4['next_action']}")
print(f"  Products: {result4.get('recommended_products', [])}")
