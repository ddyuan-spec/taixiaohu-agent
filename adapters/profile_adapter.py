"""
用户画像库适配器
支持：画像查询、更新、自动收集
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class UserProfile:
    """用户画像数据"""
    user_id: str
    name: str = ""
    age: int = 0
    gender: str = ""
    phone: str = ""

    # 健康状况
    chronic_diseases: List[str] = None  # 慢性病列表
    allergy_history: List[str] = None   # 过敏史
    family_history: List[str] = None    # 家族病史

    # 用药情况
    current_medication: List[Dict] = None  # [{"name": "", "dosage": "", "frequency": ""}]
    health_supplements: List[Dict] = None  # 保健品服用情况

    # 健康关注点
    health_concerns: List[str] = None   # 关注的健康问题
    health_goals: List[str] = None      # 健康目标

    # 生活方式
    lifestyle: Dict[str, Any] = None    # {"smoking": False, "drinking": "偶尔", "exercise": "每周2次"}

    # 元数据
    completeness: float = 0.0           # 画像完整度 0-1
    create_time: datetime = None
    update_time: datetime = None
    last_inject_time: datetime = None   # 上次注入时间

    def __post_init__(self):
        if self.chronic_diseases is None:
            self.chronic_diseases = []
        if self.allergy_history is None:
            self.allergy_history = []
        if self.family_history is None:
            self.family_history = []
        if self.current_medication is None:
            self.current_medication = []
        if self.health_supplements is None:
            self.health_supplements = []
        if self.health_concerns is None:
            self.health_concerns = []
        if self.health_goals is None:
            self.health_goals = []
        if self.lifestyle is None:
            self.lifestyle = {}
        if self.create_time is None:
            self.create_time = datetime.now()
        if self.update_time is None:
            self.update_time = datetime.now()

    def to_dict(self) -> Dict:
        return {
            "user_id": self.user_id,
            "name": self.name,
            "age": self.age,
            "gender": self.gender,
            "phone": self.phone,
            "chronic_diseases": self.chronic_diseases,
            "allergy_history": self.allergy_history,
            "family_history": self.family_history,
            "current_medication": self.current_medication,
            "health_supplements": self.health_supplements,
            "health_concerns": self.health_concerns,
            "health_goals": self.health_goals,
            "lifestyle": self.lifestyle,
            "completeness": self.completeness,
            "create_time": self.create_time.isoformat() if self.create_time else None,
            "update_time": self.update_time.isoformat() if self.update_time else None,
            "last_inject_time": self.last_inject_time.isoformat() if self.last_inject_time else None
        }

    def calculate_completeness(self) -> float:
        """计算画像完整度"""
        fields = [
            self.name, self.age > 0, self.gender,
            len(self.chronic_diseases) > 0,
            len(self.current_medication) > 0,
            len(self.health_concerns) > 0
        ]
        self.completeness = sum(1 for f in fields if f) / len(fields)
        return self.completeness


class ProfileAdapter(ABC):
    """
    用户画像适配器抽象基类

    注入时机：
    1. 会话开始时：注入完整画像
    2. 画像更新时：实时更新并重新注入
    3. 推荐产品时：注入相关画像信息（如慢性病、过敏史）
    """

    @abstractmethod
    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        获取用户画像

        Args:
            user_id: 用户唯一标识

        Returns:
            用户画像对象，不存在返回None
        """
        pass

    @abstractmethod
    def update_profile(self, user_id: str, updates: Dict) -> bool:
        """
        更新用户画像（增量更新）

        Args:
            user_id: 用户ID
            updates: 更新字段 {"age": 60, "chronic_diseases": ["高血压"]}

        Returns:
            是否成功
        """
        pass

    @abstractmethod
    def create_profile(self, profile: UserProfile) -> bool:
        """
        创建新用户画像
        """
        pass

    @abstractmethod
    def extract_from_dialogue(self, user_id: str, dialogue: List[Dict]) -> Dict:
        """
        从对话中提取画像信息

        Args:
            user_id: 用户ID
            dialogue: 对话历史 [{"role": "user", "content": ""}, ...]

        Returns:
            提取到的画像字段
        """
        pass

    # ---------------- 注入相关方法 ----------------

    def inject_for_session(self, user_id: str) -> str:
        """
        会话开始时注入画像

        Returns:
            格式化后的画像文本（用于System Prompt）
        """
        profile = self.get_profile(user_id)
        if not profile:
            return ""

        # 更新注入时间
        profile.last_inject_time = datetime.now()
        self.update_profile(user_id, {"last_inject_time": profile.last_inject_time})

        return self._format_for_prompt(profile)

    def inject_for_recommendation(self, user_id: str) -> str:
        """
        产品推荐时注入相关画像（过滤敏感信息）
        """
        profile = self.get_profile(user_id)
        if not profile:
            return ""

        # 只返回与推荐相关的信息
        parts = ["# 用户健康信息"]

        if profile.age > 0:
            parts.append(f"年龄：{profile.age}岁")
        if profile.gender:
            parts.append(f"性别：{profile.gender}")
        if profile.chronic_diseases:
            parts.append(f"慢性病：{'、'.join(profile.chronic_diseases)}")
        if profile.allergy_history:
            parts.append(f"过敏史：{'、'.join(profile.allergy_history)}")
        if profile.current_medication:
            meds = [m["name"] for m in profile.current_medication]
            parts.append(f"当前用药：{'、'.join(meds)}")
        if profile.health_concerns:
            parts.append(f"关注问题：{'、'.join(profile.health_concerns)}")

        return "\n".join(parts)

    def _format_for_prompt(self, profile: UserProfile) -> str:
        """格式化为Prompt可用的文本"""
        parts = ["# 用户画像"]

        if profile.name:
            parts.append(f"姓名：{profile.name}")
        if profile.age > 0:
            parts.append(f"年龄：{profile.age}岁")
        if profile.gender:
            parts.append(f"性别：{profile.gender}")

        if profile.chronic_diseases:
            parts.append(f"\n慢性病：{'、'.join(profile.chronic_diseases)}")
        if profile.allergy_history:
            parts.append(f"过敏史：{'、'.join(profile.allergy_history)}")
        if profile.family_history:
            parts.append(f"家族病史：{'、'.join(profile.family_history)}")

        if profile.current_medication:
            parts.append(f"\n当前用药：")
            for med in profile.current_medication:
                parts.append(f"  - {med['name']} {med.get('dosage', '')} {med.get('frequency', '')}")

        if profile.health_concerns:
            parts.append(f"\n健康关注点：{'、'.join(profile.health_concerns)}")

        if profile.lifestyle:
            parts.append(f"\n生活方式：")
            if "smoking" in profile.lifestyle:
                parts.append(f"  吸烟：{'是' if profile.lifestyle['smoking'] else '否'}")
            if "drinking" in profile.lifestyle:
                parts.append(f"  饮酒：{profile.lifestyle['drinking']}")
            if "exercise" in profile.lifestyle:
                parts.append(f"  运动：{profile.lifestyle['exercise']}")

        parts.append(f"\n画像完整度：{profile.completeness:.0%}")

        return "\n".join(parts)


