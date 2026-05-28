#!/usr/bin/env python3
"""
泰小虎多轮对话评测运行脚本 - 修复版
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evaluation.evaluator import AgentEvaluator
from evaluation.multi_turn_test_suite_full import MULTI_TURN_TESTS_FULL, CORE_MULTI_TURN_TESTS
from agent import TaiXiaoHuAgent

def main():
    print("=" * 70)
    print("🐯 泰小虎多轮对话评测系统")
    print("=" * 70)
    
    # 使用完整测试套件
    test_suite = MULTI_TURN_TESTS_FULL
    print(f"\n📋 测试套件: 完整版 {len(test_suite)} 条测试用例")
    
    # 创建评测器
    print("\n🚀 启动评测...")
    evaluator = AgentEvaluator(TaiXiaoHuAgent)
    
    # 运行评测
    report = evaluator.run_suite(test_suite, verbose=False)
    
    # 打印摘要
    print("\n" + "=" * 70)
    print("📊 评测结果摘要")
    print("=" * 70)
    print(f"总测试数: {report['summary']['total_tests']}")
    print(f"通过: {report['summary']['passed']} ({report['summary']['pass_rate']:.1f}%)")
    print(f"失败: {report['summary']['failed']}")
    print(f"平均得分: {report['summary']['avg_score']:.2f}/5.0")
    
    # 显示失败的用例（按严重程度排序）
    failed = [r for r in report['results'] if not r['passed']]
    if failed:
        print("\n" + "=" * 70)
        print("❌ 失败的测试用例")
        print("=" * 70)
        
        # 按严重程度分组
        critical_failed = [r for r in failed if r.get('severity') == 'CRITICAL']
        high_failed = [r for r in failed if r.get('severity') == 'HIGH']
        medium_failed = [r for r in failed if r.get('severity') == 'MEDIUM']
        low_failed = [r for r in failed if r.get('severity') == 'LOW']
        
        if critical_failed:
            print(f"\n🔴 严重 (CRITICAL): {len(critical_failed)}个")
            for r in critical_failed:
                print(f"  - {r['test_id']}: {r['test_name']} (得分: {r['score']:.1f})")
        
        if high_failed:
            print(f"\n🟠 高优先级 (HIGH): {len(high_failed)}个")
            for r in high_failed[:10]:
                print(f"  - {r['test_id']}: {r['test_name']} (得分: {r['score']:.1f})")
            if len(high_failed) > 10:
                print(f"    ... 还有 {len(high_failed) - 10} 个")
        
        if medium_failed:
            print(f"\n🟡 中优先级 (MEDIUM): {len(medium_failed)}个")
        
        if low_failed:
            print(f"\n🟢 低优先级 (LOW): {len(low_failed)}个")
    
    # 显示通过的用例
    passed = [r for r in report['results'] if r['passed']]
    if passed:
        print("\n" + "=" * 70)
        print(f"✅ 通过的测试用例 ({len(passed)}个)")
        print("=" * 70)
        for r in passed:
            print(f"  - {r['test_id']}: {r['test_name']} (得分: {r['score']:.1f})")
    
    # 生成改进建议
    print("\n" + "=" * 70)
    print("💡 改进建议")
    print("=" * 70)
    
    # 分析失败原因
    intent_failures = len([r for r in failed if '意图' in r['test_name'] or '意图' in str(r.get('tags', []))])
    context_failures = len([r for r in failed if '上下文' in r['test_name'] or '上下文' in str(r.get('tags', []))])
    profile_failures = len([r for r in failed if '画像' in r['test_name'] or '画像' in str(r.get('tags', []))])
    safety_failures = len([r for r in failed if r.get('severity') == 'CRITICAL'])
    deny_failures = len([r for r in failed if '否认' in r['test_name'] or '拒绝' in r['test_name']])
    
    print(f"1. 意图识别问题: {intent_failures} 个失败用例")
    print("   建议: 进一步优化意图切换检测逻辑")
    
    print(f"2. 上下文理解: {context_failures} 个失败用例")
    print("   建议: 增强多轮对话上下文保持能力")
    
    print(f"3. 画像管理: {profile_failures} 个失败用例")
    print("   建议: 完善画像提取和更新机制")
    
    print(f"4. 拒绝/否认处理: {deny_failures} 个失败用例")
    print("   建议: 优化边界处理和用户拒绝响应")
    
    if safety_failures > 0:
        print(f"5. 安全合规: {safety_failures} 个严重失败")
        print("   建议: 优先修复安全问题")
    
    print("\n" + "=" * 70)
    print("✅ 评测完成!")
    print("=" * 70)

if __name__ == "__main__":
    main()
