#!/usr/bin/env python3
"""
泰小虎智能体评测执行脚本
使用评测集 V1 进行自动化评测
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import TaiXiaoHuAgent
from evaluation import AgentEvaluator, DEFAULT_TEST_SUITE, ImprovementAdvisor


def main():
    print("=" * 70)
    print("🐯 泰小虎智能健康导购助手 - 自动化评测系统")
    print("=" * 70)
    print(f"评测集版本: V1.2")
    print(f"测试用例数: {len(DEFAULT_TEST_SUITE)}")
    print(f"评测维度: 意图识别、上下文理解、知识准确性、安全合规、回复质量、用户体验")
    print("=" * 70)
    
    # 创建评测器
    evaluator = AgentEvaluator(TaiXiaoHuAgent)
    
    # 执行评测
    report = evaluator.run_suite(DEFAULT_TEST_SUITE, verbose=True)
    
    # 打印摘要
    evaluator.print_summary()
    
    # 保存报告
    evaluator.save_report("evaluation_report.json")
    
    # 生成改进建议
    print("\n" + "=" * 70)
    print("💡 改进建议")
    print("=" * 70)
    
    advisor = ImprovementAdvisor(report)
    suggestions = advisor.generate_suggestions()
    
    for i, suggestion in enumerate(suggestions[:10], 1):
        print(f"\n{i}. {suggestion['title']}")
        print(f"   问题: {suggestion['problem']}")
        print(f"   建议: {suggestion['solution']}")
        print(f"   优先级: {suggestion['priority']}")
    
    # 返回码
    pass_rate = report["summary"]["pass_rate"]
    if pass_rate >= 0.9:
        print("\n✅ 评测通过（通过率 >= 90%）")
        return 0
    elif pass_rate >= 0.7:
        print("\n⚠️  评测警告（通过率 70%-90%）")
        return 1
    else:
        print("\n❌ 评测未通过（通过率 < 70%）")
        return 2


if __name__ == "__main__":
    sys.exit(main())
