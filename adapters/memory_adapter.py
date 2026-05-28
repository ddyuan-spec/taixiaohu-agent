"""
记忆库适配器
支持：短期记忆（对话历史）、长期记忆（重要事实）、工作记忆（当前上下文）
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class MemoryType(Enum):
    """记忆类型"""
    DIALOGUE = "dialogue"       # 对话历史
    FACT = "fact"               # 重要事实（用户偏好、关键信息）
    CONTEXT = "context"         # 工作上下文（当前意图、追问状态）
    SUMMARY = "summary"         # 对话摘要


@dataclass
class MemoryItem:
    """记忆条目"""
    id: str
    user_id: str
    session_id: str
    memory_type: MemoryType
    content: str
    importance: float = 1.0       # 重要程度 0-1
    create_time: datetime = field(default_factory=datetime.now)
    expire_time: Optional[datetime] = None  # 过期时间（None表示永不过期）
    metadata: Dict[str, Any] = field(default_factory=dict)
    access_count: int = 0         # 访问次数（用于淘汰）
    last_access_time: datetime = field(default_factory=datetime.now)

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expire_time is None:
            return False
        return datetime.now() > self.expire_time

    def touch(self):
        """更新访问时间"""
        self.access_count += 1
        self.last_access_time = datetime.now()


class MemoryAdapter(ABC):
    """
    记忆库适配器抽象基类

    记忆层级：
    1. 工作记忆（Working Memory）：当前对话上下文，TTL=会话期间
    2. 短期记忆（Short-term）：最近N轮对话，TTL=24小时
    3. 长期记忆（Long-term）：重要事实，TTL=永久

    注入时机：
    1. 每次对话前：注入工作记忆（当前意图、追问状态）
    2. 会话开始时：注入短期记忆（最近对话摘要）
    3. 特定场景：注入长期记忆（用户偏好、历史症状）
    """

    # ---------------- 基础CRUD ----------------

    @abstractmethod
    def add(self, item: MemoryItem) -> bool:
        """添加记忆"""
        pass

    @abstractmethod
    def get(self, memory_id: str) -> Optional[MemoryItem]:
        """获取单条记忆"""
        pass

    @abstractmethod
    def query(self, user_id: str, memory_type: Optional[MemoryType] = None,
              limit: int = 10) -> List[MemoryItem]:
        """查询记忆"""
        pass

    @abstractmethod
    def update(self, memory_id: str, updates: Dict) -> bool:
        """更新记忆"""
        pass

    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        pass

    @abstractmethod
    def cleanup_expired(self) -> int:
        """清理过期记忆，返回清理数量"""
        pass

    # ---------------- 记忆管理 ----------------

    @abstractmethod
    def summarize_session(self, user_id: str, session_id: str) -> str:
        """
        生成会话摘要

        将多轮对话压缩为关键信息，用于长期存储
        """
        pass

    @abstractmethod
    def consolidate(self, user_id: str):
        """
        记忆整合

        将短期记忆整合为长期记忆，去重、提炼关键信息
        """
        pass

    # ---------------- 注入相关方法 ----------------

    def inject_for_turn(self, user_id: str, session_id: str) -> str:
        """
        单轮对话前注入

        注入工作记忆：当前意图、追问状态、最近对话
        """
        # 获取工作记忆
        context_memories = self.query(
            user_id=user_id,
            memory_type=MemoryType.CONTEXT,
            limit=5
        )

        # 获取最近对话
        recent_dialogues = self.query(
            user_id=user_id,
            memory_type=MemoryType.DIALOGUE,
            limit=3
        )

        parts = []

        # 添加上下文
        if context_memories:
            parts.append("# 当前上下文")
            for mem in context_memories:
                parts.append(f"- {mem.content}")
                mem.touch()

        # 添加最近对话
        if recent_dialogues:
            parts.append("\n# 最近对话")
            for mem in reversed(recent_dialogues):  # 按时间顺序
                parts.append(f"{mem.metadata.get('role', '用户')}: {mem.content}")
                mem.touch()

        return "\n".join(parts)

    def inject_for_session(self, user_id: str) -> str:
        """
        会话开始时注入

        注入长期记忆：用户偏好、历史重要信息
        """
        # 获取重要事实
        facts = self.query(
            user_id=user_id,
            memory_type=MemoryType.FACT,
            limit=10
        )

        # 获取历史摘要
        summaries = self.query(
            user_id=user_id,
            memory_type=MemoryType.SUMMARY,
            limit=3
        )

        parts = []

        if facts:
            parts.append("# 用户偏好与历史")
            for fact in facts:
                parts.append(f"- {fact.content}")
                fact.touch()

        if summaries:
            parts.append("\n# 历史会话摘要")
            for i, summary in enumerate(summaries, 1):
                parts.append(f"[{i}] {summary.content[:100]}...")
                summary.touch()

        return "\n".join(parts)

    def save_dialogue_turn(self, user_id: str, session_id: str,
                           role: str, content: str):
        """
        保存单轮对话

        Args:
            user_id: 用户ID
            session_id: 会话ID
            role: user/assistant
            content: 内容
        """
        item = MemoryItem(
            id=f"{session_id}_{datetime.now().timestamp()}",
            user_id=user_id,
            session_id=session_id,
            memory_type=MemoryType.DIALOGUE,
            content=content[:500],  # 限制长度
            importance=0.5,
            expire_time=datetime.now() + timedelta(hours=24),  # 24小时过期
            metadata={"role": role}
        )
        self.add(item)

    def save_fact(self, user_id: str, content: str,
                  importance: float = 0.8) -> str:
        """
        保存重要事实（长期记忆）

        Returns:
            记忆ID
        """
        import uuid
        memory_id = str(uuid.uuid4())

        item = MemoryItem(
            id=memory_id,
            user_id=user_id,
            session_id="long_term",
            memory_type=MemoryType.FACT,
            content=content,
            importance=importance,
            expire_time=None,  # 永不过期
        )
        self.add(item)
        return memory_id

    def update_context(self, user_id: str, session_id: str,
                       context_type: str, content: str):
        """
        更新工作上下文

        如：当前意图、追问轮次、临时状态
        """
        # 先删除旧的同类上下文
        old_contexts = self.query(
            user_id=user_id,
            memory_type=MemoryType.CONTEXT,
            limit=100
        )
        for old in old_contexts:
            if old.metadata.get("context_type") == context_type:
                self.delete(old.id)

        # 添加新的
        item = MemoryItem(
            id=f"{session_id}_ctx_{context_type}",
            user_id=user_id,
            session_id=session_id,
            memory_type=MemoryType.CONTEXT,
            content=content,
            importance=0.9,
            expire_time=datetime.now() + timedelta(hours=2),  # 2小时过期
            metadata={"context_type": context_type}
        )
        self.add(item)


# ---------------- 实现示例 ----------------

class MockMemoryAdapter(MemoryAdapter):
    """模拟实现（内存存储）"""

    def __init__(self):
        self._memories: Dict[str, MemoryItem] = {}
        self._cleanup_interval = 3600  # 清理间隔（秒）
        self._last_cleanup = datetime.now()

    def _check_cleanup(self):
        """检查是否需要清理"""
        if (datetime.now() - self._last_cleanup).seconds > self._cleanup_interval:
            self.cleanup_expired()

    def add(self, item: MemoryItem) -> bool:
        self._check_cleanup()
        self._memories[item.id] = item
        return True

    def get(self, memory_id: str) -> Optional[MemoryItem]:
        item = self._memories.get(memory_id)
        if item and not item.is_expired():
            item.touch()
            return item
        return None

    def query(self, user_id: str, memory_type: Optional[MemoryType] = None,
              limit: int = 10) -> List[MemoryItem]:
        self._check_cleanup()

        results = []
        for item in self._memories.values():
            # 过滤用户
            if item.user_id != user_id:
                continue
            # 过滤类型
            if memory_type and item.memory_type != memory_type:
                continue
            # 过滤过期
            if item.is_expired():
                continue

            results.append(item)

        # 按重要性和时间排序
        results.sort(key=lambda x: (x.importance, x.create_time), reverse=True)
        return results[:limit]

    def update(self, memory_id: str, updates: Dict) -> bool:
        if memory_id not in self._memories:
            return False

        item = self._memories[memory_id]
        for key, value in updates.items():
            if hasattr(item, key):
                setattr(item, key, value)

        return True

    def delete(self, memory_id: str) -> bool:
        if memory_id in self._memories:
            del self._memories[memory_id]
            return True
        return False

    def cleanup_expired(self) -> int:
        """清理过期记忆"""
        expired_ids = [
            mid for mid, item in self._memories.items()
            if item.is_expired()
        ]
        for mid in expired_ids:
            del self._memories[mid]

        self._last_cleanup = datetime.now()
        return len(expired_ids)

    def summarize_session(self, user_id: str, session_id: str) -> str:
        """生成会话摘要（简单实现）"""
        dialogues = self.query(
            user_id=user_id,
            memory_type=MemoryType.DIALOGUE,
            limit=100
        )

        # 提取关键信息（实际应使用LLM生成摘要）
        user_msgs = [d for d in dialogues if d.metadata.get("role") == "user"]

        if not user_msgs:
            return ""

        # 简单拼接前3条用户消息作为摘要
        summary = "；".join([m.content[:50] for m in user_msgs[:3]])
        return f"用户咨询了：{summary}"

    def consolidate(self, user_id: str):
        """记忆整合（简单实现）"""
        # 获取24小时前的对话
        cutoff = datetime.now() - timedelta(hours=24)

        old_dialogues = [
            item for item in self._memories.values()
            if item.user_id == user_id
            and item.memory_type == MemoryType.DIALOGUE
            and item.create_time < cutoff
        ]

        if len(old_dialogues) < 5:
            return

        # 生成摘要
        summary = self.summarize_session(user_id, "")

        # 保存为长期记忆
        self.save_fact(user_id, summary, importance=0.7)

        # 删除旧对话
        for item in old_dialogues:
            self.delete(item.id)


# ---------------- 真实实现示例（使用Redis）----------------

class RedisMemoryAdapter(MemoryAdapter):
    """
    基于Redis的实现

    需要安装: pip install redis
    """

    def __init__(self, host: str = "localhost", port: int = 6379,
                 db: int = 0, password: Optional[str] = None):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self._client = None

    def _get_client(self):
        """获取Redis客户端"""
        if self._client is None:
            import redis
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True
            )
        return self._client

    def _make_key(self, item: MemoryItem) -> str:
        """生成Redis键"""
        return f"memory:{item.user_id}:{item.memory_type.value}:{item.id}"

    def add(self, item: MemoryItem) -> bool:
        """添加记忆到Redis"""
        import json
        client = self._get_client()
        key = self._make_key(item)

        # 序列化
        data = {
            "id": item.id,
            "user_id": item.user_id,
            "session_id": item.session_id,
            "memory_type": item.memory_type.value,
            "content": item.content,
            "importance": item.importance,
            "create_time": item.create_time.isoformat(),
            "metadata": json.dumps(item.metadata),
            "access_count": item.access_count,
            "last_access_time": item.last_access_time.isoformat()
        }

        # 设置过期时间
        if item.expire_time:
            ttl = int((item.expire_time - datetime.now()).total_seconds())
            if ttl > 0:
                client.hset(key, mapping=data)
                client.expire(key, ttl)
        else:
            # 永不过期
            client.hset(key, mapping=data)

        # 添加到用户索引
        client.sadd(f"memory:index:{item.user_id}", key)

        return True

    def get(self, memory_id: str) -> Optional[MemoryItem]:
        """获取单条记忆"""
        # 需要从索引中查找（简化实现）
        pass

    def query(self, user_id: str, memory_type: Optional[MemoryType] = None,
              limit: int = 10) -> List[MemoryItem]:
        """查询记忆"""
        import json
        client = self._get_client()

        # 获取用户所有记忆键
        keys = client.smembers(f"memory:index:{user_id}")

        items = []
        for key in keys:
            data = client.hgetall(key)
            if not data:
                continue

            # 过滤类型
            if memory_type and data.get("memory_type") != memory_type.value:
                continue

            item = MemoryItem(
                id=data["id"],
                user_id=data["user_id"],
                session_id=data["session_id"],
                memory_type=MemoryType(data["memory_type"]),
                content=data["content"],
                importance=float(data["importance"]),
                create_time=datetime.fromisoformat(data["create_time"]),
                metadata=json.loads(data.get("metadata", "{}")),
                access_count=int(data.get("access_count", 0)),
                last_access_time=datetime.fromisoformat(data["last_access_time"])
            )
            items.append(item)

        # 排序
        items.sort(key=lambda x: (x.importance, x.create_time), reverse=True)
        return items[:limit]

    def update(self, memory_id: str, updates: Dict) -> bool:
        """更新记忆"""
        pass

    def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        pass

    def cleanup_expired(self) -> int:
        """Redis自动过期，无需手动清理"""
        return 0

    def summarize_session(self, user_id: str, session_id: str) -> str:
        """生成摘要"""
        return MockMemoryAdapter().summarize_session(user_id, session_id)

    def consolidate(self, user_id: str):
        """记忆整合"""
        pass