# ---------------- 实现示例 ----------------

class MockProfileAdapter(ProfileAdapter):
    """模拟实现（内存存储）"""

    def __init__(self):
        self._profiles: Dict[str, UserProfile] = {}
        self._init_mock_data()

    def _init_mock_data(self):
        """初始化模拟数据"""
        mock_profile = UserProfile(
            user_id="user_001",
            name="张大爷",
            age=65,
            gender="男",
            phone="138****1234",
            chronic_diseases=["高血压", "高血脂"],
            allergy_history=["青霉素过敏"],
            current_medication=[
                {"name": "降压药", "dosage": "1片", "frequency": "每日1次"}
            ],
            health_concerns=["血压控制", "血脂管理"],
            lifestyle={"smoking": False, "drinking": "偶尔", "exercise": "散步"}
        )
        mock_profile.calculate_completeness()
        self._profiles["user_001"] = mock_profile

    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        return self._profiles.get(user_id)

    def update_profile(self, user_id: str, updates: Dict) -> bool:
        if user_id not in self._profiles:
            return False

        profile = self._profiles[user_id]

        # 更新字段
        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

        profile.update_time = datetime.now()
        profile.calculate_completeness()
        return True

    def create_profile(self, profile: UserProfile) -> bool:
        self._profiles[profile.user_id] = profile
        return True

    def extract_from_dialogue(self, user_id: str, dialogue: List[Dict]) -> Dict:
        """简单规则提取（实际应使用NER模型）"""
        extracted = {}

        for msg in dialogue:
            if msg.get("role") != "user":
                continue

            content = msg.get("content", "")

            # 提取年龄
            import re
            age_match = re.search(r'(\d{2})\s*[岁年]', content)
            if age_match:
                extracted["age"] = int(age_match.group(1))

            # 提取性别
            if "男" in content and "女" not in content:
                extracted["gender"] = "男"
            elif "女" in content and "男" not in content:
                extracted["gender"] = "女"

            # 提取慢性病
            diseases = ["高血压", "糖尿病", "心脏病", "高血脂", "关节炎", "骨质疏松"]
            found_diseases = [d for d in diseases if d in content]
            if found_diseases:
                extracted["chronic_diseases"] = found_diseases

        return extracted


