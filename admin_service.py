"""
后台管理系统 - 数据服务层 V2 (强制GitHub重载版)
解决Render临时磁盘问题：每次启动从GitHub加载预置知识库
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

# GitHub 预置知识库URL（Raw格式）
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
    except (json.JSONDecodeError, IOError) as e:
        print(f"[LoadJSON] 加载失败 {filepath}: {e}")
        return default if default is not None else []

def _save_json(filepath: str, data: Any):
    """保存 JSON 文件"""
    _ensure_data_dir()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _force_load_from_github() -> List[Dict]:
    """
    强制从GitHub加载知识库
    这是解决Render临时磁盘问题的关键函数
    """
    try:
        print(f"[KnowledgeLoader] 正在从GitHub加载知识库...")
        print(f"[KnowledgeLoader] URL: {GITHUB_KNOWLEDGE_URL}")
        
        response = requests.get(
            GITHUB_KNOWLEDGE_URL, 
            timeout=15,
            headers={'Cache-Control': 'no-cache'}
        )
        
        if response.status_code == 200:
            chunks = response.json()
            if isinstance(chunks, list) and len(chunks) > 0:
                # 保存到本地文件
                _save_json(KNOWLEDGE_FILE, chunks)
                print(f"[KnowledgeLoader] ✅ 成功加载 {len(chunks)} 个切片")
                # 打印前5个切片标题用于验证
                for i, chunk in enumerate(chunks[:5], 1):
                    print(f"[KnowledgeLoader]   {i}. {chunk.get('title', '无标题')[:50]}")
                if len(chunks) > 5:
                    print(f"[KnowledgeLoader]   ... 还有 {len(chunks)-5} 个切片")
                return chunks
            else:
                print(f"[KnowledgeLoader] ⚠️ GitHub数据为空或格式错误")
                return []
        else:
            print(f"[KnowledgeLoader] ❌ HTTP错误: {response.status_code}")
            return []
    except Exception as e:
        print(f"[KnowledgeLoader] ❌ 加载异常: {e}")
        return []

# ============================================================
# 知识库服务
# ============================================================
class KnowledgeService:
    """知识库切片管理服务 - V2强制重载版"""
    
    _cached_chunks: List[Dict] = []  # 类级缓存
    _loaded: bool = False  # 是否已加载标记
    
    def __init__(self):
        _ensure_data_dir()
        # 每次实例化都强制从GitHub加载（确保Render重启后能恢复数据）
        self._load_knowledge()
    
    def _load_knowledge(self):
        """加载知识库：优先从GitHub强制加载"""
        if not KnowledgeService._loaded:
            # 第一次加载：强制从GitHub获取
            chunks = _force_load_from_github()
            if chunks:
                KnowledgeService._cached_chunks = chunks
                KnowledgeService._loaded = True
            else:
                # GitHub失败，尝试本地文件
                print(f"[KnowledgeService] GitHub加载失败，尝试本地文件...")
                KnowledgeService._cached_chunks = _load_json(KNOWLEDGE_FILE, [])
                KnowledgeService._loaded = True
        else:
            # 已加载过，检查本地文件是否存在（可能被清空）
            local_chunks = _load_json(KNOWLEDGE_FILE, [])
            if not local_chunks and KnowledgeService._cached_chunks:
                # 本地为空但缓存有数据，恢复本地文件
                print(f"[KnowledgeService] 本地文件为空，从缓存恢复 {len(KnowledgeService._cached_chunks)} 个切片")
                _save_json(KNOWLEDGE_FILE, KnowledgeService._cached_chunks)
            elif local_chunks:
                # 本地有数据，更新缓存
                KnowledgeService._cached_chunks = local_chunks
    
    def get_all_chunks(self) -> List[Dict]:
        """获取所有知识切片"""
        # 每次获取都检查本地文件
        local = _load_json(KNOWLEDGE_FILE, [])
        if local:
            return local
        # 本地为空，返回缓存
        return KnowledgeService._cached_chunks
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict]:
        """根据 ID 获取切片"""
        chunks = self.get_all_chunks()
        for chunk in chunks:
            if chunk.get("id") == chunk_id:
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
        KnowledgeService._cached_chunks = chunks
        return chunk
    
    def delete_chunk(self, chunk_id: str) -> bool:
        """删除切片"""
        chunks = self.get_all_chunks()
        new_chunks = [c for c in chunks if c.get("id") != chunk_id]
        if len(new_chunks) == len(chunks):
            return False
        _save_json(KNOWLEDGE_FILE, new_chunks)
        KnowledgeService._cached_chunks = new_chunks
        return True
    
    def increment_call_count(self, chunk_id: str):
        """增加切片调用次数"""
        chunks = self.get_all_chunks()
        for chunk in chunks:
            if chunk.get("id") == chunk_id:
                chunk["call_count"] = chunk.get("call_count", 0) + 1
                chunk["last_called"] = datetime.now().isoformat()
                break
        _save_json(KNOWLEDGE_FILE, chunks)
        KnowledgeService._cached_chunks = chunks
    
    def upload_and_slice(self, file_content: str, filename: str) -> List[Dict]:
        """上传文件并自动切片"""
        chunks = self.get_all_chunks()
        new_chunks = []
        
        text_content = self._parse_file_content(file_content, filename)
        if not text_content.strip():
            return []
        
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
        KnowledgeService._cached_chunks = chunks
        return new_chunks
    
    def search_chunks(self, query: str, top_k: int = 3) -> List[Dict]:
        """搜索相关切片"""
        chunks = self.get_all_chunks()
        if not chunks:
            return []
        
        scored = []
        query_chars = set(query)
        
        for chunk in chunks:
            score = 0
            content = chunk.get("content", "")
            title = chunk.get("title", "")
            
            if query in title:
                score += 10
            
            query_words = re.split(r'[\s，。、；：！？,.;:!?]+', query)
            query_words = [w for w in query_words if len(w) >= 2]
            for word in query_words:
                if word in content:
                    score += len(word)
            
            overlap = len(query_chars & set(content))
            if len(query_chars) > 0:
                score += overlap / len(query_chars) * 5
            
            if score > 0:
                scored.append((score, chunk))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [chunk for _, chunk in scored[:top_k]]
        
        for chunk in results:
            self.increment_call_count(chunk["id"])
        
        return results
    
    def get_stats(self) -> Dict:
        """获取知识库统计"""
        chunks = self.get_all_chunks()
        total_calls = sum(c.get("call_count", 0) for c in chunks)
        
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
        """将文本切片"""
        paragraphs = re.split(r'\n{2,}|\r\n{2,}', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        slices = []
        current = ""
        
        for para in paragraphs:
            if len(current) + len(para) + 1 <= max_len:
                current = current + "\n" + para if current else para
            else:
                if current:
                    if len(current) < min_len and slices:
                        slices[-1] += "\n" + current
                    else:
                        slices.append(current)
                
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
            if p.get("user_id") == user_id:
                return p
        return None
    
    def create_or_update_profile(self, user_id: str, updates: Dict) -> Dict:
        """创建或更新用户画像"""
        profiles = self.get_all_profiles()
        existing = None
        for p in profiles:
            if p.get("user_id") == user_id:
                existing = p
                break
        
        now = datetime.now().isoformat()
        
        if existing:
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
            existing["history"] = history[-50:]
            
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
        
        distribution = {"low": 0, "medium": 0, "high": 0}
        
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
            if s.get("id") == session_id:
                return s
        return None

# ============================================================
# 全局服务实例
# ============================================================
knowledge_service = KnowledgeService()
profile_service = ProfileService()
session_service = SessionService()
