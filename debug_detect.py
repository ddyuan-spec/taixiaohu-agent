from agent_service import get_agent_service

service = get_agent_service()
session_id = 'debug_detect'

# Round 2: 失眠
result2 = service.process_message('最近总是失眠，晚上睡不着', session_id)
print(f"Round 2: Intent={result2['intent']}")

# 检查context
context = service.sessions.get(session_id)
print(f"Context intent: {context.current_intent}")

# 模拟Round 3
user_input = '已经持续两周了'
current_intent = context.current_intent

# 检查Step 2的逻辑
recommend_keywords = ["推荐", "有什么产品", "买什么", "哪个好", "试试", "给我介绍", "有什么适合"]
refuse_keywords = ["不想买", "不需要", "先不买", "不想产品", "不买", "不要产品", "先不考虑", "只想要建议", "有其他方法"]

is_recommend_request = any(kw in user_input for kw in recommend_keywords)
is_refuse_recommend = any(kw in user_input for kw in refuse_keywords)

print(f"\nStep 2 check:")
print(f"  is_recommend_request: {is_recommend_request}")
print(f"  is_refuse_recommend: {is_refuse_recommend}")

# 检查detect_switch
from orchestrator import IntentType, IntentRouter
router = IntentRouter()
switched_intent = router.detect_switch(user_input, current_intent)
print(f"\ndetect_switch result: {switched_intent}")
