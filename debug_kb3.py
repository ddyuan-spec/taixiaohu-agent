from agent_service import get_agent_service
from product_retriever import create_product_retriever

service = get_agent_service()
retriever = create_product_retriever()

# 测试检索
query = "失眠 有什么产品推荐吗"
print(f'Query: {query}')
results = retriever.retrieve(query, top_k=3)
print(f'Results: {len(results)}')
for r in results:
    print(f'  - {r.product_id}: {r.score}')

# 测试带症状的检索
query2 = "失眠"
print(f'\nQuery: {query2}')
results2 = retriever.retrieve(query2, top_k=3)
print(f'Results: {len(results2)}')
for r in results2:
    print(f'  - {r.product_id}: {r.score}')
