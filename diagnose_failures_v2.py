#!/usr/bin/env python3
"""诊断所有失败用例的实际回复"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evaluation.evaluator import AgentEvaluator
from evaluation.multi_turn_test_suite_full import MULTI_TURN_TESTS_FULL
from agent import TaiXiaoHuAgent

evaluator = AgentEvaluator(TaiXiaoHuAgent)

passed_count = 0
failed_count = 0
results = []

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
    
    if passed:
        passed_count += 1
    else:
        failed_count += 1
        results.append({
            'id': tc.id, 'name': tc.name, 'score': score,
            'severity': tc.severity.name, 'tags': tc.tags,
            'missing': missing, 'missing_nested': missing_nested,
            'intent_ok': intent_ok, 'final_intent': final_intent,
            'last_response': final_response[:200]
        })

# 按严重程度分组输出
print(f"\n通过: {passed_count}  失败: {failed_count}  通过率: {passed_count/50*100:.0f}%")
print("="*70)

# Critical + HIGH
critical = [r for r in results if r['severity'] in ['CRITICAL', 'HIGH']]
medium = [r for r in results if r['severity'] == 'MEDIUM']
low = [r for r in results if r['severity'] == 'LOW']

if critical:
    print(f"\n🔴 严重/高优先级 ({len(critical)}个):")
    for r in critical:
        print(f"  {r['id']}: {r['name']} [{r['score']:.0f}分]")
        print(f"    缺少: {r['missing'] or r['missing_nested']}")
        print(f"    意图: {r['final_intent']} | {'✅' if r['intent_ok'] else '❌不匹配'}")

if medium:
    print(f"\n🟡 中优先级 ({len(medium)}个):")
    for r in medium:
        print(f"  {r['id']}: {r['name']} [{r['score']:.0f}分]")
        print(f"    缺少: {r['missing'] or r['missing_nested']}")

if low:
    print(f"\n🟢 低优先级 ({len(low)}个):")
    for r in low:
        print(f"  {r['id']}: {r['name']} [{r['score']:.0f}分]")
