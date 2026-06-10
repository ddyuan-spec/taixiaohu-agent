from agent_service import get_agent_service

service = get_agent_service()

from orchestrator import create_context, IntentType
context = create_context('test')
context.short_term_memory.main_symptom = '失眠'
context.current_intent = IntentType.HEALTH_CONSULT

print('=== Before process_message ===')
print(f'_current_kb_calls: {service._current_kb_calls}')

result = service.process_message('有什么产品推荐吗', 'debug_session')
print('=== After process_message ===')
print(f"Intent: {result['intent']}")
print(f"Action: {result['next_action']}")
