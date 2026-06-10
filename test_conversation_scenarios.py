"""
对话记录测试用例
场景：用户健康咨询（睡不着）→ 推荐泰吉眠 → 追问功效/服用方式/禁忌
"""

import sys
sys.path.insert(0, '.')

from agent_service import AgentService
from conversation_logger import get_conversation_logger

def test_scenario_1():
    """
    测试场景1：失眠咨询 → 推荐泰吉眠 → 追问功效
    """
    print("=" * 60)
    print("测试场景1：失眠咨询 → 推荐泰吉眠 → 追问功效")
    print("=" * 60)
    
    service = AgentService()
    session_id = "test_scenario_1"
    
    # 第1轮：用户说睡不着
    print("\n【第1轮】用户：我最近睡不着，失眠")
    result1 = service.process_message("我最近睡不着，失眠", session_id)
    print(f"泰小虎：{result1['response'][:150]}...")
    print(f"状态：{result1['state']}，意图：{result1['intent']}")
    
    # 第2轮：用户确认症状
    print("\n【第2轮】用户：是的，已经持续一周了")
    result2 = service.process_message("是的，已经持续一周了", session_id)
    print(f"泰小虎：{result2['response'][:150]}...")
    print(f"状态：{result2['state']}，意图：{result2['intent']}")
    
    # 第3轮：用户问有什么产品推荐
    print("\n【第3轮】用户：有什么产品可以帮我改善睡眠吗？")
    result3 = service.process_message("有什么产品可以帮我改善睡眠吗？", session_id)
    print(f"泰小虎：{result3['response'][:200]}...")
    print(f"状态：{result3['state']}，意图：{result3['intent']}")
    print(f"推荐产品：{result3.get('recommended_products', [])}")
    
    # 第4轮：用户追问泰吉眠的功效
    print("\n【第4轮】用户：泰吉眠有什么功效？")
    result4 = service.process_message("泰吉眠有什么功效？", session_id)
    print(f"泰小虎：{result4['response'][:200]}...")
    print(f"状态：{result4['state']}，意图：{result4['intent']}")
    
    return session_id


def test_scenario_2():
    """
    测试场景2：直接询问泰吉眠 → 追问服用方式 → 追问禁忌
    """
    print("\n" + "=" * 60)
    print("测试场景2：直接询问泰吉眠 → 追问服用方式 → 追问禁忌")
    print("=" * 60)
    
    service = AgentService()
    session_id = "test_scenario_2"
    
    # 第1轮：直接问泰吉眠
    print("\n【第1轮】用户：泰吉眠是什么产品？")
    result1 = service.process_message("泰吉眠是什么产品？", session_id)
    print(f"泰小虎：{result1['response'][:150]}...")
    print(f"状态：{result1['state']}，意图：{result1['intent']}")
    
    # 第2轮：追问服用方式
    print("\n【第2轮】用户：怎么服用？")
    result2 = service.process_message("怎么服用？", session_id)
    print(f"泰小虎：{result2['response'][:150]}...")
    print(f"状态：{result2['state']}，意图：{result2['intent']}")
    
    # 第3轮：追问禁忌
    print("\n【第3轮】用户：有什么禁忌吗？")
    result3 = service.process_message("有什么禁忌吗？", session_id)
    print(f"泰小虎：{result3['response'][:150]}...")
    print(f"状态：{result3['state']}，意图：{result3['intent']}")
    
    return session_id


def test_scenario_3():
    """
    测试场景3：老年人失眠 → 推荐泰吉眠 → 询问是否适合
    """
    print("\n" + "=" * 60)
    print("测试场景3：老年人失眠 → 推荐泰吉眠 → 询问是否适合")
    print("=" * 60)
    
    service = AgentService()
    session_id = "test_scenario_3"
    
    # 第1轮：老年人说失眠
    print("\n【第1轮】用户：我今年65岁了，晚上总是睡不着")
    result1 = service.process_message("我今年65岁了，晚上总是睡不着", session_id)
    print(f"泰小虎：{result1['response'][:150]}...")
    print(f"状态：{result1['state']}，意图：{result1['intent']}")
    
    # 第2轮：用户问推荐什么
    print("\n【第2轮】用户：有什么适合我的产品吗？")
    result2 = service.process_message("有什么适合我的产品吗？", session_id)
    print(f"泰小虎：{result2['response'][:200]}...")
    print(f"状态：{result2['state']}，意图：{result2['intent']}")
    print(f"推荐产品：{result2.get('recommended_products', [])}")
    
    # 第3轮：用户问是否适合老年人
    print("\n【第3轮】用户：泰吉眠适合老年人吃吗？")
    result3 = service.process_message("泰吉眠适合老年人吃吗？", session_id)
    print(f"泰小虎：{result3['response'][:150]}...")
    print(f"状态：{result3['state']}，意图：{result3['intent']}")
    
    return session_id


def print_conversation_log(session_id):
    """打印对话记录"""
    print("\n" + "=" * 60)
    print(f"对话记录详情：{session_id}")
    print("=" * 60)
    
    logger = get_conversation_logger()
    session = logger.get_session(session_id)
    
    if not session:
        print("未找到对话记录")
        return
    
    print(f"\n会话ID：{session.session_id}")
    print(f"开始时间：{session.started_at}")
    print(f"总消息数：{session.total_messages}")
    print(f"用户画像：{session.user_profile}")
    
    print("\n--- 对话内容 ---")
    for msg in session.messages:
        print(f"\n[{msg.message_type.upper()}] {msg.timestamp}")
        print(f"内容：{msg.content[:100]}...")
        
        if msg.intent:
            print(f"意图：{msg.intent} (置信度: {msg.intent_confidence})")
        if msg.state:
            print(f"状态：{msg.state}")
        if msg.recommended_products:
            print(f"推荐产品：{msg.recommended_products}")
        
        if msg.knowledge_base_calls:
            print("知识库调用：")
            for call in msg.knowledge_base_calls:
                print(f"  - 查询：{call.query}")
                print(f"    结果数：{call.results_count}，耗时：{call.response_time_ms}ms")


def main():
    print("\n" + "=" * 60)
    print("泰小虎对话记录系统测试")
    print("=" * 60)
    
    # 执行三个测试场景
    session1 = test_scenario_1()
    session2 = test_scenario_2()
    session3 = test_scenario_3()
    
    # 打印对话记录
    print("\n\n" + "=" * 60)
    print("查看对话记录")
    print("=" * 60)
    
    print_conversation_log(session1)
    print_conversation_log(session2)
    print_conversation_log(session3)
    
    # 打印知识库统计
    print("\n" + "=" * 60)
    print("知识库调用统计")
    print("=" * 60)
    
    logger = get_conversation_logger()
    stats = logger.get_knowledge_base_stats()
    print(f"\n总调用次数：{stats['total_calls']}")
    print(f"平均响应时间：{stats['avg_response_time_ms']}ms")
    print(f"按意图分布：{stats['calls_by_intent']}")
    print(f"按产品分布：{stats['calls_by_product']}")
    
    print("\n" + "=" * 60)
    print("测试完成！请在后台 /admin/conversations 查看对话记录")
    print("=" * 60)


if __name__ == "__main__":
    main()
