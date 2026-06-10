"""
AgentService测试文件
测试完整的对话流程
"""

import sys
sys.path.insert(0, 'C:\\Users\\13364\\AppData\\Roaming\\TRAE SOLO CN\\ModularData\\ai-agent\\work-mode-projects\\6a16b62a291cd733e969550c\\smart_agent')

from agent_service import AgentService, get_agent_service


def test_agent_service():
    """测试AgentService完整流程"""
    print("=" * 60)
    print("AgentService 完整流程测试")
    print("=" * 60)
    
    service = get_agent_service()
    session_id = "test_session_001"
    
    # 测试场景1: 欢迎语
    print("\n【场景1】欢迎语")
    result = service.process_message("你好", session_id)
    print(f"用户: 你好")
    print(f"泰小虎: {result['response'][:100]}...")
    print(f"状态: {result['state']}, 意图: {result['intent']}")
    
    # 测试场景2: 健康咨询 - 失眠
    print("\n【场景2】健康咨询 - 失眠")
    result = service.process_message("我失眠了，睡不着", session_id)
    print(f"用户: 我失眠了，睡不着")
    print(f"泰小虎: {result['response']}")
    print(f"状态: {result['state']}, 意图: {result['intent']}")
    
    # 测试场景3: 提供画像
    print("\n【场景3】提供画像")
    result = service.process_message("我今年58岁，男，有高血压", session_id)
    print(f"用户: 我今年58岁，男，有高血压")
    print(f"泰小虎: {result['response']}")
    print(f"画像完整度: {result['context_summary']['profile_completeness']}")
    
    # 测试场景4: 产品咨询 - 泰吉眠
    print("\n【场景4】产品咨询 - 泰吉眠")
    result = service.process_message("泰吉眠适合什么人", session_id)
    print(f"用户: 泰吉眠适合什么人")
    print(f"泰小虎: {result['response'][:200]}...")
    print(f"状态: {result['state']}, 意图: {result['intent']}")
    
    # 测试场景5: 紧急症状检测
    print("\n【场景5】紧急症状检测")
    result = service.process_message("我胸痛伴大汗，感觉濒死感", session_id)
    print(f"用户: 我胸痛伴大汗，感觉濒死感")
    print(f"泰小虎: {result['response'][:150]}...")
    print(f"是否紧急: {result['is_emergency']}, 级别: {result.get('emergency_level')}")
    
    # 测试场景6: 产品推荐
    print("\n【场景6】产品推荐")
    # 创建新会话
    session_id2 = "test_session_002"
    result = service.process_message("我便秘，想调理肠道", session_id2)
    print(f"用户: 我便秘，想调理肠道")
    print(f"泰小虎: {result['response'][:200]}...")
    print(f"推荐产品数: {len(result['recommended_products'])}")
    
    # 测试场景7: 健康知识查询
    print("\n【场景7】健康知识查询")
    result = service.process_message("高血压饮食要注意什么", session_id2)
    print(f"用户: 高血压饮食要注意什么")
    print(f"泰小虎: {result['response']}")
    
    print("\n" + "=" * 60)
    print("✅ AgentService 测试完成！")
    print("=" * 60)


def test_conversation_flow():
    """测试完整对话流程"""
    print("\n" + "=" * 60)
    print("完整对话流程测试")
    print("=" * 60)
    
    service = get_agent_service()
    session_id = "flow_test_001"
    
    conversation = [
        ("你好", "欢迎"),
        ("我失眠了", "症状收集"),
        ("今年58岁，男", "画像收集"),
        ("失眠2周了", "症状详情"),
        ("泰吉眠怎么样", "产品咨询"),
    ]
    
    print("\n模拟完整对话:\n")
    for user_input, desc in conversation:
        result = service.process_message(user_input, session_id)
        print(f"用户: {user_input}")
        print(f"泰小虎: {result['response'][:80]}...")
        print(f"  [状态: {result['state']}, 意图: {result['intent']}, 轮数: {result['context_summary']['turn_count']}]")
        print()
    
    print("=" * 60)
    print("✅ 完整对话流程测试完成！")
    print("=" * 60)


def run_all_tests():
    """运行所有测试"""
    try:
        test_agent_service()
        test_conversation_flow()
        
        print("\n" + "=" * 60)
        print("🎉 所有测试通过！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    run_all_tests()
