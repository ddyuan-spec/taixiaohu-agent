"""
数据访问适配器模块
提供知识库、画像库、记忆库、Badcase库的抽象接口
"""

from .knowledge_adapter import KnowledgeAdapter
from .profile_adapter import ProfileAdapter
from .memory_adapter import MemoryAdapter
from .badcase_adapter import BadcaseAdapter

__all__ = ['KnowledgeAdapter', 'ProfileAdapter', 'MemoryAdapter', 'BadcaseAdapter']
