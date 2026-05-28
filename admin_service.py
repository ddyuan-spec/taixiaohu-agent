"""
后台管理系统 - 数据服务层 (修复版)
支持从GitHub加载预置知识库，解决Render临时磁盘问题
"""
import json
import os
import uuid
import re
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any

# ============================================================
# 数据目录与文件路径
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
KNOWLEDGE_FILE = os.path.join(DATA_DIR, "knowledge.json")
PROFILES_FILE = os.path.join(DATA_DIR, "profiles.json")
SESSIONS_FILE = os.path.join(DATA_DIR, "sessions.json")

# GitHub 预置知识库配置
GITHUB_KNOWLEDGE_URL = "https://raw.githubusercontent.com/ddyuan-spec/taixiaohu-agent/main/data/knowledge.json"

def _ensure_data_dir():
    """确保数据目录存在"""
    os.makedirs(DATA_DIR, exist_ok=True)

def _load_json(filepath: str, default: Any = None) -> Any:
    """加载 JSON 文件"""
    if not os.path.exists(filepath):
        return default if default is not None else []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return default if default is not None else []

def _save_json(filepath: str, data: Any):
    """保存 JSON 文件"""
    _ensure_data_dir()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _load_preset_knowledge():
    """从GitHub加载预置知识库（如果本地为空）"""
    try:
        # 检查本地是否已有知识库
        local_chunks = _load_json(KNOWLEDGE_FILE, [])
        if local_chunks:
            print(f"[KnowledgeService] 本地知识库已有 {len(local_chunks)} 个切片，跳过预置加载")
            return
        
        # 从GitHub加载
        print(f"[KnowledgeService] 本地知识库为空，尝试从GitHub加载预置数据...")
        response = requests.get(GITHUB_KNOWLEDGE_URL, timeout=10)
        if response.status_code == 200:
            preset_chunks = response.json()
            if isinstance(preset_chunks, list) and len(preset_chunks) > 0:
                _save_json(KNOWLEDGE_FILE, preset_chunks)
                print(f"[KnowledgeService] 成功从GitHub加载 {len(preset_chunks)} 个预置切片")
            else:
                print(f"[KnowledgeService] GitHub知识库为空或格式错误")
        else:
            print(f"[KnowledgeService] 从GitHub加载失败: HTTP {response.status_code}")
    except Exception as e:
        print(f"[KnowledgeService] 加载预置知识库失败: {e}")

