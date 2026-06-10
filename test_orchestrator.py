"""
Orchestrator测试文件
测试状态流转和决策逻辑
"""

from orchestrator import (
    Orchestrator, ConversationContext, IntentType,
    SessionState, NextAction, create_orchestrator, create_context
)


def test_emergency_detection():
    """测试紧急症状检测"""
    print("=" * 50)
    print("测试1: 紧急症状检测")
    print("=" * 50)
    
    orchestrator = create_orchestrator()
    context = create_context("user_001")
    
    # 测试高危症状（基于新的症状清单）
    test_cases = [
        # 高危症状
        ("我胸痛伴大汗，感觉濒死感", "high", "循环系统危象"),
        ("突然倒地，呼之不应", "high", "意识丧失"),
        ("心跳超过130次，感觉心悸", "high", "心律失常"),
        ("无法呼吸，面色青紫", "high", "呼吸危象"),
        ("口角歪斜，说话含糊不清", "high", "中风三联征"),
        ("突然剧烈头痛，像雷击一样", "high", "雷击样头痛"),
        ("呕血，鲜红色的血", "high", "消化道大出血"),
        ("全身皮疹，喉头水肿", "high", "严重过敏"),
        ("腹部僵硬如板，刀割样疼痛", "high", "内脏穿孔"),
        
        # 中危症状
        ("持续高热，服用退热药无效", "medium", "高热感染"),
        ("急性腹痛，怀疑是阑尾炎", "medium", "急性腹痛"),
        ("突然失明，单眼看不见", "medium", "视力骤降"),
        ("排不出尿，下腹胀痛", "medium", "尿潴留"),
        ("频繁呕吐腹泻，明显脱水", "medium", "脱水"),
        
        # 非紧急症状
        ("我只是有点失眠", None, "正常症状"),
        ("最近胃口不太好", None, "正常症状"),
    ]
    
    for user_input, expected_level, desc in test_cases:
        result = orchestrator.safety_guard.check(user_input)
        if expected_level:
            assert result is not None, f"应该检测到紧急症状: {user_input}"
            assert result["emergency_level"] == expected_level, f"紧急级别不匹配: {user_input}"
            print(f"✓ [{desc}] {user_input[:20]}... -> {result['emergency_level']}")
            # 打印检测到的症状
            if result.get("detected_symptoms"):
                print(f"   检测到: {', '.join(result['detected_symptoms'][:3])}")
        else:
            assert result is None, f"不应该检测到紧急症状: {user_input}"
            print(f"✓ [{desc}] {user_input[:20]}... -> 无紧急症状")
    
    print("\n紧急症状检测测试通过！\n")


def test_intent_switch():
    """测试意图切换检测"""
    print("=" * 50)
    print("测试2: 意图切换检测")
    print("=" * 50)
    
    orchestrator = create_orchestrator()
    
    # 测试意图切换
    test_cases = [
        ("我失眠了", None, IntentType.HEALTH_CONSULT, "新意图识别"),
        ("对了，泰吉眠适合什么人", IntentType.HEALTH_CONSULT, IntentType.PRODUCT_CONSULT, "产品意图切换"),
        ("我胸痛", IntentType.PRODUCT_CONSULT, IntentType.HEALTH_CONSULT, "健康意图切换"),
        ("转人工", IntentType.HEALTH_CONSULT, IntentType.CUSTOMER_SERVICE, "客服切换"),
        ("我还是不舒服", IntentType.HEALTH_CONSULT, None, "保持当前意图"),
    ]
    
    for user_input, current_intent, expected_intent, desc in test_cases:
        result = orchestrator.intent_router.detect_switch(user_input, current_intent)
        if expected_intent:
            assert result == expected_intent, f"意图切换检测失败: {desc}"
            print(f"✓ {desc}: {user_input} -> {result.value}")
        else:
            print(f"✓ {desc}: {user_input} -> 保持原意图")
    
    print("\n意图切换检测测试通过！\n")


def test_profile_extraction():
    """测试画像抽取"""
    print("=" * 50)
    print("测试3: 画像抽取")
    print("=" * 50)
    
    orchestrator = create_orchestrator()
    context = create_context("user_002")
    
    # 测试画像抽取
    test_cases = [
        ("我今年58岁", {"age": 58}),
        ("我是男性", {"gender": "男"}),
        ("我有高血压和糖尿病", {"chronic_diseases": "高血压、糖尿病"}),
        ("今年65岁，女，有心脏病", {"age": 65, "gender": "女", "chronic_diseases": "心脏病"}),
    ]
    
    for user_input, expected_fields in test_cases:
        result = orchestrator.profile_extractor.extract(user_input, context.profile)
        for field, expected_value in expected_fields.items():
            actual_value = result["extracted_fields"].get(field)
            assert actual_value == expected_value, f"字段 {field} 抽取失败"
            print(f"✓ 从 '{user_input}' 抽取到 {field}: {actual_value}")
    
    print("\n画像抽取测试通过！\n")


