from agent_service import get_agent_service

service = get_agent_service()
session_id = 'scenario2_fix_test'

messages = [
    "我今年55岁，男性",
    "有高血压，在吃降压药",
    "最近睡眠不太好",
    "有什么适合我的产品吗？",
]

for i, msg in enumerate(messages, 1):
    print(f'\n[Round {i}] 用户: {msg}')
    result = service.process_message(msg, session_id)
    print(f'[Round {i}] 泰小虎: {result["response"][:100]}...')
    print(f'        [意图: {result["intent"]}] [动作: {result["next_action"]}] [状态: {result["state"]}]')
    print(f'        [推荐产品: {result.get("recommended_products", [])}]')
    
    # 检查症状
    context = service.sessions.get(session_id)
    if context:
        print(f'        [症状: {context.short_term_memory.main_symptom if context.short_term_memory else "无"}]')
