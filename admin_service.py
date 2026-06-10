"""
后台管理系统 - 数据服务层
负责知识库切片、用户画像、会话记录的 JSON 文件存储与查询
"""

import json
import os
import uuid
import re
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

# GitHub 配置
GITHUB_REPO = "ddyuan-spec/taixiaohu-agent"
GITHUB_BRANCH = "main"
GITHUB_KNOWLEDGE_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/data/knowledge.json"


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


# ============================================================
# 知识库服务
# ============================================================

class KnowledgeService:
    """知识库切片管理服务"""

    def __init__(self):
        _ensure_data_dir()

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
        if not chunk_id:
            return
        chunks = self.get_all_chunks()
        for chunk in chunks:
            if chunk["id"] == chunk_id:
                chunk["call_count"] = chunk.get("call_count", 0) + 1
                chunk["last_called"] = datetime.now().isoformat()
                break
        _save_json(KNOWLEDGE_FILE, chunks)
    
    def record_access(self, chunk_id: str):
        """记录切片被访问（increment_call_count的别名）"""
        self.increment_call_count(chunk_id)

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
            # 将 query 分词（简单按空格和标点分割）
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
                # 如果是列表，将每个元素转为文本
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
            # CSV: 按行分割，保留结构
            lines = content.strip().split("\n")
            return "\n".join(lines)
        else:
            # txt, md: 直接使用
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
                    # 如果当前内容太短，尝试合并
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
        # 在句号、问号、感叹号、分号处切分
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

    def load_from_github(self) -> Dict:
        """
        从 GitHub 加载知识库
        返回: {"success": bool, "message": str, "count": int}
        """
        import urllib.request
        import ssl
        
        try:
            # 创建 SSL 上下文（忽略证书验证）
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # 下载知识库
            req = urllib.request.Request(
                GITHUB_KNOWLEDGE_URL,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            
            with urllib.request.urlopen(req, context=ssl_context, timeout=30) as response:
                github_chunks = json.loads(response.read().decode('utf-8'))
            
            if not isinstance(github_chunks, list):
                return {"success": False, "message": "GitHub 数据格式错误", "count": 0}
            
            # 合并本地和 GitHub 数据（以 GitHub 为准，去重）
            existing_ids = set()
            local_chunks = self.get_all_chunks()
            for chunk in local_chunks:
                existing_ids.add(chunk.get("id"))
            
            added_count = 0
            for chunk in github_chunks:
                if chunk.get("id") not in existing_ids:
                    local_chunks.append(chunk)
                    added_count += 1
            
            # 保存合并后的数据
            _save_json(KNOWLEDGE_FILE, local_chunks)
            
            return {
                "success": True, 
                "message": f"成功从 GitHub 加载 {added_count} 个知识切片", 
                "count": added_count,
                "total": len(local_chunks)
            }
            
        except urllib.error.HTTPError as e:
            return {"success": False, "message": f"GitHub 请求失败: {e.code}", "count": 0}
        except urllib.error.URLError as e:
            return {"success": False, "message": f"网络错误: {str(e.reason)}", "count": 0}
        except json.JSONDecodeError:
            return {"success": False, "message": "GitHub 数据解析失败", "count": 0}
        except Exception as e:
            return {"success": False, "message": f"加载失败: {str(e)}", "count": 0}


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

    def create_profile(self, profile_data: Dict) -> Dict:
        """手动创建用户画像"""
        profiles = self.get_all_profiles()
        profiles.append(profile_data)
        _save_json(PROFILES_FILE, profiles)
        return profile_data

    def update_profile(self, user_id: str, updates: Dict) -> Optional[Dict]:
        """更新用户画像（供API调用）"""
        return self.create_or_update_profile(user_id, updates)

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
        # 按时间倒序
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
