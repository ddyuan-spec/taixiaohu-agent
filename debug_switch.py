from agent_service import get_agent_service

service = get_agent_service()
session_id = 'debug_switch'

# Round 3: 设置症状
print('=== Round 3: 最近睡眠不太好 ===')
result3 = service.process_message('最近睡眠不太好', session_id)
print(f"Intent: {result3['intent']}, Action: {result3['next_action']}")

# 检查意图路由
context = service.sessions.get(session_id)
print(f"Context intent: {context.current_intent}")
print(f"Context symptom: {context.short_term_memory.main_symptom if context.short_term_memory else 'None'}")

# 检查intent_router
from orchestrator import IntentType, IntentRouter
router = IntentRouter()

# 测试detect_switch
user_input = '有什么适合我的产品吗？'
current_intent = context.current_intent
print(f'\nTesting detect_switch:')
print(f"  user_input: {user_input}")
print(f"  current_intent: {current_intent}")

# 检查是否匹配推荐关键词
recommend_keywords = ["推荐", "有什么产品", "买什么", "哪个好", "试试", "给我介绍", "有什么适合"]
print(f"  matches recommend: {any(kw in user_input for kw in recommend_keywords)}")

# 检查detect_switch
switched = router.detect_switch(user_input, current_intent)
print(f"  switched_intent: {switched}")

# 测试_auto_detect_intent
auto_intent = router._auto_detect_intent(user_input)
print(f"  auto_intent: {auto_intent}")
