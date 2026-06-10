"""
三条带知识库调用的长对话测试场景
"""
import sys, time
sys.path.insert(0, '.')

from agent_service import AgentService
from conversation_logger import get_conversation_logger

def run_scenario(session_id, title, messages):
    """运行单个测试场景"""
    print(f"\n{'='*70}")
    print(f"【{title}】")
    print(f"{'='*70}")
    
    service = AgentService()
    
    for i, msg in enumerate(messages, 1):
        print(f"\n[Round {i}] 用户: {msg}")
        result = service.process_message(msg, session_id)
        resp = result['response']
        if len(resp) > 150:
            resp = resp[:150] + "..."
        print(f"[Round {i}] 泰小虎: {resp}")
        print(f"        [意图: {result['intent']}] [动作: {result['next_action']}] [状态: {result['state']}]")
        if result.get('recommended_products'):
            names = [p.get('product_name', p.get('product_id', '')) for p in result['recommended_products']]
            print(f"        [推荐产品: {names}]")
        time.sleep(0.3)
    
    return session_id

def main():
    print("=" * 70)
    print("泰小虎 - 带知识库调用的长对话测试场景")
    print("=" * 70)
    
    # 检查LLM连接
    service = AgentService()
    conn = service.test_llm_connection()
    print(f"\nLLM连接: {conn.get('success')} - {conn.get('message', '')}")
    if not conn.get('success'):
        print("⚠️ LLM未连接！")
        return
    
    sessions = []
    
    # 场景1：完整健康咨询流程（画像→建议→推荐→追问→接受）
    sessions.append(run_scenario(
        f"kb_scenario_1_{int(time.time())}",
        "场景1：完整健康咨询流程",
        [
            "我今年45岁，女性",
            "最近总是失眠，晚上睡不着",
            "已经持续两周了",
            "有什么产品可以推荐吗？",
            "泰吉眠有什么功效？",
            "怎么服用？",
            "有什么禁忌吗？",
            "好的，那我试试"
        ]
    ))
    
    # 场景2：高血压患者的健康咨询
    sessions.append(run_scenario(
        f"kb_scenario_2_{int(time.time())}",
        "场景2：高血压患者咨询",
        [
            "我今年55岁，男性",
            "有高血压，在吃降压药",
            "最近睡眠不太好",
            "有什么适合我的产品吗？",
            "泰吉眠高血压患者能吃吗？",
            "和降压药有冲突吗？",
            "好的，我了解一下"
        ]
    ))
    
    # 场景3：用户拒绝推荐后追问产品
    sessions.append(run_scenario(
        f"kb_scenario_3_{int(time.time())}",
        "场景3：拒绝后追问产品信息",
        [
            "我最近总是失眠",
            "有什么方法可以改善？",
            "我先不想买产品，有其他建议吗？",
            "那泰吉眠是什么产品？",
            "有什么功效？",
            "价格是多少？"
        ]
    ))
    
    # 打印统计
    print(f"\n{'='*70}")
    print("【调用统计】")
    print(f"{'='*70}")
    
    logger = get_conversation_logger()
    llm_calls = 0
    kb_calls = 0
    total_tokens = 0
    
    for session in logger.sessions.values():
        if any(s in session.session_id for s in sessions):
            for msg in session.messages:
                if isinstance(msg, dict):
                    llm_calls += len(msg.get('llm_calls', []))
                    kb_calls += len(msg.get('knowledge_base_calls', []))
                    for call in msg.get('llm_calls', []):
                        if isinstance(call, dict):
                            total_tokens += call.get('total_tokens', 0)
    
    print(f"LLM调用次数: {llm_calls}")
    print(f"知识库调用次数: {kb_calls}")
    print(f"总Token消耗: {total_tokens}")
    
    print(f"\n{'='*70}")
    print("测试完成！请在后台查看对话记录")
    print("http://localhost:5000/admin/conversations")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
