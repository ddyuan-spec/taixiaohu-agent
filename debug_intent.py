from agent_service import get_agent_service
from conversation_logger import get_conversation_logger

service = get_agent_service()
session_id = 'debug_intent_session'

# Round 1
print('=== Round 1: 我最近总是失眠 ===')
result1 = service.process_message('我最近总是失眠', session_id)
print(f"Intent: {result1['intent']}, Action: {result1['next_action']}, State: {result1['state']}")
context = service.sessions.get(session_id)
if context:
    print(f"Context current_intent: {context.current_intent}")
    print(f"Context symptom: {context.short_term_memory.main_symptom if context.short_term_memory else 'None'}")

# Round 2
print('\n=== Round 2: 有什么产品可以推荐吗？ ===')
result2 = service.process_message('有什么产品可以推荐吗？', session_id)
print(f"Intent: {result2['intent']}, Action: {result2['next_action']}, State: {result2['state']}")
if context:
    print(f"Context current_intent: {context.current_intent}")
    print(f"Context symptom: {context.short_term_memory.main_symptom if context.short_term_memory else 'None'}")

# 检查对话记录
print('\n=== 对话记录 ===')
logger = get_conversation_logger()
session = logger.get_session(session_id)
if session:
    for msg in session.messages:
        if isinstance(msg, dict):
            kb_calls = msg.get('knowledge_base_calls', [])
            llm_calls = msg.get('llm_calls', [])
        else:
            kb_calls = msg.knowledge_base_calls if hasattr(msg, 'knowledge_base_calls') else []
            llm_calls = msg.llm_calls if hasattr(msg, 'llm_calls') else []
        print(f"[{msg.get('message_type', msg.message_type if hasattr(msg, 'message_type') else '?')}] KB: {len(kb_calls)}, LLM: {len(llm_calls)}")
