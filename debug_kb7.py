from agent_service import get_agent_service

service = get_agent_service()

# 测试症状提取
from orchestrator import create_context, IntentType, Orchestrator

context = create_context('test')
context.current_intent = IntentType.HEALTH_CONSULT

print(f'Before extract: symptom = "{context.short_term_memory.main_symptom}"')

orchestrator = Orchestrator()
orchestrator._extract_symptom('我最近总是失眠', context)

print(f'After extract: symptom = "{context.short_term_memory.main_symptom}"')
