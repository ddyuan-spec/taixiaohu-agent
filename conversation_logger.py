"""
对话记录日志系统
记录用户与AI的完整对话流程，包括意图识别、产品推荐、知识库调用等
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

# 数据存储目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONVERSATION_LOG_DIR = os.path.join(DATA_DIR, "conversation_logs")

# 确保目录存在
os.makedirs(CONVERSATION_LOG_DIR, exist_ok=True)


class MessageType(Enum):
    """消息类型"""
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class IntentType(Enum):
    """意图类型"""
    HEALTH_CONSULT = "health_consult"
    PRODUCT_CONSULT = "product_consult"
    KNOWLEDGE_QUERY = "knowledge_query"
    GREETING = "greeting"
    OTHER = "other"


@dataclass
class KnowledgeSource:
    """知识库来源文档（单个切片）"""
    file_name: str = ""           # 源文件名
    chunk_id: str = ""            # 切片ID
    chunk_content: str = ""       # 切片内容摘要
    relevance: float = 0.0        # 相似度分数 0-1


@dataclass
class KnowledgeBaseCall:
    """知识库调用记录"""
    query: str
    intent: str
    results_count: int
    product_ids: List[str]
    response_time_ms: int
    sources: List[KnowledgeSource] = field(default_factory=list)  # 命中的源文档
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class LLMCall:
    """LLM调用记录"""
    module: str  # 调用的模块名称
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    response_time_ms: int
    success: bool
    error_message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ConversationMessage:
    """对话消息记录"""
    message_id: str
    message_type: str  # user/agent/system
    content: str
    intent: Optional[str] = None
    intent_confidence: float = 0.0
    state: Optional[str] = None
    recommended_products: List[str] = field(default_factory=list)
    knowledge_base_calls: List[KnowledgeBaseCall] = field(default_factory=list)
    llm_calls: List[LLMCall] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ConversationSession:
    """对话会话记录"""
    session_id: str
    user_id: str
    started_at: str
    ended_at: Optional[str] = None
    messages: List[ConversationMessage] = field(default_factory=list)
    user_profile: Dict[str, Any] = field(default_factory=dict)
    total_messages: int = 0
    is_active: bool = True
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


class ConversationLogger:
    """对话记录日志器"""
    
    def __init__(self):
        self.sessions: Dict[str, ConversationSession] = {}
        self._load_existing_sessions()
    
    def _load_existing_sessions(self):
        """加载已存在的会话记录"""
        print(f"[ConversationLogger] 尝试加载会话目录: {CONVERSATION_LOG_DIR}")
        print(f"[ConversationLogger] 目录是否存在: {os.path.exists(CONVERSATION_LOG_DIR)}")
        
        if not os.path.exists(CONVERSATION_LOG_DIR):
            print(f"[ConversationLogger] 目录不存在，跳过加载")
            return
        
        files = [f for f in os.listdir(CONVERSATION_LOG_DIR) if f.endswith('.json')]
        print(f"[ConversationLogger] 找到 {len(files)} 个JSON文件: {files}")
        
        for filename in files:
            try:
                filepath = os.path.join(CONVERSATION_LOG_DIR, filename)
                print(f"[ConversationLogger] 正在加载: {filename}")
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    session = self._dict_to_session(data)
                    self.sessions[session.session_id] = session
                    print(f"[ConversationLogger] 成功加载: {session.session_id}, 消息数: {len(session.messages)}")
            except Exception as e:
                print(f"[ConversationLogger] 加载会话记录失败 {filename}: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"[ConversationLogger] 总共加载了 {len(self.sessions)} 个会话")
    
    def _dict_to_session(self, data: Dict) -> ConversationSession:
        """将字典转换为 ConversationSession 对象，递归处理嵌套结构"""
        # 处理 messages 列表
        messages = []
        for msg_data in data.get('messages', []):
            # 处理 knowledge_base_calls
            kb_calls = []
            for kb in msg_data.get('knowledge_base_calls', []):
                # 处理 sources 嵌套
                sources = []
                for src in kb.get('sources', []):
                    sources.append(KnowledgeSource(**src))
                kb_obj = KnowledgeBaseCall(
                    query=kb.get('query', ''),
                    intent=kb.get('intent', ''),
                    results_count=kb.get('results_count', 0),
                    product_ids=kb.get('product_ids', []),
                    response_time_ms=kb.get('response_time_ms', 0),
                    sources=sources,
                    timestamp=kb.get('timestamp', datetime.now().isoformat())
                )
                kb_calls.append(kb_obj)
            
            # 处理 llm_calls
            llm_calls = []
            for llm in msg_data.get('llm_calls', []):
                llm_calls.append(LLMCall(**llm))
            
            message = ConversationMessage(
                message_id=msg_data.get('message_id', ''),
                message_type=msg_data.get('message_type', ''),
                content=msg_data.get('content', ''),
                intent=msg_data.get('intent'),
                intent_confidence=msg_data.get('intent_confidence', 0.0),
                state=msg_data.get('state'),
                recommended_products=msg_data.get('recommended_products', []),
                knowledge_base_calls=kb_calls,
                llm_calls=llm_calls,
                timestamp=msg_data.get('timestamp', datetime.now().isoformat())
            )
            messages.append(message)
        
        return ConversationSession(
            session_id=data.get('session_id', ''),
            user_id=data.get('user_id', ''),
            started_at=data.get('started_at', ''),
            ended_at=data.get('ended_at'),
            messages=messages,
            user_profile=data.get('user_profile', {}),
            total_messages=data.get('total_messages', len(messages)),
            is_active=data.get('is_active', True)
        )
    
    def create_session(self, session_id: str, user_id: str = "") -> ConversationSession:
        """创建新会话"""
        session = ConversationSession(
            session_id=session_id,
            user_id=user_id,
            started_at=datetime.now().isoformat()
        )
        self.sessions[session_id] = session
        self._save_session(session)
        return session
    
    def get_or_create_session(self, session_id: str, user_id: str = "") -> ConversationSession:
        """获取或创建会话"""
        if session_id not in self.sessions:
            return self.create_session(session_id, user_id)
        return self.sessions[session_id]
    
    def log_user_message(self, session_id: str, content: str, user_id: str = "") -> ConversationMessage:
        """记录用户消息"""
        session = self.get_or_create_session(session_id, user_id)
        
        message = ConversationMessage(
            message_id=f"{session_id}_user_{len(session.messages)}",
            message_type=MessageType.USER.value,
            content=content
        )
        
        session.messages.append(message)
        session.total_messages = len(session.messages)
        self._save_session(session)
        
        return message
    
    def log_agent_response(self, session_id: str, content: str, 
                          intent: str = None, intent_confidence: float = 0.0,
                          state: str = None, recommended_products: List[str] = None,
                          knowledge_base_calls: List[KnowledgeBaseCall] = None,
                          llm_calls: List[LLMCall] = None) -> ConversationMessage:
        """记录AI回复"""
        session = self.get_or_create_session(session_id)
        
        message = ConversationMessage(
            message_id=f"{session_id}_agent_{len(session.messages)}",
            message_type=MessageType.AGENT.value,
            content=content,
            intent=intent,
            intent_confidence=intent_confidence,
            state=state,
            recommended_products=recommended_products or [],
            knowledge_base_calls=knowledge_base_calls or [],
            llm_calls=llm_calls or []
        )
        
        session.messages.append(message)
        session.total_messages = len(session.messages)
        self._save_session(session)
        
        return message
    
    def log_knowledge_base_call(self, session_id: str, query: str, intent: str,
                                results_count: int, product_ids: List[str],
                                response_time_ms: int,
                                sources: List[Dict] = None):
        """记录知识库调用"""
        session = self.get_or_create_session(session_id)

        # 构建 sources
        source_objs = []
        if sources:
            for src in sources:
                source_objs.append(KnowledgeSource(
                    file_name=src.get('file_name', ''),
                    chunk_id=src.get('chunk_id', ''),
                    chunk_content=src.get('chunk_content', ''),
                    relevance=src.get('relevance', 0.0)
                ))

        call = KnowledgeBaseCall(
            query=query,
            intent=intent,
            results_count=results_count,
            product_ids=product_ids,
            response_time_ms=response_time_ms,
            sources=source_objs,
            timestamp=datetime.now().isoformat()
        )

        # 添加到最后一条AI回复中
        if session.messages and session.messages[-1]:
            last_msg = session.messages[-1]
            if isinstance(last_msg, dict):
                if last_msg.get('message_type') == 'agent':
                    if 'knowledge_base_calls' not in last_msg:
                        last_msg['knowledge_base_calls'] = []
                    last_msg['knowledge_base_calls'].append(asdict(call))
                    self._save_session(session)
            elif hasattr(last_msg, 'message_type') and last_msg.message_type == MessageType.AGENT.value:
                last_msg.knowledge_base_calls.append(call)
    
    def log_llm_call(self, session_id: str, module: str, prompt_tokens: int,
                     completion_tokens: int, total_tokens: int,
                     response_time_ms: int, success: bool, error_message: str = ""):
        """记录LLM调用"""
        session = self.get_or_create_session(session_id)
        
        call = {
            'module': module,
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': total_tokens,
            'response_time_ms': response_time_ms,
            'success': success,
            'error_message': error_message,
            'timestamp': datetime.now().isoformat()
        }
        
        # 添加到最后一条AI回复中
        if session.messages and session.messages[-1]:
            last_msg = session.messages[-1]
            if isinstance(last_msg, dict):
                if last_msg.get('message_type') == 'agent':
                    if 'llm_calls' not in last_msg:
                        last_msg['llm_calls'] = []
                    last_msg['llm_calls'].append(call)
                    self._save_session(session)
            elif hasattr(last_msg, 'message_type') and last_msg.message_type == MessageType.AGENT.value:
                last_msg.llm_calls.append(LLMCall(**call))
            self._save_session(session)
    
    def update_user_profile(self, session_id: str, profile: Dict[str, Any]):
        """更新用户画像"""
        session = self.get_or_create_session(session_id)
        session.user_profile.update(profile)
        self._save_session(session)
    
    def end_session(self, session_id: str):
        """结束会话"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.ended_at = datetime.now().isoformat()
            session.is_active = False
            self._save_session(session)
    
    def _save_session(self, session: ConversationSession):
        """保存会话到文件"""
        filepath = os.path.join(CONVERSATION_LOG_DIR, f"{session.session_id}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)
    
    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """获取会话"""
        return self.sessions.get(session_id)
    
    def get_all_sessions(self, limit: int = 100) -> List[ConversationSession]:
        """获取所有会话（按时间倒序，每次从磁盘刷新）"""
        self._load_existing_sessions()
        sessions = sorted(
            self.sessions.values(),
            key=lambda s: s.started_at,
            reverse=True
        )
        return sessions[:limit]
    
    def get_active_sessions(self) -> List[ConversationSession]:
        """获取活跃会话"""
        return [s for s in self.sessions.values() if s.is_active]
    
    def get_knowledge_base_stats(self) -> Dict[str, Any]:
        """获取知识库调用统计"""
        stats = {
            "total_calls": 0,
            "calls_by_intent": {},
            "calls_by_product": {},
            "avg_response_time_ms": 0
        }
        
        total_time = 0
        for session in self.sessions.values():
            for msg in session.messages:
                for call in msg.knowledge_base_calls:
                    stats["total_calls"] += 1
                    
                    # 按意图统计
                    intent = call.intent or "unknown"
                    stats["calls_by_intent"][intent] = stats["calls_by_intent"].get(intent, 0) + 1
                    
                    # 按产品统计
                    for pid in call.product_ids:
                        stats["calls_by_product"][pid] = stats["calls_by_product"].get(pid, 0) + 1
                    
                    total_time += call.response_time_ms
        
        if stats["total_calls"] > 0:
            stats["avg_response_time_ms"] = round(total_time / stats["total_calls"], 2)
        
        return stats


# 全局日志器实例
_conversation_logger = None


def get_conversation_logger() -> ConversationLogger:
    """获取全局对话日志器"""
    global _conversation_logger
    if _conversation_logger is None:
        _conversation_logger = ConversationLogger()
    return _conversation_logger
