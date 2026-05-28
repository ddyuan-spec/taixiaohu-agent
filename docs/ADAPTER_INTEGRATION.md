# 泰小虎智能体 - 数据适配器集成指南

## 概述

本文档介绍如何将泰小虎智能体与外部知识库、画像库、记忆库、Badcase库进行集成。

## 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                         泰小虎智能体 Agent                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   意图路由    │  │  Prompt生成  │  │     对话管理          │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                 │                      │              │
│  ┌──────▼─────────────────▼──────────────────────▼──────────┐  │
│  │                    数据访问层 (Adapters)                   │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │  │
│  │  │ 知识库   │ │ 画像库   │ │ 记忆库   │ │Badcase库 │    │  │
│  │  │ Adapter │ │ Adapter │ │ Adapter │ │ Adapter │    │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘    │  │
│  └───────┼────────────┼────────────┼────────────┼──────────┘  │
└──────────┼────────────┼────────────┼────────────┼─────────────┘
           │            │            │            │
           ▼            ▼            ▼            ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
    │ 向量DB   │ │ 关系DB   │ │  NoSQL   │ │ 日志/分析│
    │ Milvus   │ │ MySQL    │ │  Redis   │ │    ES    │
    │Pinecone  │ │PostgreSQL│ │  Mongo   │ │ClickHouse│
    └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

## 快速开始

### 1. 安装依赖

```bash
pip install pymilvus sqlalchemy pymysql redis elasticsearch
```

### 2. 配置适配器

```python
from adapters import (
    KnowledgeAdapter, MockKnowledgeAdapter, MilvusKnowledgeAdapter,
    ProfileAdapter, MockProfileAdapter, MySQLProfileAdapter,
    MemoryAdapter, MockMemoryAdapter, RedisMemoryAdapter,
    BadcaseAdapter, MockBadcaseAdapter, ESBadcaseAdapter
)

# 开发环境使用Mock适配器
knowledge_adapter = MockKnowledgeAdapter()
profile_adapter = MockProfileAdapter()
memory_adapter = MockMemoryAdapter()
badcase_adapter = MockBadcaseAdapter()

# 生产环境使用真实适配器
knowledge_adapter = MilvusKnowledgeAdapter(
    host="localhost",
    port="19530",
    collection_name="knowledge"
)

profile_adapter = MySQLProfileAdapter(
    connection_string="mysql+pymysql://user:pass@localhost/taixiaohu"
)

memory_adapter = RedisMemoryAdapter(
    host="localhost",
    port=6379,
    db=0
)

badcase_adapter = ESBadcaseAdapter(
    hosts=["localhost:9200"],
    index="badcases"
)
```

### 3. 注入Agent

```python
from agent import TaiXiaoHuAgent

class TaiXiaoHuAgentWithAdapters(TaiXiaoHuAgent):
    def __init__(self, user_id: str = "anonymous"):
        super().__init__()
        self.user_id = user_id
        
        # 初始化适配器
        self.knowledge_adapter = MockKnowledgeAdapter()
        self.profile_adapter = MockProfileAdapter()
        self.memory_adapter = MockMemoryAdapter()
        self.badcase_adapter = MockBadcaseAdapter()
        
        # 会话开始时注入数据
        self._inject_session_data()
    
    def _inject_session_data(self):
        """注入会话数据"""
        # 1. 注入用户画像
        profile_text = self.profile_adapter.inject_for_session(self.user_id)
        if profile_text:
            self.system_prompt += f"\n\n{profile_text}"
        
        # 2. 注入长期记忆
        memory_text = self.memory_adapter.inject_for_session(self.user_id)
        if memory_text:
            self.system_prompt += f"\n\n{memory_text}"
    
    def process_message(self, user_input: str, intent: Optional[str] = None):
        """处理消息（带数据注入）"""
        # 1. 注入工作记忆
        context_text = self.memory_adapter.inject_for_turn(self.user_id, self.session_id)
        
        # 2. 根据意图注入知识
        if intent:
            knowledge_text = self.knowledge_adapter.inject_for_intent(intent, user_input)
        else:
            knowledge_text = ""
        
        # 3. 调用父类处理
        result = super().process_message(user_input, intent)
        
        # 4. 保存对话到记忆
        self.memory_adapter.save_dialogue_turn(
            self.user_id, self.session_id, "user", user_input
        )
        self.memory_adapter.save_dialogue_turn(
            self.user_id, self.session_id, "assistant", result["response"]
        )
        
        # 5. 自动检测Badcase
        badcase = self.badcase_adapter.auto_detect(
            self.user_id, self.session_id,
            user_input, result["response"],
            {"intent": intent, "state": result["state"]}
        )
        if badcase:
            self.badcase_adapter.add(badcase)
            print(f"[Badcase Detected] {badcase.title}")
        
        return result
```

