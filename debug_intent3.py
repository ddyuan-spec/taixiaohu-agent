from agent_service import get_agent_service
from conversation_logger import get_conversation_logger

service = get_agent_service()
session_id = 'debug_intent_session3'

# Round 1
print('=== Round 1: 我最近总是失眠 ===')
result1 = service.process_message('我最近总是失眠', session_id)
print(f"Intent: {result1['intent']}, Action: {result1['next_action']}, State: {result1['state']}")

# Round 2
print('\n=== Round 2: 有什么产品可以推荐吗？ ===')
result2 = service.process_message('有什么产品可以推荐吗？', session_id)
print(f"Intent: {result2['intent']}, Action: {result2['next_action']}, State: {result2['state']}")
print(f"Recommended products: {result2.get('recommended_products', [])}")

# 检查对话记录
print('\n=== 对话记录 ===')
logger = get_conversation_logger()
session = logger.get_session(session_id)
if session:
    for i, msg in enumerate(session.messages):
        if hasattr(msg, 'message_type'):
            msg_type = msg.message_type.value if hasattr(msg.message_type, 'value') else str(msg.message_type)
            kb_calls = msg.knowledge_base_calls
            llm_calls = msg.llm_calls
        else:
            msg_type = msg.get('message_type', '?')
            kb_calls = msg.get('knowledge_base_calls', [])
            llm_calls = msg.get('llm_calls', [])
        print(f"[{i}] {msg_type}: KB={len(kb_calls)}, LLM={len(llm_calls)}")
        if kb_calls:
            for kb in kb_calls:
                if isinstance(kb, dict):
                    print(f"    KB: query={kb.get('query')}, results={kb.get('results_count')}")
                else:
                    print(f"    KB: query={kb.query}, results={kb.results_count}")
