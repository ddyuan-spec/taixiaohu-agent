"""
改进建议生成器
根据评测结果生成针对性的改进建议
"""

from typing import List, Dict
from collections import Counter


class ImprovementAdvisor:
    """
    改进建议顾问
    
    分析评测报告，生成可执行的改进建议
    """
    
    def __init__(self, report: Dict):
        self.report = report
        
    def generate_suggestions(self) -> List[Dict]:
        """生成改进建议列表"""
        suggestions = []
        
        # 1. 分析失败测试
        failed_tests = self.report.get("failed_tests", [])
        
        # 按问题类型分组
        issue_patterns = self._analyze_issue_patterns(failed_tests)
        
        # 2. 针对每种问题类型生成建议
        for issue_type, count in issue_patterns.items():
            suggestion = self._create_suggestion(issue_type, count, failed_tests)
            if suggestion:
                suggestions.append(suggestion)
        
        # 3. 按优先级排序
        suggestions.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
        
        return suggestions
    
    def _analyze_issue_patterns(self, failed_tests: List[Dict]) -> Dict[str, int]:
        """分析问题模式"""
        patterns = Counter()
        
        for test in failed_tests:
            for issue in test.get("issues", []):
                issue_type = issue.get("type", "unknown")
                patterns[issue_type] += 1
        
        return dict(patterns)
    
    def _create_suggestion(self, issue_type: str, count: int, 
                          failed_tests: List[Dict]) -> Dict:
        """针对问题类型创建建议"""
        
        suggestion_templates = {
            "missing_pattern": {
                "title": "补充缺失的回复内容",
                "problem": f"有{count}个测试用例缺少期望的回复内容",
                "solution": "检查Prompt是否包含足够的知识，或产品库是否缺少相关信息",
                "action_items": [
                    "检查知识库覆盖度",
                    "补充缺失的产品信息",
                    "优化检索算法"
                ],
                "priority": "高" if count > 5 else "中",
                "priority_score": count * 2
            },
            
            "forbidden_pattern": {
                "title": "修复安全违规问题",
                "problem": f"发现{count}个安全违规（如给出诊断、推荐处方药）",
                "solution": "加强安全过滤，完善System Prompt中的安全约束",
                "action_items": [
                    "在System Prompt中强化安全红线",
                    "添加安全关键词过滤",
                    "增加输出审核机制"
                ],
                "priority": "紧急",
                "priority_score": count * 10  # 安全问题是最高优先级
            },
            
            "intent_mismatch": {
                "title": "优化意图识别",
                "problem": f"有{count}个测试用例意图识别错误",
                "solution": "扩展意图关键词库，优化意图匹配逻辑",
                "action_items": [
                    "收集更多意图样本",
                    "扩展关键词库",
                    "考虑使用语义相似度匹配"
                ],
                "priority": "高" if count > 3 else "中",
                "priority_score": count * 3
            },
            
            "state_mismatch": {
                "title": "修复状态管理问题",
                "problem": f"有{count}个测试用例状态管理错误",
                "solution": "检查状态机逻辑，确保状态转换正确",
                "action_items": [
                    "审查状态机代码",
                    "添加状态转换日志",
                    "增加状态校验"
                ],
                "priority": "中",
                "priority_score": count * 2
            },
            
            "repetition": {
                "title": "解决回复重复问题",
                "problem": f"有{count}个测试用例出现重复回复",
                "solution": "增加回复多样性，避免循环回复",
                "action_items": [
                    "记录最近回复，检测重复",
                    "增加回复模板多样性",
                    "优化追问处理逻辑"
                ],
                "priority": "中",
                "priority_score": count * 2
            },
            
            "too_short": {
                "title": "增加回复信息量",
                "problem": f"有{count}个测试用例回复过短",
                "solution": "优化Prompt要求，确保回复完整",
                "action_items": [
                    "在Prompt中要求详细回答",
                    "检查是否过早结束对话",
                    "增加信息覆盖度检查"
                ],
                "priority": "低",
                "priority_score": count
            },
            
            "too_long": {
                "title": "优化回复长度",
                "problem": f"有{count}个测试用例回复过长",
                "solution": "精简回复内容，突出重点",
                "action_items": [
                    "设置回复长度限制",
                    "优化信息组织方式",
                    "使用要点式回复"
                ],
                "priority": "低",
                "priority_score": count
            },
            
            "format_error": {
                "title": "修复格式问题",
                "problem": f"有{count}个测试用例格式不规范",
                "solution": "统一回复格式，检查特殊符号",
                "action_items": [
                    "检查【】等符号配对",
                    "统一换行和分段",
                    "规范数字和单位格式"
                ],
                "priority": "低",
                "priority_score": count
            },
            
            "safety_violation": {
                "title": "严重：安全违规",
                "problem": f"发现{count}个严重安全违规",
                "solution": "立即修复安全问题，加强安全策略",
                "action_items": [
                    "审查所有安全相关回复",
                    "添加安全关键词黑名单",
                    "实施输出内容审核",
                    "进行安全培训"
                ],
                "priority": "紧急",
                "priority_score": count * 20
            },
            
            "exception": {
                "title": "修复系统异常",
                "problem": f"有{count}个测试用例发生异常",
                "solution": "检查代码异常处理，增加容错机制",
                "action_items": [
                    "添加异常捕获",
                    "增加输入校验",
                    "完善错误日志"
                ],
                "priority": "高",
                "priority_score": count * 5
            }
        }
        
        template = suggestion_templates.get(issue_type)
        if template:
            # 添加相关测试用例
            related_tests = [
                t for t in failed_tests
                if any(i.get("type") == issue_type for i in t.get("issues", []))
            ]
            template["related_tests"] = [t["id"] for t in related_tests[:5]]
            return template
        
        return None
    
    def generate_action_plan(self) -> Dict:
        """生成行动计划"""
        suggestions = self.generate_suggestions()
        
        # 按优先级分组
        urgent = [s for s in suggestions if s["priority"] == "紧急"]
        high = [s for s in suggestions if s["priority"] == "高"]
        medium = [s for s in suggestions if s["priority"] == "中"]
        low = [s for s in suggestions if s["priority"] == "低"]
        
        return {
            "summary": {
                "total_suggestions": len(suggestions),
                "urgent": len(urgent),
                "high": len(high),
                "medium": len(medium),
                "low": len(low)
            },
            "phases": [
                {
                    "phase": 1,
                    "name": "紧急修复",
                    "duration": "1-2天",
                    "tasks": urgent
                },
                {
                    "phase": 2,
                    "name": "高优先级优化",
                    "duration": "3-5天",
                    "tasks": high
                },
                {
                    "phase": 3,
                    "name": "中优先级改进",
                    "duration": "1-2周",
                    "tasks": medium
                },
                {
                    "phase": 4,
                    "name": "低优先级优化",
                    "duration": "2-4周",
                    "tasks": low
                }
            ]
        }
    
    def export_to_markdown(self, filepath: str):
        """导出改进建议为Markdown文档"""
        suggestions = self.generate_suggestions()
        plan = self.generate_action_plan()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# 泰小虎智能体改进建议\n\n")
            f.write(f"生成时间: {self.report.get('summary', {}).get('timestamp', 'N/A')}\n\n")
            
            # 摘要
            f.write("## 评测摘要\n\n")
            summary = self.report.get("summary", {})
            f.write(f"- 总测试数: {summary.get('total_tests', 0)}\n")
            f.write(f"- 通过: {summary.get('passed', 0)}\n")
            f.write(f"- 失败: {summary.get('failed', 0)}\n")
            f.write(f"- 通过率: {summary.get('pass_rate', 0)*100:.1f}%\n")
            f.write(f"- 平均得分: {summary.get('avg_score', 0):.1f}\n\n")
            
            # 行动计划
            f.write("## 行动计划\n\n")
            for phase in plan["phases"]:
                if phase["tasks"]:
                    f.write(f"### 阶段{phase['phase']}: {phase['name']} ({phase['duration']})\n\n")
                    for task in phase["tasks"]:
                        f.write(f"#### {task['title']}\n\n")
                        f.write(f"**问题**: {task['problem']}\n\n")
                        f.write(f"**解决方案**: {task['solution']}\n\n")
                        f.write("**具体行动**:\n")
                        for action in task.get("action_items", []):
                            f.write(f"- [ ] {action}\n")
                        f.write(f"\n**优先级**: {task['priority']}\n\n")
                        if task.get("related_tests"):
                            f.write(f"**相关测试**: {', '.join(task['related_tests'])}\n\n")
                        f.write("---\n\n")
            
            # 详细建议
            f.write("## 详细改进建议\n\n")
            for i, suggestion in enumerate(suggestions, 1):
                f.write(f"{i}. **{suggestion['title']}** ({suggestion['priority']})\n")
                f.write(f"   - 问题: {suggestion['problem']}\n")
                f.write(f"   - 建议: {suggestion['solution']}\n\n")
        
        print(f"\n📄 改进建议已导出: {filepath}")
