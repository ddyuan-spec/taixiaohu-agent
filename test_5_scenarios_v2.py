"""
5个多轮对话测试场景 + 特殊伴侣对话场景
包含：健康咨询、产品推荐、产品追问、意图切换
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
        time.sleep(0.2)
    
    return session_id

def main():
    print("=" * 70)
    print("泰小虎 - 5个多轮对话测试场景 + 特殊场景")
    print("=" * 70)
    
    # 检查LLM连接
    service = AgentService()
    conn = service.test_llm_connection()
    print(f"\nLLM连接: {conn.get('success')} - {conn.get('message', '')}")
    if not conn.get('success'):
        print("⚠️ LLM未连接！")
        return
    
    sessions = []
    timestamp = int(time.time())
    
    # 场景1：失眠女性 - 画像→推荐→追问→换产品
    sessions.append(run_scenario(
        f"scenario_1_{timestamp}",
        "场景1：失眠女性完整咨询流程",
        [
            "你好，我今年42岁，女性",
            "最近总是失眠，睡不好",
            "已经有一个月了",
            "有什么产品可以推荐吗？",
            "泰吉眠有什么功效？",
            "还有其他助眠产品吗？",
            "智忆高是什么？",
            "好的，我先试试泰吉眠"
        ]
    ))
    
    # 场景2：便秘男性 - 多产品推荐
    sessions.append(run_scenario(
        f"scenario_2_{timestamp}",
        "场景2：便秘男性多产品推荐",
        [
            "我今年38岁，男性",
            "经常便秘，消化不好",
            "有什么适合我的产品？",
            "泰美畅有什么功效？",
            "智忆高对消化有帮助吗？",
            "那安美来呢？"
        ]
    ))
    
    # 场景3：记忆力问题 - 画像→推荐→追问→确认
    sessions.append(run_scenario(
        f"scenario_3_{timestamp}",
        "场景3：记忆力问题咨询",
        [
            "我今年50岁，最近记忆力下降",
            "经常忘事，记性不好",
            "有什么产品可以改善？",
            "智忆高适合我吗？",
            "怎么服用？",
            "有什么禁忌？",
            "好的，我了解一下"
        ]
    ))
    
    # 场景4：综合健康 - 多症状多产品
    sessions.append(run_scenario(
        f"scenario_4_{timestamp}",
        "场景4：综合健康多产品推荐",
        [
            "我今年45岁，女性",
            "睡眠不好，经常失眠",
            "而且皮肤状态也不好",
            "有什么产品可以推荐？",
            "泰吉眠和安美来哪个更适合我？",
            "可以同时服用吗？",
            "好的，我先买泰吉眠试试"
        ]
    ))
    
    # 场景5：男性压力大 - 画像→建议→推荐
    sessions.append(run_scenario(
        f"scenario_5_{timestamp}",
        "场景5：男性压力大咨询",
        [
            "你好，我今年35岁，男性",
            "工作压力大，经常焦虑",
            "睡眠质量也不好",
            "有什么方法可以改善？",
            "有什么产品推荐吗？",
            "泰吉眠和智忆高有什么区别？",
            "那我选泰吉眠吧"
        ]
    ))
    
    # 特殊场景：用户失眠→伴侣问题→推荐产品→追问
    sessions.append(run_scenario(
        f"special_partner_{timestamp}",
        "【特殊场景】用户失眠→伴侣便秘→推荐产品→追问",
        [
            "你好，我今年40岁，男性",
            "我最近总是失眠，睡不好",
            "有什么产品可以推荐吗？",
            "泰吉眠有什么副作用吗？",
            "对了，我妻子最近便秘很严重",
            "她今年38岁",
            "有什么产品适合她吗？",
            "泰美畅效果怎么样？",
            "需要服用多久才能见效？",
            "好的，我让她试试"
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
    
    print(f"会话数: {len(sessions)}")
    print(f"LLM调用次数: {llm_calls}")
    print(f"知识库调用次数: {kb_calls}")
    print(f"总Token消耗: {total_tokens}")
    
    print(f"\n{'='*70}")
    print("测试完成！请在后台查看对话记录")
    print("http://localhost:5000/admin/conversations")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
