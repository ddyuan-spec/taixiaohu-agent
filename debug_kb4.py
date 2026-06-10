from agent_service import get_agent_service
from orchestrator import create_context, IntentType

service = get_agent_service()

# 创建上下文
context = create_context('test')
context.short_term_memory.main_symptom = '失眠'
context.current_intent = IntentType.HEALTH_CONSULT

print('=== Before _generate_product_recommendation ===')
print(f'_current_kb_calls: {service._current_kb_calls}')

# 直接调用推荐方法
result = service._generate_product_recommendation('有什么产品推荐吗', context, 'test_session')

print('\n=== After _generate_product_recommendation ===')
print(f'_current_kb_calls: {service._current_kb_calls}')
print(f'result: {result}')
