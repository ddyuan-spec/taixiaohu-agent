#!/usr/bin/env python3
"""
泰小虎多轮对话评测运行脚本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evaluation.evaluator import AgentEvaluator
from evaluation.multi_turn_test_suite_full import MULTI_TURN_TESTS_FULL, CORE_MULTI_TURN_TESTS
from agent import TaiXiaoHuAgent

def main():
    print("=" * 60)
    print("🐯 泰小虎多轮对话评测系统")
    print("=" * 60)
    
    # 选择测试套件
    print("\n选择测试套件:")
    print("1. 核心测试套件 (20条)")
    print("2. 完整测试套件 (50条)")
    
    choice = input("\n请输入选项 (1/2, 默认2): ").strip() or "2"
    
    if choice == "1":
        test_suite = CORE_MULTI_TURN_TESTS
        print(f"\n📋 已选择核心测试套件: {len(test_suite)} 条测试用例")
    else:
        test_suite = MULTI_TURN_TESTS_FULL
        print(f"\n📋 已选择完整测试套件: {len(test_suite)} 条测试用例")
    
    # 是否显示详细输出
    verbose = input("\n是否显示详细输出? (y/n, 默认n): ").strip().lower() == 'y'
    
    # 创建评测器
    print("\n🚀 启动评测...")
    evaluator = AgentEvaluator(TaiXiaoHuAgent)
    
    # 运行评测
    report = evaluator.run_suite(test_suite, verbose=verbose)
    
    # 打印摘要
    print("\n" + "=" * 60)
    print("📊 评测结果摘要")
    print("=" * 60)
    print(f"总测试数: {report['summary']['total_tests']}")
    print(f"通过: {report['summary']['passed']} ({report['summary']['pass_rate']:.1f}%)")
    print(f"失败: {report['summary']['failed']}")
    print(f"平均得分: {report['summary']['avg_score']:.2f}/5.0")
    
    # 按类别统计
    print("\n📈 按类别统计:")
    for category, stats in report['by_category'].items():
        print(f"  {category}: {stats['passed']}/{stats['total']} 通过")
    
    # 保存报告
    report_path = "multi_turn_evaluation_report.json"
    evaluator.save_report(report_path)
    print(f"\n💾 详细报告已保存: {report_path}")
    
    # 显示失败的用例
    failed = [r for r in report['results'] if not r['passed']]
    if failed:
        print("\n❌ 失败的测试用例:")
        for r in failed[:10]:  # 只显示前10个
            print(f"  - {r['test_id']}: {r['test_name']} (得分: {r['score']:.1f})")
        if len(failed) > 10:
            print(f"  ... 还有 {len(failed) - 10} 个失败用例")
    
    print("\n" + "=" * 60)
    print("✅ 评测完成!")
    print("=" * 60)

if __name__ == "__main__":
    main()