## 各适配器详细说明

### 知识库适配器 (KnowledgeAdapter)

**功能**：
- 向量语义检索（RAG）
- 关键词搜索
- 按分类浏览
- 知识注入

**注入时机**：
1. 意图识别后：根据意图类型注入相关知识
2. 追问时：根据上下文注入深度知识

**示例**：
```python
# 健康咨询时注入症状知识
knowledge = knowledge_adapter.inject_for_intent(
    "health_consult", 
    "我最近头痛得厉害"
)
# 返回格式化知识文本，附加到Prompt
```

### 画像库适配器 (ProfileAdapter)

**功能**：
- 用户画像查询/更新
- 画像完整度计算
- 自动提取（从对话中）
- 画像注入

**注入时机**：
1. 会话开始时：注入完整画像
2. 推荐产品时：注入健康相关信息

**示例**：
```python
# 获取用户画像
profile = profile_adapter.get_profile("user_001")

# 从对话中提取并更新
extracted = profile_adapter.extract_from_dialogue("user_001", dialogue)
profile_adapter.update_profile("user_001", extracted)

# 注入画像
profile_text = profile_adapter.inject_for_session("user_001")
```

### 记忆库适配器 (MemoryAdapter)

**功能**：
- 短期记忆（对话历史，TTL=24h）
- 长期记忆（重要事实，永久）
- 工作记忆（当前上下文，TTL=2h）
- 记忆整合（自动摘要）

**注入时机**：
1. 每次对话前：注入工作记忆
2. 会话开始时：注入长期记忆

**示例**：
```python
# 保存对话
memory_adapter.save_dialogue_turn(user_id, session_id, "user", "你好")

# 保存重要事实
memory_adapter.save_fact(user_id, "用户有高血压", importance=0.9)

# 更新上下文
memory_adapter.update_context(user_id, session_id, "current_intent", "health_consult")

# 注入记忆
context = memory_adapter.inject_for_turn(user_id, session_id)
```

### Badcase库适配器 (BadcaseAdapter)

**功能**：
- 自动检测潜在问题
- 人工标注
- 根因分析
- 修复追踪
- 反馈学习

**注入时机**：
1. 每次对话后：自动检测
2. 用户反馈时：记录问题

**示例**：
```python
# 自动检测
badcase = badcase_adapter.auto_detect(
    user_id, session_id,
    user_input, agent_response,
    context
)

if badcase:
    badcase_adapter.add(badcase)
    
    # 分析根因
    root_cause = badcase_adapter.analyze_root_cause(badcase)
    
    # 生成修复建议
    suggestion = badcase_adapter.suggest_fix(badcase)
    
    # 更新状态
    badcase_adapter.update(badcase.id, {
        "status": BadcaseStatus.FIXING,
        "root_cause": root_cause,
        "fix_suggestion": suggestion,
        "assignee": "developer_001"
    })

# 生成报告
report = badcase_adapter.generate_report(
    start_time=datetime(2026, 1, 1),
    end_time=datetime(2026, 1, 31)
)
```

## 数据库Schema

### MySQL - 用户画像表

```sql
CREATE TABLE user_profiles (
    user_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(64),
    age INT,
    gender VARCHAR(8),
    phone VARCHAR(20),
    chronic_diseases JSON,
    allergy_history JSON,
    family_history JSON,
    current_medication JSON,
    health_supplements JSON,
    health_concerns JSON,
    health_goals JSON,
    lifestyle JSON,
    completeness FLOAT DEFAULT 0,
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_inject_time TIMESTAMP NULL
);
```