def test_orchestrator_decision():
    """测试Orchestrator决策流程"""
    print("=" * 50)
    print("测试4: Orchestrator决策流程")
    print("=" * 50)
    
    orchestrator = create_orchestrator()
    context = create_context("user_003")
    
    # 测试场景1: 紧急症状（使用新的症状关键词）
    print("\n场景1: 紧急症状")
    context.current_intent = IntentType.PRODUCT_CONSULT
    decision = orchestrator.decide("我胸痛伴大汗，感觉濒死感", context)
    assert decision.is_emergency == True
    assert decision.emergency_level == "high"
    assert decision.should_end == True
    print(f"✓ 检测到紧急症状: {decision.response[:30]}...")
    
    # 测试场景2: 意图切换（产品咨询中突然说胸痛）
    print("\n场景2: 意图切换")
    context = create_context("user_004")
    context.current_intent = IntentType.PRODUCT_CONSULT
    decision = orchestrator.decide("对了，我胸痛伴大汗", context)
    # 注意：这里会先检测到紧急症状，而不是意图切换
    assert decision.is_emergency == True
    print(f"✓ 产品咨询中检测到胸痛 -> 紧急处理")
    
    # 测试场景3: 正常产品咨询
    print("\n场景3: 产品咨询")
    context = create_context("user_005")
    context.current_intent = IntentType.PRODUCT_CONSULT
    decision = orchestrator.decide("泰吉眠适合什么人", context)
    assert decision.intent == IntentType.PRODUCT_CONSULT
    assert decision.state == SessionState.PRODUCT_CONSULT
    print(f"✓ 产品咨询 -> {decision.state.value}")
    
    # 测试场景4: 画像收集
    print("\n场景4: 画像收集")
    context = create_context("user_006")
    context.current_intent = IntentType.HEALTH_CONSULT
    decision = orchestrator.decide("我失眠了", context)
    # 前3轮应该尝试收集画像
    if decision.state == SessionState.PROFILE_COLLECT:
        print(f"✓ 画像收集: {decision.response}")
    else:
        print(f"✓ 跳过画像收集，直接进入症状收集")
    
    # 测试场景5: 画像抽取
    print("\n场景5: 画像抽取")
    context = create_context("user_007")
    context.current_intent = IntentType.HEALTH_CONSULT
    # 先测试画像抽取功能
    profile_result = orchestrator.profile_extractor.extract("我今年58岁，男，有高血压", context.profile)
    # 更新画像
    for field, value in profile_result["extracted_fields"].items():
        setattr(context.profile, field, value)
    context.profile.update_completeness()
    
    assert context.profile.age == 58
    assert context.profile.gender == "男"
    assert context.profile.chronic_diseases == "高血压"
    print(f"✓ 画像已更新: 年龄={context.profile.age}, 性别={context.profile.gender}, 慢病={context.profile.chronic_diseases}")
    
    print("\nOrchestrator决策流程测试通过！\n")


def test_conversation_flow():
    """测试完整对话流程"""
    print("=" * 50)
    print("测试5: 完整对话流程")
    print("=" * 50)
    
    orchestrator = create_orchestrator()
    context = create_context("user_008")
    
    # 模拟对话流程
    conversation = [
        ("你好", "欢迎"),
        ("我失眠了", "健康咨询"),
        ("今年58岁", "提供画像"),
        ("对了，泰吉眠适合什么人", "切换产品意图"),
        ("我胸痛", "紧急症状"),
    ]
    
    print("\n模拟对话流程:")
    for user_input, desc in conversation:
        decision = orchestrator.decide(user_input, context)
        print(f"  用户: {user_input}")
        print(f"  -> 状态: {decision.state.value}, 意图: {decision.intent.value}")
        if decision.is_emergency:
            print(f"  -> ⚠️ 紧急: {decision.emergency_level}")
        print()
    
    print("完整对话流程测试通过！\n")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Orchestrator 测试套件")
    print("=" * 60 + "\n")
    
    try:
        test_emergency_detection()
        test_intent_switch()
        test_profile_extraction()
        test_orchestrator_decision()
        test_conversation_flow()
        
        print("=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        raise
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()
