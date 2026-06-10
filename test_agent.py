"""
泰小虎智能体功能测试
"""

from agent import TaiXiaoHuAgent

def test_all():
    print("=" * 60)
    print("🐯 泰小虎智能体功能测试")
    print("=" * 60)

    agent = TaiXiaoHuAgent()
    errors = []

    # 1. 欢迎消息
    print("\n--- 1. 欢迎消息 ---")
    w = agent.get_welcome_message()
    assert "泰小虎" in w, "欢迎消息缺少名称"
    print(f"✓ 欢迎消息: {w[:30]}...")

    # 2. 意图选项
    print("\n--- 2. 意图选项 ---")
    opts = agent.get_intent_options()
    assert len(opts) == 4, f"意图选项应为4个，实际{len(opts)}"
    for o in opts:
        print(f"  ✓ {o['code']}: {o['label']}")
    assert opts[0]['code'] == 'health_consult'

    # 3. 健康咨询（多轮症状分析）
    print("\n--- 3. 健康咨询（多轮症状分析） ---")
    r = agent.process_message("", intent="health_consult")
    assert r['state'] == 'symptom_analysis'
    print(f"  引导: {r['response'][:40]}...")

    r = agent.process_message("我最近膝盖疼")
    assert r['state'] == 'symptom_analysis'
    print(f"  第1轮: {r['response'][:40]}...")

    r = agent.process_message("大概两周了，大概5分")
    print(f"  第2轮: {r['response'][:40]}...")

    r = agent.process_message("有时候腰也有点酸")
    print(f"  第3轮: {r['response'][:40]}...")

    r = agent.process_message("没有慢性病，没在吃药")
    assert r['state'] == 'product_recommend'
    assert '症状总结' in r['response']
    print(f"  总结: {r['response'][:60]}...")
    print("  ✓ 多轮症状分析 + 产品推荐 正常")

    # 4. 紧急症状
    print("\n--- 4. 紧急症状检测 ---")
    agent.clear_session()
    r = agent.process_message("我突然胸痛很厉害")
    assert "120" in r['response']
    print(f"  ✓ 紧急响应: {r['response'][:40]}...")

    # 5. 产品咨询
    print("\n--- 5. 产品咨询 ---")
    agent.clear_session()
    r = agent.process_message("", intent="product_consult")
    assert r['state'] == 'product_consult'
    print(f"  引导: {r['response'][:40]}...")

    r = agent.process_message("我想买保护关节的保健品")
    assert '氨糖' in r['response'] or '关节' in r['response']
    print(f"  推荐: {r['response'][:60]}...")
    print("  ✓ 产品咨询 + 推荐 正常")

    # 6. 健康知识
    print("\n--- 6. 健康知识问答 ---")
    agent.clear_session()
    r = agent.process_message("", intent="knowledge_query")
    assert r['state'] == 'knowledge_qa'

    r = agent.process_message("血压多少算正常")
    assert '血压' in r['response']
    print(f"  回答: {r['response'][:60]}...")
    print("  ✓ 健康知识问答 正常")

    # 7. 边界处理
    print("\n--- 7. 边界处理 ---")
    agent.clear_session()
    r = agent.process_message("", intent="other")
    r = agent.process_message("今天天气不错")
    assert "健康" in r['response']
    print(f"  闲聊: {r['response'][:40]}...")

    agent.clear_session()
    r = agent.process_message("", intent="other")
    r = agent.process_message("我要投诉你们的产品")
    assert "抱歉" in r['response'] or "客服" in r['response']
    print(f"  投诉: {r['response'][:40]}...")
    print("  ✓ 边界处理 正常")

    # 8. 客服转接
    print("\n--- 8. 客服转接 ---")
    agent.clear_session()
    r = agent.process_message("我要转人工客服")
    assert "转接" in r['response'] or "客服" in r['response']
    print(f"  ✓ 转接: {r['response'][:40]}...")

    # 9. 免责声明
    print("\n--- 9. 免责声明触发 ---")
    agent.clear_session()
    r = agent.process_message("我头疼")
    assert "温馨提示" in r['response']
    print(f"  ✓ 免责声明已附加")

    # 10. 画像收集
    print("\n--- 10. 画像收集 ---")
    agent.clear_session()
    agent.start_profile_collect()
    r = agent.process_message("我今年58岁，女性")
    assert agent.user_profile.age == 58
    assert agent.user_profile.gender == "女"
    r = agent.process_message("有高血压，关注血压和睡眠")
    assert "高血压" in agent.user_profile.chronic_diseases
    print(f"  ✓ 画像完整度: {agent.user_profile.completeness:.0%}")

    # 11. 统计信息
    print("\n--- 11. 统计信息 ---")
    stats = agent.get_stats()
    print(f"  名称: {stats['name']}")
    print(f"  消息数: {stats['total_messages']}")
    print(f"  画像: {stats['profile']['completeness']:.0%}")

    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)

if __name__ == "__main__":
    test_all()