# ============================================================
# 知识库服务
# ============================================================
class KnowledgeService:
    """知识库切片管理服务"""
    def __init__(self):
        _ensure_data_dir()
        # 启动时尝试加载预置知识库
        _load_preset_knowledge()
    
    def get_all_chunks(self) -> List[Dict]:
        """获取所有知识切片"""
        return _load_json(KNOWLEDGE_FILE, [])
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict]:
        """根据 ID 获取切片"""
        chunks = self.get_all_chunks()
        for chunk in chunks:
            if chunk["id"] == chunk_id:
                return chunk
        return None
    
    def add_chunk(self, title: str, content: str, source_file: str = "manual") -> Dict:
        """手动添加切片"""
        chunks = self.get_all_chunks()
        chunk = {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "content": content,
            "source_file": source_file,
            "call_count": 0,
            "last_called": None,
            "created_at": datetime.now().isoformat()
        }
        chunks.append(chunk)
        _save_json(KNOWLEDGE_FILE, chunks)
        return chunk
    
    def delete_chunk(self, chunk_id: str) -> bool:
        """删除切片"""
        chunks = self.get_all_chunks()
        new_chunks = [c for c in chunks if c["id"] != chunk_id]
        if len(new_chunks) == len(chunks):
            return False
        _save_json(KNOWLEDGE_FILE, new_chunks)
        return True
    
    def increment_call_count(self, chunk_id: str):
        """增加切片调用次数"""
        chunks = self.get_all_chunks()
        for chunk in chunks:
            if chunk["id"] == chunk_id:
                chunk["call_count"] = chunk.get("call_count", 0) + 1
                chunk["last_called"] = datetime.now().isoformat()
                break
        _save_json(KNOWLEDGE_FILE, chunks)
    
    def upload_and_slice(self, file_content: str, filename: str) -> List[Dict]:
        """
        上传文件并自动切片
        支持 .txt, .md, .csv, .json
        """
        chunks = self.get_all_chunks()
        new_chunks = []
        
        # 根据文件类型解析内容
        text_content = self._parse_file_content(file_content, filename)
        if not text_content.strip():
            return []
        
        # 切片：每 200-500 字一个切片
        sliced_texts = self._slice_text(text_content)
        
        for i, text in enumerate(sliced_texts):
            chunk = {
                "id": str(uuid.uuid4())[:8],
                "title": f"{filename} - 切片{i + 1}",
                "content": text.strip(),
                "source_file": filename,
                "call_count": 0,
                "last_called": None,
                "created_at": datetime.now().isoformat()
            }
            chunks.append(chunk)
            new_chunks.append(chunk)
        
        _save_json(KNOWLEDGE_FILE, chunks)
        return new_chunks
    
    def search_chunks(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        从上传的知识库中搜索相关切片（关键词匹配）
        用于 agent._get_knowledge_fallback 的扩展搜索
        """
        chunks = self.get_all_chunks()
        if not chunks:
            return []
        
        scored = []
        query_chars = set(query)
        
        for chunk in chunks:
            score = 0
            content = chunk.get("content", "")
            title = chunk.get("title", "")
            
            # 标题匹配
            if query in title:
                score += 10
            
            # 内容匹配 - 逐词匹配
            query_words = re.split(r'[\s，。、；：！？,.;:!?]+', query)
            query_words = [w for w in query_words if len(w) >= 2]
            for word in query_words:
                if word in content:
                    score += len(word)  # 匹配词越长，权重越高
            
            # 字符重叠度
            overlap = len(query_chars & set(content))
            if len(query_chars) > 0:
                score += overlap / len(query_chars) * 5
            
            if score > 0:
                scored.append((score, chunk))
        
        # 按分数排序
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [chunk for _, chunk in scored[:top_k]]
        
        # 更新调用次数
        for chunk in results:
            self.increment_call_count(chunk["id"])
        
        return results
    
    def get_stats(self) -> Dict:
        """获取知识库统计"""
        chunks = self.get_all_chunks()
        total_calls = sum(c.get("call_count", 0) for c in chunks)
        
        # 今日调用次数
        today = datetime.now().strftime("%Y-%m-%d")
        today_calls = sum(
            1 for c in chunks
            if c.get("last_called") and c["last_called"].startswith(today)
        )
        
        return {
            "total_chunks": len(chunks),
            "total_calls": total_calls,
            "today_calls": today_calls
        }
    
    def _parse_file_content(self, content: str, filename: str) -> str:
        """根据文件类型解析内容"""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        
        if ext == "json":
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    parts = []
                    for item in data:
                        if isinstance(item, dict):
                            parts.append(json.dumps(item, ensure_ascii=False))
                        else:
                            parts.append(str(item))
                    return "\n".join(parts)
                elif isinstance(data, dict):
                    return json.dumps(data, ensure_ascii=False, indent=2)
                return str(data)
            except json.JSONDecodeError:
                return content
        elif ext == "csv":
            lines = content.strip().split("\n")
            return "\n".join(lines)
        else:
            return content
    
    def _slice_text(self, text: str, min_len: int = 200, max_len: int = 500) -> List[str]:
        """
        将文本切片，每 200-500 字一个切片
        优先在句号、换行等位置切分
        """
        # 先按段落分割
        paragraphs = re.split(r'\n{2,}|\r\n{2,}', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        slices = []
        current = ""
        
        for para in paragraphs:
            if len(current) + len(para) + 1 <= max_len:
                if current:
                    current += "\n" + para
                else:
                    current = para
            else:
                # 当前段落加入后会超长，先保存当前内容
                if current:
                    if len(current) < min_len and slices:
                        slices[-1] += "\n" + current
                    else:
                        slices.append(current)
                
                # 处理超长段落：在句号处切分
                if len(para) > max_len:
                    sub_slices = self._split_long_paragraph(para, max_len)
                    slices.extend(sub_slices[:-1])
                    current = sub_slices[-1] if sub_slices else ""
                else:
                    current = para
        
        if current:
            if len(current) < min_len and slices:
                slices[-1] += "\n" + current
            else:
                slices.append(current)
        
        return slices
    
    def _split_long_paragraph(self, text: str, max_len: int) -> List[str]:
        """切分超长段落"""
        split_pattern = r'(?<=[。！？；\n])'
        sentences = re.split(split_pattern, text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        slices = []
        current = ""
        
        for sent in sentences:
            if len(current) + len(sent) <= max_len:
                current += sent
            else:
                if current:
                    slices.append(current)
                # 如果单句超长，强制切分
                if len(sent) > max_len:
                    for i in range(0, len(sent), max_len):
                        slices.append(sent[i:i + max_len])
                    current = ""
                else:
                    current = sent
        
        if current:
            slices.append(current)
        
        return slices if slices else [text]

# ============================================================
# 用户画像服务
# ============================================================
class ProfileService:
    """用户画像管理服务"""
    def __init__(self):
        _ensure_data_dir()
    
    def get_all_profiles(self) -> List[Dict]:
        """获取所有用户画像"""
        return _load_json(PROFILES_FILE, [])
    
    def get_profile_by_id(self, user_id: str) -> Optional[Dict]:
        """根据用户 ID 获取画像"""
        profiles = self.get_all_profiles()
        for p in profiles:
            if p["user_id"] == user_id:
                return p
        return None
    
    def create_or_update_profile(self, user_id: str, updates: Dict) -> Dict:
        """创建或更新用户画像"""
        profiles = self.get_all_profiles()
        existing = None
        for p in profiles:
            if p["user_id"] == user_id:
                existing = p
                break
        
        now = datetime.now().isoformat()
        
        if existing:
            # 记录变更历史
            history = existing.get("history", [])
            for key, new_value in updates.items():
                if key in ("user_id", "history", "created_at", "updated_at"):
                    continue
                old_value = existing.get(key)
                if old_value != new_value:
                    history.append({
                        "field": key,
                        "old": old_value,
                        "new": new_value,
                        "time": now,
                        "reason": "会话更新"
                    })
            existing["history"] = history[-50:]  # 保留最近50条
            
            # 更新字段
            for key, value in updates.items():
                if key not in ("user_id", "created_at"):
                    existing[key] = value
            existing["updated_at"] = now
            existing["completeness"] = self._calculate_completeness(existing)
        else:
            profile = {
                "user_id": user_id,
                "name": updates.get("name", ""),
                "age": updates.get("age", 0),
                "gender": updates.get("gender", ""),
                "chronic_diseases": updates.get("chronic_diseases", ""),
                "allergy_history": updates.get("allergy_history", ""),
                "current_medication": updates.get("current_medication", ""),
                "health_concerns": updates.get("health_concerns", ""),
                "completeness": 0.0,
                "history": [],
                "created_at": now,
                "updated_at": now
            }
            profile["completeness"] = self._calculate_completeness(profile)
            profiles.append(profile)
            existing = profile
        
        _save_json(PROFILES_FILE, profiles)
        return existing
    
    def get_profile_history(self, user_id: str) -> List[Dict]:
        """获取用户画像变更历史"""
        profile = self.get_profile_by_id(user_id)
        if not profile:
            return []
        return profile.get("history", [])
    
    def get_profile_sessions(self, user_id: str) -> List[Dict]:
        """获取用户的所有会话记录"""
        sessions = _load_json(SESSIONS_FILE, [])
        return [s for s in sessions if s.get("user_id") == user_id]
    
    def get_stats(self) -> Dict:
        """获取画像统计"""
        profiles = self.get_all_profiles()
        
        # 完整度分布
        distribution = {
            "low": 0,       # 0-30%
            "medium": 0,    # 30-70%
            "high": 0       # 70-100%
        }
        
        for p in profiles:
            c = p.get("completeness", 0)
            if c < 0.3:
                distribution["low"] += 1
            elif c < 0.7:
                distribution["medium"] += 1
            else:
                distribution["high"] += 1
        
        return {
            "total_profiles": len(profiles),
            "distribution": distribution
        }
    
    def _calculate_completeness(self, profile: Dict) -> float:
        """计算画像完整度"""
        fields = [
            profile.get("age", 0),
            profile.get("gender", ""),
            profile.get("chronic_diseases", ""),
            profile.get("current_medication", ""),
            profile.get("health_concerns", "")
        ]
        filled = sum(1 for f in fields if f)
        return round(filled / len(fields), 2) if fields else 0.0

# ============================================================
# 会话记录服务
# ============================================================
class SessionService:
    """会话记录管理服务"""
    def __init__(self):
        _ensure_data_dir()
    
    def get_all_sessions(self) -> List[Dict]:
        """获取所有会话记录"""
        return _load_json(SESSIONS_FILE, [])
    
    def add_session(self, user_id: str, messages: List[Dict]) -> Dict:
        """添加会话记录"""
        sessions = self.get_all_sessions()
        now = datetime.now().isoformat()
        session = {
            "id": str(uuid.uuid4())[:8],
            "user_id": user_id,
            "messages": messages,
            "message_count": len(messages),
            "created_at": now
        }
        sessions.append(session)
        _save_json(SESSIONS_FILE, sessions)
        return session
    
    def get_recent_sessions(self, limit: int = 10) -> List[Dict]:
        """获取最近 N 条会话记录"""
        sessions = self.get_all_sessions()
        sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return sessions[:limit]
    
    def get_session_by_id(self, session_id: str) -> Optional[Dict]:
        """根据 ID 获取会话"""
        sessions = self.get_all_sessions()
        for s in sessions:
            if s["id"] == session_id:
                return s
        return None

# ============================================================
# 全局服务实例
# ============================================================
knowledge_service = KnowledgeService()
profile_service = ProfileService()
session_service = SessionService()
