"""
知识库适配器
支持：向量检索（RAG）、关键词搜索、分类浏览
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class KnowledgeItem:
    """知识条目"""
    id: str
    title: str
    content: str
    category: str
    tags: List[str]
    source: str
    create_time: datetime
    update_time: datetime
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None  # 向量嵌入


class KnowledgeAdapter(ABC):
    """
    知识库适配器抽象基类

    注入时机：
    1. 会话开始时：注入用户可能关心的健康知识
    2. 意图识别后：根据意图注入相关知识（健康咨询→症状知识，产品咨询→产品知识）
    3. 追问时：根据上下文注入深度知识
    """

    @abstractmethod
    def search(self, query: str, top_k: int = 5,
               filters: Optional[Dict] = None) -> List[KnowledgeItem]:
        """
        语义搜索知识库

        Args:
            query: 查询文本
            top_k: 返回数量
            filters: 过滤条件 {"category": "症状", "tags": ["头痛"]}

        Returns:
            知识条目列表
        """
        pass

    @abstractmethod
    def keyword_search(self, keywords: List[str],
                       top_k: int = 5) -> List[KnowledgeItem]:
        """
        关键词搜索（用于快速匹配）
        """
        pass

    @abstractmethod
    def get_by_category(self, category: str,
                        limit: int = 10) -> List[KnowledgeItem]:
        """
        按分类获取知识
        """
        pass

    @abstractmethod
    def add(self, item: KnowledgeItem) -> bool:
        """
        添加知识（自动向量化）
        """
        pass

    @abstractmethod
    def update(self, item_id: str, updates: Dict) -> bool:
        """
        更新知识
        """
        pass

    # ---------------- 注入相关方法 ----------------

    def inject_for_intent(self, intent: str, user_input: str) -> str:
        """
        根据意图注入相关知识

        Args:
            intent: 意图类型
            user_input: 用户输入

        Returns:
            格式化后的知识文本（用于Prompt）
        """
        if intent == "health_consult":
            # 搜索症状相关知识
            results = self.search(user_input, top_k=3,
                                  filters={"category": "症状"})
        elif intent == "product_consult":
            # 搜索产品相关知识
            results = self.search(user_input, top_k=3,
                                  filters={"category": "产品"})
        elif intent == "knowledge_query":
            # 通用健康知识
            results = self.search(user_input, top_k=3)
        else:
            return ""

        return self._format_for_prompt(results)

    def _format_for_prompt(self, items: List[KnowledgeItem]) -> str:
        """格式化为Prompt可用的知识文本"""
        if not items:
            return ""

        parts = ["# 参考知识"]
        for i, item in enumerate(items, 1):
            parts.append(f"[{i}] {item.title}")
            parts.append(item.content[:300])  # 限制长度
            parts.append("")

        return "\n".join(parts)


# ---------------- 实现示例 ----------------

class MockKnowledgeAdapter(KnowledgeAdapter):
    """模拟实现（用于测试）"""

    def __init__(self):
        self._data: List[KnowledgeItem] = []
        self._init_mock_data()

    def _init_mock_data(self):
        """初始化模拟数据"""
        from datetime import datetime
        mock_items = [
            {
                "id": "k1",
                "title": "头痛的常见原因",
                "content": "头痛可能由多种原因引起：1.紧张性头痛 2.偏头痛 3.高血压 4.颈椎问题...",
                "category": "症状",
                "tags": ["头痛", "偏头痛", "头晕"]
            },
            {
                "id": "k2",
                "title": "鱼油的功效与作用",
                "content": "鱼油富含Omega-3，有助于心脑血管健康，降低血脂...",
                "category": "产品",
                "tags": ["鱼油", "心脑血管", "血脂"]
            },
            {
                "id": "k3",
                "title": "高血压的日常管理",
                "content": "高血压患者应注意：1.低盐饮食 2.规律运动 3.定期监测...",
                "category": "健康知识",
                "tags": ["高血压", "血压", "饮食"]
            }
        ]

        for item in mock_items:
            self._data.append(KnowledgeItem(
                id=item["id"],
                title=item["title"],
                content=item["content"],
                category=item["category"],
                tags=item["tags"],
                source="mock",
                create_time=datetime.now(),
                update_time=datetime.now(),
                metadata={}
            ))

    def search(self, query: str, top_k: int = 5,
               filters: Optional[Dict] = None) -> List[KnowledgeItem]:
        """简单关键词匹配（实际应使用向量检索）"""
        results = []
        for item in self._data:
            score = 0
            # 标题匹配
            if query in item.title:
                score += 10
            # 内容匹配
            if query in item.content:
                score += 5
            # 标签匹配
            for tag in item.tags:
                if tag in query or query in tag:
                    score += 8

            # 过滤
            if filters and "category" in filters:
                if item.category != filters["category"]:
                    continue

            if score > 0:
                results.append((score, item))

        # 按分数排序
        results.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in results[:top_k]]

    def keyword_search(self, keywords: List[str], top_k: int = 5) -> List[KnowledgeItem]:
        results = []
        for item in self._data:
            for kw in keywords:
                if kw in item.title or kw in item.content or kw in item.tags:
                    results.append(item)
                    break
        return results[:top_k]

    def get_by_category(self, category: str, limit: int = 10) -> List[KnowledgeItem]:
        return [item for item in self._data
                if item.category == category][:limit]

    def add(self, item: KnowledgeItem) -> bool:
        self._data.append(item)
        return True

    def update(self, item_id: str, updates: Dict) -> bool:
        for item in self._data:
            if item.id == item_id:
                for key, value in updates.items():
                    setattr(item, key, value)
                item.update_time = datetime.now()
                return True
        return False


# ---------------- 真实实现示例（使用Milvus）----------------

class MilvusKnowledgeAdapter(KnowledgeAdapter):
    """
    基于Milvus向量数据库的实现

    需要安装: pip install pymilvus
    """

    def __init__(self, host: str = "localhost", port: str = "19530",
                 collection_name: str = "knowledge"):
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self._client = None
        self._embedding_model = None

    def _get_client(self):
        """获取Milvus客户端（延迟初始化）"""
        if self._client is None:
            from pymilvus import MilvusClient
            self._client = MilvusClient(uri=f"http://{self.host}:{self.port}")
        return self._client

    def _get_embedding(self, text: str) -> List[float]:
        """获取文本向量（使用Embedding模型）"""
        # 实际应调用OpenAI、BGE等模型
        # 这里用随机向量模拟
        import random
        return [random.random() for _ in range(768)]

    def search(self, query: str, top_k: int = 5,
               filters: Optional[Dict] = None) -> List[KnowledgeItem]:
        """向量语义搜索"""
        client = self._get_client()
        query_vector = self._get_embedding(query)

        # 构建过滤条件
        filter_expr = ""
        if filters:
            conditions = []
            if "category" in filters:
                conditions.append(f'category == "{filters["category"]}"')
            if conditions:
                filter_expr = " and ".join(conditions)

        results = client.search(
            collection_name=self.collection_name,
            data=[query_vector],
            filter=filter_expr,
            limit=top_k,
            output_fields=["id", "title", "content", "category", "tags", "source"]
        )

        # 转换为KnowledgeItem
        items = []
        for result in results[0]:
            entity = result["entity"]
            items.append(KnowledgeItem(
                id=entity["id"],
                title=entity["title"],
                content=entity["content"],
                category=entity["category"],
                tags=entity["tags"].split(","),
                source=entity["source"],
                create_time=datetime.now(),
                update_time=datetime.now(),
                metadata={}
            ))

        return items

    def keyword_search(self, keywords: List[str], top_k: int = 5) -> List[KnowledgeItem]:
        """关键词搜索（使用Milvus的模糊查询）"""
        client = self._get_client()

        # 构建OR条件
        conditions = " or ".join([f'title like "%{kw}%"' for kw in keywords])

        results = client.query(
            collection_name=self.collection_name,
            filter=conditions,
            limit=top_k,
            output_fields=["id", "title", "content", "category", "tags"]
        )

        return [self._dict_to_item(r) for r in results]

    def get_by_category(self, category: str, limit: int = 10) -> List[KnowledgeItem]:
        client = self._get_client()
        results = client.query(
            collection_name=self.collection_name,
            filter=f'category == "{category}"',
            limit=limit
        )
        return [self._dict_to_item(r) for r in results]

    def add(self, item: KnowledgeItem) -> bool:
        """添加知识（自动向量化）"""
        client = self._get_client()

        # 生成向量
        if item.embedding is None:
            item.embedding = self._get_embedding(item.content)

        # 插入数据
        client.insert(
            collection_name=self.collection_name,
            data=[{
                "id": item.id,
                "title": item.title,
                "content": item.content,
                "category": item.category,
                "tags": ",".join(item.tags),
                "source": item.source,
                "embedding": item.embedding
            }]
        )
        return True

    def update(self, item_id: str, updates: Dict) -> bool:
        client = self._get_client()
        client.upsert(
            collection_name=self.collection_name,
            data=[{"id": item_id, **updates}]
        )
        return True

    def _dict_to_item(self, d: Dict) -> KnowledgeItem:
        return KnowledgeItem(
            id=d["id"],
            title=d["title"],
            content=d["content"],
            category=d["category"],
            tags=d.get("tags", "").split(","),
            source=d.get("source", ""),
            create_time=datetime.now(),
            update_time=datetime.now(),
            metadata={}
        )
