#!/usr/bin/env python3
"""
泰小虎多轮对话评测运行脚本 - 自动版
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
    
    # 按类别统计
    print("\n📈 按类别统计:")
    for category, stats in report['by_category'].items():
        rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"  {category}: {stats['passed']}/{stats['total']} 通过 ({rate:.1f}%)")
    
    # 按严重程度统计
    print("\n🎯 按严重程度统计:")
    by_severity = {}
    for r in report['results']:
        sev = r.get('severity', 'UNKNOWN')
        if sev not in by_severity:
            by_severity[sev] = {'total': 0, 'passed': 0}
        by_severity[sev]['total'] += 1
        if r['passed']:
            by_severity[sev]['passed'] += 1
    
    for sev, stats in sorted(by_severity.items(), 
                              key=lambda x: {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}.get(x[0], 4)):
        rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"  {sev}: {stats['passed']}/{stats['total']} 通过 ({rate:.1f}%)")
    
    # 保存报告
    report_path = "multi_turn_evaluation_report.json"
    evaluator.save_report(report_path)
    print(f"\n💾 详细报告已保存: {report_path}")
    
    # 显示失败的用例（按严重程度排序）
    failed = [r for r in report['results'] if not r['passed']]
    if failed:
        print("\n" + "=" * 70)
        print("❌ 失败的测试用例")
        print("=" * 70)
        
        # 按严重程度分组
        critical_failed = [r for r in failed if r.get('severity') == 'CRITICAL']
        high_failed = [r for r in failed if r.get('severity') == 'HIGH']
        other_failed = [r for r in failed if r.get('severity') not in ['CRITICAL', 'HIGH']]
        
        if critical_failed:
            print("\n🔴 严重 (CRITICAL):")
            for r in critical_failed:
                print(f"  - {r['test_id']}: {r['test_name']} (得分: {r['score']:.1f})")
        
        if high_failed:
            print("\n🟠 高优先级 (HIGH):")
            for r in high_failed[:10]:
                print(f"  - {r['test_id']}: {r['test_name']} (得分: {r['score']:.1f})")
            if len(high_failed) > 10:
                print(f"    ... 还有 {len(high_failed) - 10} 个")
        
        if other_failed:
            print(f"\n🟡 其他: {len(other_failed)} 个")
    
    # 生成改进建议
    print("\n" + "=" * 70)
    print("💡 改进建议")
    print("=" * 70)
    
    # 分析失败原因
    intent_failures = len([r for r in failed if '意图' in r['test_name'] or '意图' in str(r.get('tags', []))])
    context_failures = len([r for r in failed if '上下文' in r['test_name'] or '上下文' in str(r.get('tags', []))])
    profile_failures = len([r for r in failed if '画像' in r['test_name'] or '画像' in str(r.get('tags', []))])
    safety_failures = len([r for r in failed if r.get('severity') == 'CRITICAL'])
    
    if intent_failures > 0:
        print(f"1. 意图识别: {intent_failures} 个失败用例")
        print("   建议: 扩展意图识别关键词，优化意图切换逻辑")
    
    if context_failures > 0:
        print(f"2. 上下文理解: {context_failures} 个失败用例")
        print("   建议: 增强对话历史管理，优化上下文关联")
    
    if profile_failures > 0:
        print(f"3. 画像管理: {profile_failures} 个失败用例")
        print("   建议: 完善画像收集和更新机制")
    
    if safety_failures > 0:
        print(f"4. 安全合规: {safety_failures} 个严重失败")
        print("   建议: 优先修复安全问题，加强安全检测")
    
    print("\n" + "=" * 70)
    print("✅ 评测完成!")
    print("=" * 70)

if __name__ == "__main__":
    main()
