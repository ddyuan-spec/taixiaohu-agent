"""
Badcase库适配器
支持：问题记录、根因分析、自动修复建议、闭环追踪
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class BadcaseType(Enum):
    """Badcase类型"""
    INTENT_ERROR = "intent_error"           # 意图识别错误
    RESPONSE_ERROR = "response_error"       # 回复内容错误
    SAFETY_ISSUE = "safety_issue"           # 安全问题
    EXPERIENCE_ISSUE = "experience_issue"   # 体验问题（回复慢、重复等）
    HALLUCINATION = "hallucination"         # 幻觉/编造信息
    CONTEXT_LOSS = "context_loss"           # 上下文丢失


class BadcaseStatus(Enum):
    """处理状态"""
    NEW = "new"                             # 新发现
    CONFIRMED = "confirmed"                 # 已确认
    FIXING = "fixing"                       # 修复中
    FIXED = "fixed"                         # 已修复
    CLOSED = "closed"                       # 已关闭
    IGNORED = "ignored"                     # 忽略


@dataclass
class BadcaseItem:
    """Badcase条目"""
    id: str
    user_id: str
    session_id: str
    badcase_type: BadcaseType
    title: str                              # 问题标题
    description: str                        # 问题描述
    user_input: str                         # 用户输入
    agent_response: str                     # 智能体回复
    expected_response: Optional[str] = None # 期望回复
    context: Dict[str, Any] = field(default_factory=dict)  # 上下文信息
    status: BadcaseStatus = BadcaseStatus.NEW
    severity: int = 3                       # 严重程度 1-5
    root_cause: Optional[str] = None        # 根因分析
    fix_suggestion: Optional[str] = None    # 修复建议
    fix_commit: Optional[str] = None        # 修复提交
    create_time: datetime = field(default_factory=datetime.now)
    update_time: datetime = field(default_factory=datetime.now)
    close_time: Optional[datetime] = None
    reporter: str = "system"                # 报告人
    assignee: Optional[str] = None          # 负责人

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "badcase_type": self.badcase_type.value,
            "title": self.title,
            "description": self.description,
            "user_input": self.user_input,
            "agent_response": self.agent_response,
            "expected_response": self.expected_response,
            "context": self.context,
            "status": self.status.value,
            "severity": self.severity,
            "root_cause": self.root_cause,
            "fix_suggestion": self.fix_suggestion,
            "fix_commit": self.fix_commit,
            "create_time": self.create_time.isoformat(),
            "update_time": self.update_time.isoformat(),
            "close_time": self.close_time.isoformat() if self.close_time else None,
            "reporter": self.reporter,
            "assignee": self.assignee
        }


class BadcaseAdapter(ABC):
    """
    Badcase库适配器抽象基类

    核心功能：
    1. 自动检测：基于规则自动识别潜在问题
    2. 人工标注：运营人员手动标注问题
    3. 根因分析：分析Badcase产生的技术原因
    4. 修复追踪：追踪修复进度，闭环管理
    5. 反馈学习：从Badcase中提取知识，改进模型

    注入时机：
    1. 每次对话后：自动检测潜在问题
    2. 用户反馈时：记录显式反馈的问题
    3. 定期复盘：批量分析Badcase模式
    """

    # ---------------- 基础CRUD ----------------

    @abstractmethod
    def add(self, item: BadcaseItem) -> bool:
        """添加Badcase"""
        pass

    @abstractmethod
    def get(self, badcase_id: str) -> Optional[BadcaseItem]:
        """获取Badcase"""
        pass

    @abstractmethod
    def query(self, status: Optional[BadcaseStatus] = None,
              badcase_type: Optional[BadcaseType] = None,
              limit: int = 50) -> List[BadcaseItem]:
        """查询Badcase"""
        pass

    @abstractmethod
    def update(self, badcase_id: str, updates: Dict) -> bool:
        """更新Badcase"""
        pass

    @abstractmethod
    def delete(self, badcase_id: str) -> bool:
        """删除Badcase"""
        pass

    # ---------------- 自动检测 ----------------

    def auto_detect(self, user_id: str, session_id: str,
                    user_input: str, agent_response: str,
                    context: Dict[str, Any]) -> Optional[BadcaseItem]:
        """
        自动检测潜在问题

        检测规则：
        1. 重复回复：连续3次相同回复
        2. 答非所问：用户追问但回复不相关
        3. 安全违规：包含敏感词
        4. 上下文丢失：用户提及前文但回复未关联
        5. 过度承诺：宣称治疗效果
        """
        import uuid

        # 检测1：重复回复
        if self._check_repetition(session_id, agent_response):
            return BadcaseItem(
                id=str(uuid.uuid4()),
                user_id=user_id,
                session_id=session_id,
                badcase_type=BadcaseType.EXPERIENCE_ISSUE,
                title="重复回复",
                description="智能体连续多次给出相同回复",
                user_input=user_input,
                agent_response=agent_response,
                context=context,
                severity=3
            )

        # 检测2：答非所问（简单关键词匹配）
        if self._check_irrelevant(user_input, agent_response):
            return BadcaseItem(
                id=str(uuid.uuid4()),
                user_id=user_id,
                session_id=session_id,
                badcase_type=BadcaseType.RESPONSE_ERROR,
                title="回复不相关",
                description="用户追问但智能体回复与问题无关",
                user_input=user_input,
                agent_response=agent_response,
                context=context,
                severity=4
            )

        # 检测3：安全违规
        if self._check_safety_violation(agent_response):
            return BadcaseItem(
                id=str(uuid.uuid4()),
                user_id=user_id,
                session_id=session_id,
                badcase_type=BadcaseType.SAFETY_ISSUE,
                title="安全违规",
                description="回复包含违规内容",
                user_input=user_input,
                agent_response=agent_response,
                context=context,
                severity=5
            )

        # 检测4：上下文丢失
        if self._check_context_loss(user_input, agent_response, context):
            return BadcaseItem(
                id=str(uuid.uuid4()),
                user_id=user_id,
                session_id=session_id,
                badcase_type=BadcaseType.CONTEXT_LOSS,
                title="上下文丢失",
                description="用户提及前文信息但智能体未关联",
                user_input=user_input,
                agent_response=agent_response,
                context=context,
                severity=3
            )

        return None

    def _check_repetition(self, session_id: str, response: str) -> bool:
        """检查是否重复回复（简化实现）"""
        # 实际应查询最近N条回复
        return False

    def _check_irrelevant(self, user_input: str, agent_response: str) -> bool:
        """检查是否答非所问"""
        # 用户追问关键词
        follow_up_keywords = ["功效", "效果", "作用", "为什么", "怎么", "多少钱"]
        # 如果用户追问但回复是欢迎语
        if any(kw in user_input for kw in follow_up_keywords):
            welcome_patterns = ["您好", "我是泰小虎", "请问您今天"]
            if any(pat in agent_response for pat in welcome_patterns):
                return True
        return False

    def _check_safety_violation(self, response: str) -> bool:
        """检查安全违规"""
        violation_keywords = [
            "治愈", "根治", "包治", "百分之百有效",
            "代替药物", "不用看医生", "停药"
        ]
        return any(kw in response for kw in violation_keywords)

    def _check_context_loss(self, user_input: str, response: str,
                           context: Dict) -> bool:
        """检查上下文丢失"""
        # 用户提及前文产品
        if any(kw in user_input for kw in ["刚才", "上面", "那个产品"]):
            # 但回复未提及产品
            if "产品" not in response and "推荐" not in response:
                return True
        return False

    # ---------------- 根因分析 ----------------

    def analyze_root_cause(self, badcase: BadcaseItem) -> str:
        """
        分析Badcase根因

        常见根因：
        1. 意图识别错误：关键词匹配不足
        2. 知识缺失：知识库未覆盖
        3. 上下文管理：状态机设计问题
        4. 安全策略：过滤规则不完善
        5. 模型幻觉：生成内容不受控
        """
        if badcase.badcase_type == BadcaseType.INTENT_ERROR:
            return "意图识别模块关键词覆盖不足，或语义理解能力有限"

        elif badcase.badcase_type == BadcaseType.RESPONSE_ERROR:
            if "欢迎" in badcase.agent_response:
                return "状态机设计问题：用户追问时未保持上下文状态"
            return "知识库缺失或检索不准确"

        elif badcase.badcase_type == BadcaseType.CONTEXT_LOSS:
            return "工作记忆管理问题：未正确保存/注入对话上下文"

        elif badcase.badcase_type == BadcaseType.SAFETY_ISSUE:
            return "安全过滤规则不完善，或模型生成不受控"

        elif badcase.badcase_type == BadcaseType.EXPERIENCE_ISSUE:
            return "回复生成逻辑问题：缺乏多样性或陷入循环"

        return "需要进一步分析"

    def suggest_fix(self, badcase: BadcaseItem) -> str:
        """
        生成修复建议
        """
        root_cause = badcase.root_cause or self.analyze_root_cause(badcase)

        suggestions = {
            "意图识别": "1. 扩展意图关键词库\n2. 增加语义相似度匹配\n3. 优化意图确认机制",
            "知识库": "1. 补充缺失知识\n2. 优化检索算法\n3. 增加知识验证机制",
            "上下文": "1. 修复状态机逻辑\n2. 增强工作记忆管理\n3. 优化追问处理",
            "安全": "1. 完善敏感词库\n2. 增加生成内容审核\n3. 强化安全Prompt",
            "体验": "1. 增加回复多样性\n2. 优化重复检测\n3. 改进异常处理"
        }

        for key, suggestion in suggestions.items():
            if key in root_cause:
                return suggestion

        return "1. 复现问题\n2. 定位代码\n3. 编写修复\n4. 测试验证"

    # ---------------- 反馈学习 ----------------

    def extract_training_data(self, badcase: BadcaseItem) -> Optional[Dict]:
        """
        从Badcase中提取训练数据

        用于：
        1. 意图识别模型微调
        2. 知识库补充
        3. 安全策略优化
        """
        if badcase.status != BadcaseStatus.FIXED:
            return None

        if not badcase.expected_response:
            return None

        return {
            "user_input": badcase.user_input,
            "context": badcase.context,
            "bad_response": badcase.agent_response,
            "good_response": badcase.expected_response,
            "type": badcase.badcase_type.value,
            "use_for": "sft"  # supervised fine-tuning
        }

    def generate_report(self, start_time: datetime,
                       end_time: datetime) -> Dict:
        """
        生成Badcase分析报告
        """
        all_cases = self.query()
        period_cases = [
            c for c in all_cases
            if start_time <= c.create_time <= end_time
        ]

        # 按类型统计
        type_count = {}
        for case in period_cases:
            t = case.badcase_type.value
            type_count[t] = type_count.get(t, 0) + 1

        # 按状态统计
        status_count = {}
        for case in period_cases:
            s = case.status.value
            status_count[s] = status_count.get(s, 0) + 1

        # 严重问题
        severe_cases = [c for c in period_cases if c.severity >= 4]

        return {
            "period": f"{start_time} ~ {end_time}",
            "total_cases": len(period_cases),
            "by_type": type_count,
            "by_status": status_count,
            "severe_cases": len(severe_cases),
            "fix_rate": status_count.get("fixed", 0) / len(period_cases)
            if period_cases else 0,
            "top_issues": sorted(type_count.items(),
                                key=lambda x: x[1], reverse=True)[:3]
        }


# ---------------- 实现示例 ----------------

class MockBadcaseAdapter(BadcaseAdapter):
    """模拟实现（内存存储）"""

    def __init__(self):
        self._badcases: Dict[str, BadcaseItem] = {}
        self._session_responses: Dict[str, List[str]] = {}  # 用于检测重复

    def add(self, item: BadcaseItem) -> bool:
        self._badcases[item.id] = item
        return True

    def get(self, badcase_id: str) -> Optional[BadcaseItem]:
        return self._badcases.get(badcase_id)

    def query(self, status: Optional[BadcaseStatus] = None,
              badcase_type: Optional[BadcaseType] = None,
              limit: int = 50) -> List[BadcaseItem]:
        results = []
        for item in self._badcases.values():
            if status and item.status != status:
                continue
            if badcase_type and item.badcase_type != badcase_type:
                continue
            results.append(item)

        # 按严重程度和时间排序
        results.sort(key=lambda x: (x.severity, x.create_time), reverse=True)
        return results[:limit]

    def update(self, badcase_id: str, updates: Dict) -> bool:
        if badcase_id not in self._badcases:
            return False

        item = self._badcases[badcase_id]
        for key, value in updates.items():
            if hasattr(item, key):
                setattr(item, key, value)

        item.update_time = datetime.now()

        # 如果状态变为fixed或closed，记录关闭时间
        if updates.get("status") in [BadcaseStatus.FIXED, BadcaseStatus.CLOSED]:
            item.close_time = datetime.now()

        return True

    def delete(self, badcase_id: str) -> bool:
        if badcase_id in self._badcases:
            del self._badcases[badcase_id]
            return True
        return False

    def _check_repetition(self, session_id: str, response: str) -> bool:
        """检查重复回复"""
        if session_id not in self._session_responses:
            self._session_responses[session_id] = []

        responses = self._session_responses[session_id]
        responses.append(response)

        # 只保留最近5条
        if len(responses) > 5:
            responses = responses[-5:]
        self._session_responses[session_id] = responses

        # 检查最近3条是否相同
        if len(responses) >= 3:
            last_three = responses[-3:]
            if len(set(last_three)) == 1:
                return True

        return False


# ---------------- 真实实现示例（使用Elasticsearch）----------------

class ESBadcaseAdapter(BadcaseAdapter):
    """
    基于Elasticsearch的实现

    需要安装: pip install elasticsearch
    """

    def __init__(self, hosts: List[str], index: str = "badcases"):
        self.hosts = hosts
        self.index = index
        self._client = None

    def _get_client(self):
        """获取ES客户端"""
        if self._client is None:
            from elasticsearch import Elasticsearch
            self._client = Elasticsearch(self.hosts)
        return self._client

    def add(self, item: BadcaseItem) -> bool:
        """添加Badcase到ES"""
        client = self._get_client()
        client.index(index=self.index, id=item.id, document=item.to_dict())
        return True

    def get(self, badcase_id: str) -> Optional[BadcaseItem]:
        """获取Badcase"""
        client = self._get_client()
        try:
            result = client.get(index=self.index, id=badcase_id)
            return self._doc_to_item(result["_source"])
        except:
            return None

    def query(self, status: Optional[BadcaseStatus] = None,
              badcase_type: Optional[BadcaseType] = None,
              limit: int = 50) -> List[BadcaseItem]:
        """查询Badcase"""
        client = self._get_client()

        # 构建查询
        must = []
        if status:
            must.append({"term": {"status": status.value}})
        if badcase_type:
            must.append({"term": {"badcase_type": badcase_type.value}})

        query = {"bool": {"must": must}} if must else {"match_all": {}}

        results = client.search(
            index=self.index,
            query=query,
            sort=[{"severity": "desc"}, {"create_time": "desc"}],
            size=limit
        )

        return [self._doc_to_item(hit["_source"])
                for hit in results["hits"]["hits"]]

    def update(self, badcase_id: str, updates: Dict) -> bool:
        """更新Badcase"""
        client = self._get_client()
        client.update(index=self.index, id=badcase_id, doc=updates)
        return True

    def delete(self, badcase_id: str) -> bool:
        """删除Badcase"""
        client = self._get_client()
        client.delete(index=self.index, id=badcase_id)
        return True

    def _doc_to_item(self, doc: Dict) -> BadcaseItem:
        """ES文档转对象"""
        return BadcaseItem(
            id=doc["id"],
            user_id=doc["user_id"],
            session_id=doc["session_id"],
            badcase_type=BadcaseType(doc["badcase_type"]),
            title=doc["title"],
            description=doc["description"],
            user_input=doc["user_input"],
            agent_response=doc["agent_response"],
            expected_response=doc.get("expected_response"),
            context=doc.get("context", {}),
            status=BadcaseStatus(doc["status"]),
            severity=doc["severity"],
            root_cause=doc.get("root_cause"),
            fix_suggestion=doc.get("fix_suggestion"),
            fix_commit=doc.get("fix_commit"),
            create_time=datetime.fromisoformat(doc["create_time"]),
            update_time=datetime.fromisoformat(doc["update_time"]),
            close_time=datetime.fromisoformat(doc["close_time"]) if doc.get("close_time") else None,
            reporter=doc.get("reporter", "system"),
            assignee=doc.get("assignee")
        )
