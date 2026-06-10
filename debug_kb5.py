from agent_service import get_agent_service
from orchestrator import create_context, IntentType

service = get_agent_service()

# 模拟Round 1后的上下文
context = create_context('debug_session_3')
context.short_term_memory.main_symptom = '失眠'
context.current_intent = IntentType.HEALTH_CONSULT

# 直接调用推荐方法
query = '有什么产品推荐吗'
print(f'Query: {query}')
print(f'Context symptom: {context.short_term_memory.main_symptom}')

# 构建查询（复制_generate_product_recommendation的逻辑）
search_query = query
if context.short_term_memory and context.short_term_memory.main_symptom:
    search_query += f" {context.short_term_memory.main_symptom}"

print(f'Search query: {search_query}')

# 检索
results = service.product_retriever.retrieve(search_query, top_k=3)
print(f'Results: {len(results)}')
for r in results:
    print(f'  - {r.product_id}: {r.score}')