# ---------------- 真实实现示例（使用MySQL）----------------

class MySQLProfileAdapter(ProfileAdapter):
    """
    基于MySQL的实现

    需要安装: pip install pymysql sqlalchemy
    """

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._engine = None

    def _get_engine(self):
        """获取数据库引擎（延迟初始化）"""
        if self._engine is None:
            from sqlalchemy import create_engine
            self._engine = create_engine(self.connection_string)
        return self._engine

    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """查询用户画像"""
        from sqlalchemy import text

        engine = self._get_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM user_profiles WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()

            if not result:
                return None

            return self._row_to_profile(result)

    def update_profile(self, user_id: str, updates: Dict) -> bool:
        """更新画像"""
        from sqlalchemy import text

        # 构建更新SQL
        set_clauses = []
        params = {"user_id": user_id, "update_time": datetime.now()}

        for key, value in updates.items():
            if key in ["chronic_diseases", "allergy_history", "family_history",
                       "current_medication", "health_supplements",
                       "health_concerns", "health_goals", "lifestyle"]:
                # JSON字段
                set_clauses.append(f"{key} = JSON_SET({key}, '$', :{key})")
                params[key] = json.dumps(value)
            else:
                set_clauses.append(f"{key} = :{key}")
                params[key] = value

        if not set_clauses:
            return False

        sql = f"""
        UPDATE user_profiles
        SET {', '.join(set_clauses)}, update_time = :update_time
        WHERE user_id = :user_id
        """

        engine = self._get_engine()
        with engine.connect() as conn:
            conn.execute(text(sql), params)
            conn.commit()

        return True

    def create_profile(self, profile: UserProfile) -> bool:
        """创建画像"""
        from sqlalchemy import text

        sql = """
        INSERT INTO user_profiles
        (user_id, name, age, gender, phone, chronic_diseases, allergy_history,
         family_history, current_medication, health_supplements, health_concerns,
         health_goals, lifestyle, completeness, create_time, update_time)
        VALUES
        (:user_id, :name, :age, :gender, :phone, :chronic_diseases, :allergy_history,
         :family_history, :current_medication, :health_supplements, :health_concerns,
         :health_goals, :lifestyle, :completeness, :create_time, :update_time)
        """

        import json
        params = {
            "user_id": profile.user_id,
            "name": profile.name,
            "age": profile.age,
            "gender": profile.gender,
            "phone": profile.phone,
            "chronic_diseases": json.dumps(profile.chronic_diseases),
            "allergy_history": json.dumps(profile.allergy_history),
            "family_history": json.dumps(profile.family_history),
            "current_medication": json.dumps(profile.current_medication),
            "health_supplements": json.dumps(profile.health_supplements),
            "health_concerns": json.dumps(profile.health_concerns),
            "health_goals": json.dumps(profile.health_goals),
            "lifestyle": json.dumps(profile.lifestyle),
            "completeness": profile.completeness,
            "create_time": profile.create_time,
            "update_time": profile.update_time
        }

        engine = self._get_engine()
        with engine.connect() as conn:
            conn.execute(text(sql), params)
            conn.commit()

        return True

    def extract_from_dialogue(self, user_id: str, dialogue: List[Dict]) -> Dict:
        """从对话中提取（复用Mock实现）"""
        return MockProfileAdapter().extract_from_dialogue(user_id, dialogue)

    def _row_to_profile(self, row) -> UserProfile:
        """数据库行转对象"""
        import json

        return UserProfile(
            user_id=row.user_id,
            name=row.name,
            age=row.age,
            gender=row.gender,
            phone=row.phone,
            chronic_diseases=json.loads(row.chronic_diseases) if row.chronic_diseases else [],
            allergy_history=json.loads(row.allergy_history) if row.allergy_history else [],
            family_history=json.loads(row.family_history) if row.family_history else [],
            current_medication=json.loads(row.current_medication) if row.current_medication else [],
            health_supplements=json.loads(row.health_supplements) if row.health_supplements else [],
            health_concerns=json.loads(row.health_concerns) if row.health_concerns else [],
            health_goals=json.loads(row.health_goals) if row.health_goals else [],
            lifestyle=json.loads(row.lifestyle) if row.lifestyle else {},
            completeness=row.completeness,
            create_time=row.create_time,
            update_time=row.update_time,
            last_inject_time=row.last_inject_time
        )