### Milvus - 知识库Collection

```python
from pymilvus import FieldSchema, CollectionSchema, DataType

fields = [
    FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
    FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=256),
    FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=4096),
    FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=64),
    FieldSchema(name="tags", dtype=DataType.VARCHAR, max_length=512),
    FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=128),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768)
]

schema = CollectionSchema(fields, "knowledge_base")
```

### Redis - 记忆存储

```
Key: memory:{user_id}:{memory_type}:{memory_id}
Type: Hash
Fields:
  - id
  - content
  - importance
  - create_time
  - metadata (JSON)
TTL: 根据memory_type设置

Index: memory:index:{user_id}
Type: Set
Members: [memory_key1, memory_key2, ...]
```

### Elasticsearch - Badcase索引

```json
{
  "mappings": {
    "properties": {
      "id": {"type": "keyword"},
      "user_id": {"type": "keyword"},
      "badcase_type": {"type": "keyword"},
      "title": {"type": "text"},
      "description": {"type": "text"},
      "status": {"type": "keyword"},
      "severity": {"type": "integer"},
      "create_time": {"type": "date"},
      "context": {"type": "object"}
    }
  }
}
```

## 部署建议

### 开发环境

```python
# 全部使用Mock适配器
adapters = {
    "knowledge": MockKnowledgeAdapter(),
    "profile": MockProfileAdapter(),
    "memory": MockMemoryAdapter(),
    "badcase": MockBadcaseAdapter()
}
```

### 测试环境

```python
# 混合使用
adapters = {
    "knowledge": MockKnowledgeAdapter(),  # 使用Mock数据
    "profile": MySQLProfileAdapter("mysql://test-db"),
    "memory": RedisMemoryAdapter("localhost", 6379),
    "badcase": MockBadcaseAdapter()
}
```

### 生产环境

```python
# 全部使用真实适配器
adapters = {
    "knowledge": MilvusKnowledgeAdapter("milvus-cluster"),
    "profile": MySQLProfileAdapter("mysql://prod-db"),
    "memory": RedisMemoryAdapter("redis-cluster", 6379),
    "badcase": ESBadcaseAdapter(["es-node1:9200", "es-node2:9200"])
}
```

## 监控指标

| 指标 | 说明 | 告警阈值 |
|------|------|---------|
| 知识库检索延迟 | 向量搜索P99延迟 | > 200ms |
| 画像查询延迟 | 数据库查询P99延迟 | > 50ms |
| 记忆写入延迟 | Redis写入P99延迟 | > 20ms |
| Badcase数量 | 每日新增Badcase数 | > 100 |
| 修复率 | 已修复/总Badcase | < 80% |

## 常见问题

### Q1: 如何切换适配器实现？

A: 通过配置或环境变量切换：

```python
import os

if os.getenv("ENV") == "production":
    adapter = MilvusKnowledgeAdapter()
else:
    adapter = MockKnowledgeAdapter()
```

### Q2: 如何处理适配器故障？

A: 使用降级策略：

```python
try:
    result = knowledge_adapter.search(query)
except Exception as e:
    logger.error(f"Knowledge search failed: {e}")
    # 降级到Mock或空结果
    result = []
```

### Q3: 如何保证数据一致性？

A: 关键操作使用事务或补偿机制：

```python
# 画像更新时同时更新记忆
profile_adapter.update_profile(user_id, updates)
memory_adapter.save_fact(user_id, f"用户更新了{field}")
```

## 扩展开发

如需添加新的适配器实现：

1. 继承对应的抽象基类
2. 实现所有抽象方法
3. 添加单元测试
4. 更新配置文档

示例：

```python
class CustomKnowledgeAdapter(KnowledgeAdapter):
    def __init__(self, config: Dict):
        self.config = config
    
    def search(self, query: str, top_k: int = 5, 
               filters: Optional[Dict] = None) -> List[KnowledgeItem]:
        # 实现搜索逻辑
        pass
    
    # ... 实现其他方法
```
