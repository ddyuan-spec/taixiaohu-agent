"""
完整场景测试 - 修复后的对话流程
"""
import sys, time
sys.path.insert(0, '.')

from agent_service import AgentService
from conversation_logger import get_conversation_logger

def run_test(session_id, title, messages):
    """运行单个测试场景"""
    print(f"\n{'='*60}")
    print(f"【{title}】")
    print(f"{'='*60}")
    
    service = AgentService()
    
    for msg in messages:
        print(f"\n>>> 用户: {msg}")
        result = service.process_message(msg, session_id)
        resp = result['response']
        # 截断过长回复
        if len(resp) > 200:
            resp = resp[:200] + "..."
        print(f"<<< 泰小虎: {resp}")
        print(f"    [意图: {result['intent']}] [动作: {result['next_action']}] [状态: {result['state']}]")
        if result.get('recommended_products'):
            names = [p.get('product_name', p.get('product_id', '')) for p in result['recommended_products']]
            print(f"    [推荐产品: {names}]")
        time.sleep(0.5)
    
    return session_id


def main():
    print("=" * 60)
    print("泰小虎 - 修复后完整场景测试")
    print("=" * 60)
    
    # 先测试LLM连接
    service = AgentService()
    status = service.get_llm_status()
    print(f"\nLLM状态: enabled={status['enabled']}, model={status['model']}")
    
    conn = service.test_llm_connection()
    print(f"连接测试: {conn.get('success')} - {conn.get('message', '')}")
    
    if not conn.get('success'):
        print("\n⚠️ LLM未连接，请检查API Key！")
        return
    
    # 场景1：画像收集
    run_test(
        f"fix_test_profile_{int(time.time())}",
        "场景1：画像收集 - 用户描述身体情况",
        [
            "我最近总是失眠，晚上翻来覆去睡不着",
            "大概有两三周了",
            "工作压力比较大，经常加班到很晚"
        ]
    )
    
    # 场景2：健康建议 → 用户接受推荐
    run_test(
        f"fix_test_accept_{int(time.time())}",
        "场景2：健康建议 → 用户接受产品推荐",
        [
            "我最近总是睡不着，失眠很严重",
            "有什么产品可以推荐给我吗？",
            "好的，泰吉眠怎么服用？"
        ]
    )
    
    # 场景3：健康建议 → 用户拒绝推荐
    run_test(
        f"fix_test_refuse_{int(time.time())}",
        "场景3：健康建议 → 用户拒绝产品推荐",
        [
            "最近总是睡不着，失眠",
            "我先不想买产品，有其他方法吗？"
        ]
    )
    
    # 场景4：追问产品信息
    run_test(
        f"fix_test_inquiry_{int(time.time())}",
        "场景4：追问产品详细信息",
        [
            "泰吉眠有什么功效？",
            "怎么服用？一次吃几片？",
            "有什么禁忌吗？孕妇能吃吗？"
        ]
    )
    
    # 场景5：完整流程 - 画像收集→推荐→追问
    run_test(
        f"fix_test_full_{int(time.time())}",
        "场景5：完整流程 - 画像→推荐→追问→接受",
        [
            "我今年45岁，女性，最近总是失眠",
            "有高血压，在吃降压药",
            "有什么适合我的产品吗？",
            "泰吉眠我这种情况能吃吗？",
            "好的，那我试试"
        ]
    )
    
    # 打印LLM统计
    print(f"\n{'='*60}")
    print("【LLM调用统计】")
    print(f"{'='*60}")
    
    logger = get_conversation_logger()
    total_calls = 0
    total_tokens = 0
    total_time = 0
    
    for session in logger.sessions.values():
        if session.session_id.startswith("fix_test_"):
            for msg in session.messages:
                llm_calls = msg.get('llm_calls', []) if isinstance(msg, dict) else (msg.llm_calls if hasattr(msg, 'llm_calls') else [])
                for call in llm_calls:
                    if isinstance(call, dict):
                        total_calls += 1
                        total_tokens += call.get('total_tokens', 0)
                        total_time += call.get('response_time_ms', 0)
    
    print(f"测试场景LLM调用次数: {total_calls}")
    print(f"总Token消耗: {total_tokens}")
    if total_calls > 0:
        print(f"平均响应时间: {total_time / total_calls:.0f}ms")
    
    print(f"\n{'='*60}")
    print("测试完成！请在后台查看对话记录")
    print("http://localhost:5000/admin/conversations")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
