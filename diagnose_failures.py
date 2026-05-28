#!/usr/bin/env python3
"""诊断所有失败用例的实际回复"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evaluation.evaluator import AgentEvaluator
from evaluation.multi_turn_test_suite_full import MULTI_TURN_TESTS_FULL
from agent import TaiXiaoHuAgent

evaluator = AgentEvaluator(TaiXiaoHuAgent)

for tc in MULTI_TURN_TESTS_FULL:
    agent = TaiXiaoHuAgent()
    all_responses = []
    final_response = ""
    final_intent = None
    
    for role, message in tc.dialogue_sequence:
        if role == "user":
            result = agent.process_message(message)
            final_response = result.get("response", "")
            final_intent = result.get("intent")
            all_responses.append(f"  用户: {message}")
            all_responses.append(f"  AI: {final_response[:120]}")
    
    # 检查期望关键词
    missing = [p for p in tc.expected_patterns if isinstance(p, str) and p not in final_response]
    missing_nested = [p for p in tc.expected_patterns if isinstance(p, list) and not any(sub in final_response for sub in p)]
    forbidden_found = [p for p in (tc.forbidden_patterns or []) if p in final_response]
    intent_ok = (final_intent == tc.expected_intent) if tc.expected_intent else True
    
    score = 100.0
    if missing: score -= len(missing) * 10
    if missing_nested: score -= len(missing_nested) * 10
    if forbidden_found: score -= len(forbidden_found) * 20
    if not intent_ok: score -= 20
    score = max(0, score)
    passed = score >= 80
    
    if not passed:
        print(f"\n{'='*70}")
        print(f"❌ {tc.id}: {tc.name}  [得分:{score:.0f}] 严重程度:{tc.severity.name}")
        print(f"   标签: {tc.tags}")
        print(f"   期望意图: {tc.expected_intent} | 实际意图: {final_intent} | {'✅' if intent_ok else '❌意图不匹配'}")
        if missing:
            print(f"   缺少关键词: {missing}")
        if missing_nested:
            print(f"   缺少嵌套关键词(任一): {missing_nested}")
        if forbidden_found:
            print(f"   包含禁用词: {forbidden_found}")
        print(f"   对话流程:")
        for line in all_responses[-6:]:  # 最后3轮
            print(f"   {line}")
        print(f"   最终回复前150字: {final_response[:150]}")
