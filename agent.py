"""
泰小虎智能健康导购助手 - 核心智能体模块 V2
基于 Prompt 完整文档 V1/V2 实现，修复多轮对话问题

模块清单：
- System Prompt: 全局人设与安全红线
- 意图路由: 健康咨询 | 产品咨询 | 健康知识 | 其他
- 症状分析: 多轮追问 + 紧急识别
- 产品推荐: 基于症状/需求推荐保健品
- 免责声明: 条件触发
- 画像收集: 基本信息 + 健康状况
- 边界处理: 闲聊/投诉/转接
- 购买记录: 复购提醒
"""

import json
import os
import random
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
# LLM 閫傞厤鍣紙鍙€夛級
try:
    from adapters.llm_adapter import llm_adapter
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


# ============================================================
# 数据模型
# ============================================================

class IntentType(Enum):
    """意图类型"""
    HEALTH_CONSULT = "health_consult"    # 健康咨询
    PRODUCT_CONSULT = "product_consult"   # 产品咨询
    KNOWLEDGE_QUERY = "knowledge_query"   # 健康知识
    REPURCHASE = "repurchase"             # 复购
    CUSTOMER_SERVICE = "customer_service" # 客服
    COMPLAINT = "complaint"               # 投诉
    PROFILE_UPDATE = "profile_update"     # 画像更新
    OTHER = "other"                       # 其他


class SessionState(Enum):
    """会话状态"""
    WELCOME = "welcome"                   # 欢迎/意图选择
    PROFILE_COLLECT = "profile_collect"   # 画像收集
    SYMPTOM_ANALYSIS = "symptom_analysis" # 症状分析（多轮）
    PRODUCT_RECOMMEND = "product_recommend"  # 产品推荐
    KNOWLEDGE_QA = "knowledge_qa"         # 健康知识问答
    BOUNDARY = "boundary"                 # 边界处理
    PRODUCT_CONSULT = "product_consult"   # 产品咨询
    REPURCHASE = "repurchase"             # 复购推荐
    TRANSFER_CS = "transfer_cs"           # 转接客服
    EMERGENCY = "emergency"               # 紧急状态
    COMPLAINT = "complaint"               # 投诉处理


class SymptomRound(Enum):
    """症状追问轮次"""
    MAIN_SYMPTOM = 1       # 主要症状
    DURATION_SEVERITY = 2  # 持续时间 + 严重程度
    ACCOMPANY = 3           # 伴随症状
    HISTORY_MEDICATION = 4  # 病史 + 用药


@dataclass
class Message:
    """消息"""
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)
    intent: Optional[IntentType] = None  # 记录消息对应的意图

    def to_dict(self) -> Dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "intent": self.intent.value if self.intent else None
        }


@dataclass
class UserProfile:
    """用户画像"""
    name: str = ""
    age: int = 0
    gender: str = ""
    chronic_diseases: str = ""   # 慢性病史
    allergy_history: str = ""     # 过敏史
    current_medication: str = ""  # 当前用药
    health_concerns: str = ""     # 健康关注点
    completeness: float = 0.0     # 完整度 0-1
    history: List[Dict] = field(default_factory=list)  # 变更历史

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "age": self.age,
            "gender": self.gender,
            "chronic_diseases": self.chronic_diseases,
            "allergy_history": self.allergy_history,
            "current_medication": self.current_medication,
            "health_concerns": self.health_concerns,
            "completeness": self.completeness
        }

    def update_completeness(self):
        fields = [self.age, self.gender, self.chronic_diseases,
                  self.current_medication, self.health_concerns]
        filled = sum(1 for f in fields if f)
        self.completeness = filled / len(fields)

    def update_field(self, field_name: str, value: str, reason: str = ""):
        """更新字段并记录历史"""
        old_value = getattr(self, field_name, "")
        if old_value != value:
            self.history.append({
                "field": field_name,
                "old": old_value,
                "new": value,
                "time": datetime.now().isoformat(),
                "reason": reason
            })
            setattr(self, field_name, value)


@dataclass
class PurchaseRecord:
    """购买记录（模拟）"""
    product_name: str
    purchase_date: str
    quantity: int
    duration_months: int = 1  # 可用月数


# ============================================================
# Prompt 常量
# ============================================================

SYSTEM_PROMPT = """你是「泰小虎」，一位专业、温和、耐心、贴心的健康顾问。你的名字叫泰小虎，你可以用"我"或"泰小虎"自称。

你的服务对象是45-70岁的中老年用户。他们可能不太熟悉互联网操作，可能对健康问题感到焦虑和不安，需要你用最简单、最温暖的方式为他们提供帮助。

# 核心能力
1. 健康评估：通过对话了解用户的身体状况，提供初步的健康方向性建议
2. 症状自查：帮助用户梳理症状信息，提供可能的健康方向参考
3. 保健品推荐：根据用户健康状况和需求，推荐合适的保健产品
4. 健康知识科普：用通俗易懂的语言解答健康相关问题

# 能力边界声明（非常重要）
1. 你是健康顾问，不是医生。你提供的是健康方向性建议，不是医学诊断
2. 你不能给出具体的疾病诊断结论
3. 你不能开具处方或推荐具体的处方药物
4. 你不能替代专业医疗机构的检查和治疗
5. 当用户描述的症状可能涉及严重疾病时，你必须立即建议用户就医
6. 你推荐的是保健产品，不是治疗药物，不能宣称产品具有治疗功效

# 输出规范
1. 字数限制：每次回复不超过200个汉字
2. 语言要求：使用简单易懂的日常用语，避免使用专业医学术语
3. 格式要求：使用短句，每句话不超过25个字。适当使用分段
4. 称呼规范：称呼用户为"您"，保持尊重和亲切
5. 标点规范：使用中文标点符号

# 安全红线（绝对不可违反）
1. 给出具体的疾病诊断（如"您得了XX病"）
2. 推荐处方药物或替代医生的治疗方案
3. 对紧急症状（如胸痛、呼吸困难、突然昏迷等）给出非就医建议
4. 宣称保健品可以治疗或治愈疾病
5. 贬低正规医疗或鼓励用户放弃就医
6. 收集用户的隐私敏感信息（如身份证号、银行卡号等）
7. 对用户的健康焦虑进行恐吓或夸大

# 语气风格
像一位关心长辈健康的晚辈：温和、耐心、亲切、专业但不生硬、鼓励性。"""

DISCLAIMER_TEXT = "温馨提示：我的建议仅供参考，不能代替医生的专业诊断。如果身体不适，请及时到正规医院就诊。"

EMERGENCY_SYMPTOMS = [
    "胸痛", "胸闷", "胸口痛", "喘不上气", "呼吸困难", "剧烈头痛", "意识模糊", "昏迷",
    "大量出血", "严重外伤", "高热不退", "心跳加速", "半身麻木",
    "说话不清楚", "突然视力模糊", "剧烈腹痛", "中风", "心脏病"
]

EMERGENCY_RESPONSE = "您说的这个情况需要马上重视！请您立刻拨打120急救电话，或者马上让家人送您去医院。身体健康是最重要的，千万别耽误！"

# 意图引导话术
INTENT_GUIDES = {
    IntentType.HEALTH_CONSULT: "您好！请问今天想咨询什么健康问题呢？比如哪里不舒服、想了解什么症状？",
    IntentType.PRODUCT_CONSULT: "欢迎了解健康产品！请问您想为哪方面的健康需求选购产品呢？",
    IntentType.KNOWLEDGE_QUERY: "想学习健康知识吗？请问您对什么健康话题感兴趣？",
    IntentType.REPURCHASE: "您好！请问是想复购之前的产品吗？",
    IntentType.CUSTOMER_SERVICE: "好的，我帮您转接人工客服，请稍等~",
    IntentType.COMPLAINT: "非常抱歉给您带来不好的体验。我已经记录下来了，会尽快处理。",
    IntentType.OTHER: "请问有什么可以帮您的？"
}

# 症状追问话术
SYMPTOM_QUESTIONS = {
    SymptomRound.MAIN_SYMPTOM: "您别着急，咱们慢慢说。您能告诉我哪里不舒服吗？",
    SymptomRound.DURATION_SEVERITY: "这种情况多久了？如果1到10分，您觉得有多难受？",
    SymptomRound.ACCOMPANY: "除了这个，还有其他不舒服的地方吗？",
    SymptomRound.HISTORY_MEDICATION: "您以前有过类似的情况吗？目前在吃什么药或保健品吗？"
}

def _format_symptom_question(round_type: 'SymptomRound', symptom: str = "") -> str:
    """格式化症状追问，包含检测到的症状"""
    q = SYMPTOM_QUESTIONS[round_type]
    if symptom and round_type == SymptomRound.ACCOMPANY:
        return f"关于您说的【{symptom}】，这种情况大概持续多久了？如果1到10分，您觉得有多难受？"
    if symptom and round_type == SymptomRound.HISTORY_MEDICATION:
        return f"除了【{symptom}】，还有其他不舒服的地方吗？"
    return q

# 模拟产品库
PRODUCT_DATABASE = [
    {
        "name": "安美来胶原玻尿酸燕窝酸固体饮料",
        "category": "美容养颜",
        "efficacy": "富含鳕鱼胶原蛋白肽、玻尿酸、燕窝酸和麦角硫因，有助于抗皱美白、止脱发、抗衰老",
        "audience": "18岁以上成年男女，关注皮肤美容、抗衰老的人群",
        "usage": "每天1袋，用100ml凉水或温水冲调，推荐睡前1-2小时饮用",
        "symptoms": [
            "皮肤",
            "皱纹",
            "美白",
            "脱发",
            "头发",
            "美容",
            "养颜",
            "胶原蛋白",
            "玻尿酸",
            "燕窝"
        ],
        "contraindications": [
            "孕妇",
            "哺乳期"
        ],
        "productId": "2018137912588005376",
        "shopId": "1980510179516006400",
        "keywords": [
            "安美来",
            "燕窝"
        ]
    },
    {
        "name": "智忆高复合磷脂酰丝氨酸压片糖果",
        "category": "脑部健康",
        "efficacy": "含磷脂酰丝氨酸(PS)、DHA、燕窝酸，显著提高记忆力、学习能力和学习成绩",
        "audience": "3岁以上儿童、青少年、学生、中老年人，需要提高记忆力和学习能力的人群",
        "usage": "每天3-4片，咀嚼食用",
        "symptoms": [
            "记忆",
            "学习",
            "脑力",
            "注意力",
            "学生",
            "考试",
            "聪明",
            "DHA",
            "磷脂",
            "大脑"
        ],
        "contraindications": [],
        "productId": "2018137364916760576",
        "shopId": "1980510179516006400",
        "keywords": [
            "智忆高"
        ]
    },
    {
        "name": "泰美畅超级益生菌压片糖果",
        "category": "肠道健康",
        "efficacy": "含7大专利菌株+控释定植技术，99%活菌稳植，润肠通便、阻脂排脂、调节肠道菌群",
        "audience": "3岁以上人群，便秘、肠胃不适、想减肥瘦身的人群",
        "usage": "常温水吞服，不要嚼食，每天1-2次，每次1-2片",
        "symptoms": [
            "便秘",
            "肠胃",
            "消化",
            "肠道",
            "益生菌",
            "减肥",
            "瘦身",
            "排毒",
            "胀气",
            "腹泻"
        ],
        "contraindications": [],
        "productId": "2005554146321526784",
        "shopId": "1980510179516006400",
        "keywords": [
            "泰美畅"
        ]
    },
    {
        "name": "膳纤7星营养餐",
        "category": "营养代餐",
        "efficacy": "7星级体重管理特膳食品，纠正易胖体质、促进脂肪消耗、减少热量摄入，同时保证营养均衡",
        "audience": "想要健康减脂、控制体重的人群",
        "usage": "每天代替1-2餐，用适量温水冲调食用",
        "symptoms": [
            "减肥",
            "减脂",
            "体重",
            "代餐",
            "营养",
            "饱腹",
            "瘦身",
            "肥胖",
            "控制体重"
        ],
        "contraindications": [],
        "productId": "2042054585543958528",
        "shopId": "2029392044486082560",
        "keywords": [
            "膳纤",
            "七星",
            "7星"
        ]
    },
    {
        "name": "保元津",
        "category": "滋补养生",
        "efficacy": "增加骨密度、改善睡眠、抗衰补肾、强免疫，从根源解决中老年人骨质疏松、腰酸腿软、失眠等问题",
        "audience": "40岁以上中老年男女，骨质疏松、睡眠差、体虚乏力、更年期不适人群",
        "usage": "每日2次，每次2片，早、晚饭后半小时温水送服",
        "symptoms": [
            "骨质疏松",
            "骨密度",
            "睡眠",
            "失眠",
            "肾虚",
            "腰酸",
            "腿软",
            "更年期",
            "免疫力",
            "衰老"
        ],
        "contraindications": [
            "少年儿童",
            "孕妇",
            "哺乳期",
            "妇科肿瘤患者"
        ],
        "productId": "",
        "shopId": "",
        "keywords": [
            "保元津"
        ]
    },
    {
        "name": "泰力脂",
        "category": "心脑血管",
        "efficacy": "调节血脂、保肝护肝，含红曲提取物(天然洛伐他汀)、水飞蓟素、吡啶甲酸铬",
        "audience": "高血脂、脂肪肝、高血压、糖尿病合并高血脂人群",
        "usage": "初始每日2次、每次2片；达标后每日1次、每次2片，餐后服用",
        "symptoms": [
            "血脂",
            "胆固醇",
            "脂肪肝",
            "高血压",
            "心血管",
            "降脂",
            "保肝",
            "护肝"
        ],
        "contraindications": [],
        "productId": "",
        "shopId": "",
        "keywords": [
            "泰力脂",
            "降脂"
        ]
    },
    {
        "name": "泰尔血素",
        "category": "补血养血",
        "efficacy": "铁+叶酸+维C黄金三角配方，改善营养性贫血，科学补铁补血养血",
        "audience": "营养性贫血人群、气血不足女性、备孕/孕妇/产妇、儿童青少年、中老年人",
        "usage": "每日1次，每次2片，餐时或餐后温水吞服",
        "symptoms": [
            "贫血",
            "补血",
            "缺铁",
            "头晕",
            "乏力",
            "面色苍白",
            "手脚冰凉",
            "气血"
        ],
        "contraindications": [],
        "productId": "",
        "shopId": "",
        "keywords": [
            "泰尔血素",
            "补血"
        ]
    },
    {
        "name": "泰吉眠沙棘茶氨酸",
        "category": "睡眠健康",
        "efficacy": "中科院专利成果，含沙棘萃取5-羟色胺，30分钟入睡，延长深睡，改善失眠，无副作用无依赖",
        "audience": "失眠、睡眠质量差的人群，3岁以上全龄适用",
        "usage": "每天1次，每次2片，睡前30分钟嚼食",
        "symptoms": [
            "失眠",
            "睡眠",
            "睡不着",
            "睡眠质量",
            "深睡",
            "多梦",
            "易醒",
            "焦虑"
        ],
        "contraindications": [
            "3岁以下婴幼儿"
        ],
        "productId": "",
        "shopId": "",
        "keywords": [
            "泰吉眠",
            "睡眠"
        ]
    }
],
        "name": "钙片+维生素D3",
        "category": "骨骼健康",
        "efficacy": "补充钙质和维生素D，帮助骨骼强健",
        "audience": "中老年人、骨质疏松风险人群",
        "usage": "每日1次，每次1片，随餐服用",
        "symptoms": ["骨质疏松", "骨头", "关节", "腰酸", "腿抽筋", "钙", "骨头疼", "缺钙", "抽筋"],
        "contraindications": []
    },
    {
        "name": "益生菌粉",
        "category": "肠道健康",
        "efficacy": "调节肠道菌群平衡，促进消化吸收",
        "audience": "消化不良、肠胃功能较弱的人群",
        "usage": "每日1次，每次1袋，温水冲服",
        "symptoms": ["肠胃", "消化", "便秘", "腹泻", "肚子", "胃", "肠道", "胃胀", "胃痛", "益生菌"],
        "contraindications": []
    },
    {
        "name": "复合维生素B族",
        "category": "营养补充",
        "efficacy": "补充多种B族维生素，缓解疲劳，维持神经健康，对缓解头痛有一定帮助",
        "audience": "容易疲劳、睡眠不佳、压力大、经常头痛的人群",
        "usage": "每日1次，每次1片，饭后服用",
        "symptoms": ["疲劳", "失眠", "睡眠", "神经", "压力", "没精神", "头痛", "偏头疼", "头疼", "维生素B"],
        "contraindications": []
    },
    {
        "name": "氨糖软骨素",
        "category": "关节养护",
        "efficacy": "修复关节软骨，缓解关节不适",
        "audience": "关节不适、运动人群、中老年人",
        "usage": "每日2次，每次2粒，饭后服用",
        "symptoms": ["关节", "膝盖", "腰", "骨关节", "软骨", "走路疼", "关节痛", "腰疼", "腿疼"],
        "contraindications": []
    },
    {
        "name": "护肝片",
        "category": "肝脏养护",
        "efficacy": "保护肝脏细胞，促进肝脏解毒功能",
        "audience": "长期服药、饮酒、熬夜的人群",
        "usage": "每日2次，每次1片，饭后服用",
        "symptoms": ["肝", "熬夜", "喝酒", "脂肪肝", "肝脏", "肝火旺"],
        "contraindications": []
    },
    {
        "name": "叶黄素软胶囊",
        "category": "眼部健康",
        "efficacy": "补充叶黄素，保护视力，缓解眼疲劳",
        "audience": "长时间用眼、视力下降的中老年人群",
        "usage": "每日1次，每次1粒，饭后服用",
        "symptoms": ["眼睛", "视力", "看不清", "眼干", "眼疲劳", "模糊", "眼花"],
        "contraindications": []
    },
    {
        "name": "大豆异黄酮",
        "category": "女性健康",
        "efficacy": "调节内分泌，缓解更年期不适",
        "audience": "更年期女性、内分泌失调人群",
        "usage": "每日1次，每次1粒，饭后服用",
        "symptoms": ["更年期", "潮热", "出汗", "女性", "内分泌", "月经不调", "盗汗"],
        "contraindications": []
    },
    {
        "name": "褪黑素片",
        "category": "睡眠健康",
        "efficacy": "帮助调节睡眠节律，改善睡眠质量",
        "audience": "失眠、睡眠质量差、倒时差的人群",
        "usage": "睡前30分钟服用1片",
        "symptoms": ["失眠", "睡不着", "睡眠", "睡不好", "多梦", "易醒", "褪黑素"],
        "contraindications": []
    },
    {
        "name": "辅酶Q10",
        "category": "心脏养护",
        "efficacy": "为心肌提供能量，保护心脏健康",
        "audience": "关注心脏健康、容易心慌气短的人群",
        "usage": "每日1次，每次1粒，饭后服用",
        "symptoms": ["心慌", "气短", "心脏", "胸闷", "心悸", "辅酶"],
        "contraindications": []
    }
]

# 模拟健康知识库
KNOWLEDGE_BASE = {
    "血压": "正常血压范围是收缩压90-140mmHg，舒张压60-90mmHg。建议每天定时测量血压，保持低盐饮食，适量运动。",
    "血糖": "空腹血糖正常值是3.9-6.1mmol/L。控制糖分摄入，多吃粗粮蔬菜，定期检测血糖很重要。",
    "睡眠": "中老年人建议每天睡6-8小时。睡前避免饮茶和咖啡，保持规律作息，适当散步有助睡眠。",
    "失眠": "失眠可能与情绪、生活习惯、年龄等因素有关。建议您睡前避免饮茶和咖啡，保持规律作息，适当散步有助于睡眠。",
    "饮食": "建议每天摄入12种以上食物，多吃蔬菜水果、粗粮杂粮，少吃油腻和高盐食物。",
    "运动": "中老年人适合散步、太极、游泳等温和运动。每天运动30分钟，每周至少5天。",
    "骨质疏松": "50岁以上人群要注意补钙和维生素D。多喝牛奶、豆制品，适当晒太阳。",
    "关节": "保护关节要注意控制体重，避免长时间保持同一姿势。适当做关节活动操。",
    "便秘": "每天喝足够的水，多吃富含膳食纤维的食物，如蔬菜、水果、粗粮。养成定时排便习惯。",
    "免疫力": "保持良好作息、均衡饮食、适度运动、心情愉快，都有助于提高免疫力。",
    "眼睛": "用眼40分钟要休息10分钟。多吃胡萝卜、菠菜等富含维生素A的食物。",
    "心脏": "保护心脏要戒烟限酒、控制体重、规律运动、保持心情愉快。定期检查心电图。",
    "血脂": "血脂偏高要少吃动物内脏和油炸食品，多吃深海鱼和蔬菜。定期检查血脂指标。",
    "维生素C": "维生素C有助于增强免疫力，促进胶原蛋白合成，保护血管健康。多吃新鲜水果蔬菜。",
    "鱼油": "鱼油富含Omega-3脂肪酸，其中的DHA和EPA对心脑血管健康有益。DHA主要支持大脑和视力，EPA主要支持心血管健康。",
    "DHA": "DHA是大脑和视网膜的重要成分，有助于维持认知功能和视力健康。",
    "EPA": "EPA有助于降低血脂、抗炎，对心血管健康特别重要。",
    "益生菌": "益生菌有助于维持肠道菌群平衡，改善消化功能，增强免疫力。",
    "钙片": "钙是骨骼和牙齿的主要成分，中老年人容易缺钙，需要适当补充。",
    "褪黑素": "褪黑素是调节睡眠节律的激素，有助于改善睡眠质量，但不是安眠药。"
}


# ============================================================
# 核心智能体
# ============================================================

class TaiXiaoHuAgent:
    """泰小虎智能健康导购助手 V2"""

    def __init__(self):
        self.name = "泰小虎"
        self.messages: List[Message] = []
        self.state: SessionState = SessionState.WELCOME
        self.current_intent: Optional[IntentType] = None
        self.previous_intent: Optional[IntentType] = None  # 记录上一个意图
        self.symptom_round: int = 0
        self.symptom_data: Dict[str, str] = {}
        self.user_profile = UserProfile()
        self.purchase_history: List[PurchaseRecord] = []
        self.intent_deny_count: int = 0
        self.max_messages: int = 100
        self.last_recommended: List[str] = []
        self.pending_question: Optional[str] = None  # 待回答的问题
        self.refusal_count: int = 0  # 用户拒绝次数
        self.context_summary: str = ""  # 对话上下文摘要

        # 初始化模拟购买记录
        self._init_sample_purchase_history()

    def _init_sample_purchase_history(self):
        """初始化示例购买记录"""
        self.purchase_history = [
            PurchaseRecord("鱼油软胶囊", "2026-03-15", 2, 2),
            PurchaseRecord("钙片+维生素D3", "2026-04-01", 1, 3),
        ]

    # --------------------------------------------------------
    # 主入口
    # --------------------------------------------------------

    
    def _call_llm(self, user_message: str, system_prompt: str = None) -> Optional[str]:
        """璋冪敤鐪熷疄 LLM 鑾峰彇鍥炲"""
        if not LLM_AVAILABLE:
            return None

        llm_adapter.reload_config()
        if not llm_adapter.is_enabled:
            return None

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            messages.append({"role": "system", "content": SYSTEM_PROMPT})

        # 娣诲姞鏈€杩戠殑瀵硅瘽鍘嗗彶
        recent = self.messages[-20:] if len(self.messages) > 20 else self.messages
        for msg in recent:
            messages.append({"role": msg.role, "content": msg.content})

        # 娣诲姞褰撳墠鐢ㄦ埛娑堟伅
        messages.append({"role": "user", "content": user_message})

        result = llm_adapter.chat(messages)
        if result.success:
            return result.content
        else:
            print(f"[LLM Error] {result.error}")
            if llm_adapter.config.get("fallback_to_mock", True):
                return None
            return f"鎶辨瓑锛屾垜鐜板湪閬囧埌浜嗕竴浜涙妧鏈棶棰橈細{result.error}"

    def process_message(self, user_input: str, intent: Optional[str] = None) -> Dict:
        """
        处理用户消息的主入口 - V2增强版
        """
        # 保存用户消息（带意图标记）
        msg = Message(role="user", content=user_input, intent=self.current_intent)
        self.messages.append(msg)

        # 1. 紧急症状检测（最高优先级）
        emergency = self._check_emergency(user_input)
        if emergency:
            self.state = SessionState.EMERGENCY
            resp = self._build_response(EMERGENCY_RESPONSE, need_disclaimer=False)
            return resp

        # 2. 检测意图切换
        intent_switched = self._detect_intent_switch(user_input)
        if intent_switched:
            self.previous_intent = self.current_intent
            self.current_intent = intent_switched
            self.refusal_count = 0  # 重置拒绝计数
            return self._route_by_intent(user_input, is_switch=True)

        # 3. 客服转接检测
        if self._should_transfer_cs(user_input):
            resp = self._build_response(
                "您的问题我已经记录下来了。为了更好地帮您解决，我帮您转接到人工客服，请稍等~",
                state=SessionState.TRANSFER_CS
            )
            return resp

        # 4. 意图确认/切换（外部传入）
        if intent:
            new_intent = IntentType(intent)
            if new_intent != self.current_intent:
                self.previous_intent = self.current_intent
                self.current_intent = new_intent
            self.intent_deny_count = 0
            return self._route_by_intent(user_input)

        # 5. 处理用户拒绝/否认
        refusal_type = self._check_refusal(user_input)
        if refusal_type:
            return self._handle_refusal(user_input, refusal_type)

        # 6. 根据当前状态处理
        response = self._handle_by_state(user_input)

        return response

    # --------------------------------------------------------
    # 意图检测与切换
    # --------------------------------------------------------

    def _detect_intent_switch(self, user_input: str) -> Optional[IntentType]:
        """检测意图切换 - V2增强版"""
        # 紧急症状优先
        if self._check_emergency(user_input):
            return IntentType.HEALTH_CONSULT

        # 意图切换关键词
        switch_patterns = {
            IntentType.PRODUCT_CONSULT: [
                "对了.*产品", "对了.*怎么样", "对了.*多少钱", "对了.*推荐",
                "那.*产品", "那.*推荐", "那.*钙片", "那.*鱼油", "那.*维生素",
                "给我推荐", "有什么产品", "买什么", "哪个好",
                "多少钱", "价格", "怎么买", "有.*吗",
                "我想买", "给我.*买", "一起发过来", "还想买"
            ],
            IntentType.HEALTH_CONSULT: [
                "其实.*", "对了.*不舒服", "对了.*疼", "对了.*痛",
                "我.*症状", "我.*不舒服", "我.*疼", "我.*痛", "我.*难受",
                "是不是.*病", "是不是.*问题", "怎么回事",
                "你先帮我看看", "帮我看看", "还是疼", "还是.*不舒服"
            ],
            IntentType.KNOWLEDGE_QUERY: [
                "为什么", "什么原因", "怎么回事", "有什么作用",
                "有什么好处", "有什么用", "是什么", "有什么区别",
                "想先了解", "了解一下", "什么造成的"
            ],
            IntentType.COMPLAINT: [
                "投诉", "差评", "退货", "退款", "质量.*问题", "发货.*慢",
                "APP.*闪退", "闪退", "不好用", "有问题"
            ],
            IntentType.CUSTOMER_SERVICE: [
                "找人工", "人工客服", "转人工", "客服", "人工"
            ],
            IntentType.REPURCHASE: [
                "复购", "再买", "还要.*", "还要买", "之前.*买", "上次.*买",
                "吃完了", "用完了", "快用完"
            ]
        }

        # 检查切换模式
        for intent_type, patterns in switch_patterns.items():
            for pattern in patterns:
                if re.search(pattern, user_input):
                    # 如果检测到不同意图，返回新意图
                    if intent_type != self.current_intent:
                        return intent_type

        # 检查当前意图是否仍然有效
        if self.current_intent:
            current_valid = self._validate_current_intent(user_input)
            if not current_valid:
                # 当前意图不再有效，尝试检测新意图
                new_intent = self._auto_detect_intent(user_input)
                if new_intent and new_intent != self.current_intent:
                    return new_intent

        return None

    def _validate_current_intent(self, user_input: str) -> bool:
        """验证当前意图是否仍然有效"""
        if not self.current_intent:
            return False

        # 根据当前意图检查用户输入是否相关
        if self.current_intent == IntentType.HEALTH_CONSULT:
            health_keywords = ["疼", "痛", "不舒服", "症状", "病", "难受", "感觉"]
            return any(kw in user_input for kw in health_keywords)

        elif self.current_intent == IntentType.PRODUCT_CONSULT:
            product_keywords = ["产品", "买", "多少钱", "价格", "推荐", "功效"]
            return any(kw in user_input for kw in product_keywords)

        elif self.current_intent == IntentType.KNOWLEDGE_QUERY:
            knowledge_keywords = ["为什么", "是什么", "怎么", "知识", "作用"]
            return any(kw in user_input for kw in knowledge_keywords)

        return True

    # --------------------------------------------------------
    # 意图路由
    # --------------------------------------------------------

    def _route_by_intent(self, user_input: str, is_switch: bool = False) -> Dict:
        """根据意图路由到对应处理模块 - V3：切换后直接处理用户内容"""
        if self.current_intent == IntentType.HEALTH_CONSULT:
            self.state = SessionState.SYMPTOM_ANALYSIS
            self.symptom_round = 0
            self.symptom_data = {}
            # 直接处理用户输入，不再只输出引导话术
            return self._handle_symptom_analysis(user_input)

        elif self.current_intent == IntentType.PRODUCT_CONSULT:
            self.state = SessionState.PRODUCT_CONSULT
            # 直接处理产品咨询
            return self._handle_product_consult(user_input)

        elif self.current_intent == IntentType.KNOWLEDGE_QUERY:
            self.state = SessionState.KNOWLEDGE_QA
            return self._handle_knowledge_qa(user_input)

        elif self.current_intent == IntentType.REPURCHASE:
            self.state = SessionState.REPURCHASE
            return self._handle_repurchase(user_input)

        elif self.current_intent == IntentType.COMPLAINT:
            return self._handle_complaint(user_input)

        elif self.current_intent == IntentType.CUSTOMER_SERVICE:
            return self._build_response(
                "好的，我帮您转接人工客服，请稍等~",
                state=SessionState.TRANSFER_CS
            )

        elif self.current_intent == IntentType.PROFILE_UPDATE:
            self.state = SessionState.PROFILE_COLLECT
            return self._handle_profile_collect(user_input)

        else:
            self.state = SessionState.BOUNDARY
            return self._handle_boundary(user_input)

    # --------------------------------------------------------
    # 状态机处理
    # --------------------------------------------------------

    def _handle_by_state(self, user_input: str) -> Dict:
        """根据当前会话状态处理消息 - V2增强版"""
        if self.state == SessionState.WELCOME:
            return self._handle_welcome(user_input)

        elif self.state == SessionState.PROFILE_COLLECT:
            return self._handle_profile_collect(user_input)

        elif self.state == SessionState.SYMPTOM_ANALYSIS:
            return self._handle_symptom_analysis(user_input)

        elif self.state == SessionState.PRODUCT_RECOMMEND:
            return self._handle_product_recommend(user_input)

        elif self.state == SessionState.PRODUCT_CONSULT:
            return self._handle_product_consult(user_input)

        elif self.state == SessionState.KNOWLEDGE_QA:
            return self._handle_knowledge_qa(user_input)

        elif self.state == SessionState.BOUNDARY:
            return self._handle_boundary(user_input)

        elif self.state == SessionState.REPURCHASE:
            return self._handle_repurchase(user_input)

        elif self.state == SessionState.COMPLAINT:
            # 投诉状态：用户继续说话视为投诉继续
            complaint_keywords = ["发货", "包装", "产品", "质量", "收到", "订单", "快递", "钙片", "维生素"]
            if any(kw in user_input for kw in complaint_keywords):
                return self._handle_complaint(user_input)
            # 用户转换话题：视为投诉已处理，回到欢迎
            self.state = SessionState.WELCOME
            if hasattr(self, 'complaint_content'):
                del self.complaint_content
            return self._handle_welcome(user_input)

        elif self.state == SessionState.EMERGENCY:
            # 紧急状态下，继续强调就医
            return self._build_response(
                "请您务必重视，尽快拨打120或前往医院。如果情况严重，千万不要拖延！",
                need_disclaimer=False
            )

        else:
            return self._handle_welcome(user_input)

    # --------------------------------------------------------
    # 拒绝/否认处理
    # --------------------------------------------------------

    def _check_refusal(self, user_input: str) -> Optional[str]:
        """检查用户是否拒绝或否认"""
        refusal_patterns = {
            "deny_info": ["不想说", "不想回答", "不想告诉", "保密", "隐私", "不说", "不告诉"],
            "deny_suggestion": ["不想吃", "不想买", "不想用", "不用了", "算了", "不要", "太麻烦"],
            "deny_intent": ["不是", "不对", "错了", "没.*意思", "随便问问", "就问问"],
            "deny_emergency": ["没事", "老毛病", "不用管", "没关系", "不要紧"],
            "confirm_end": ["好的", "知道了", "明白", "谢谢", "不客气"]
        }

        for refusal_type, patterns in refusal_patterns.items():
            for pattern in patterns:
                if pattern in user_input or re.search(pattern, user_input):
                    return refusal_type

        return None

    def _handle_refusal(self, user_input: str, refusal_type: str) -> Dict:
        """处理用户拒绝/否认"""
        self.refusal_count += 1

        if refusal_type == "deny_info":
            # 用户拒绝提供信息
            if self.refusal_count >= 2:
                # 多次拒绝，给出通用建议
                return self._build_response(
                    "好的，我理解。那基于一般情况，我建议您可以从日常保健开始。"
                    "比如保持规律作息、均衡饮食、适度运动。"
                    "如果您有具体的健康问题，随时可以问我~"
                )
            else:
                # 换角度询问
                return self._build_response(
                    "没关系，那您能告诉我主要想改善什么健康问题吗？"
                    "比如睡眠、关节、心脑血管等方面？"
                )

        elif refusal_type == "deny_suggestion":
            # 用户拒绝建议
            if self.refusal_count >= 2:
                return self._build_response(
                    "好的，我理解您的想法。那您可以再考虑考虑，"
                    "或者告诉我您更倾向于哪种方式，我帮您参谋参谋~"
                )
            else:
                return self._build_response(
                    "那您平时有什么保健习惯吗？或者您更倾向于什么样的调理方式？"
                )

        elif refusal_type == "deny_intent":
            # 用户否认意图（"不是"、"算了"、"就问问"）
            if any(kw in user_input for kw in ["算了", "不买了", "就问问", "随便问问"]):
                # 否认购买意向
                return self._build_response(
                    "好的，没问题！如果以后有需要，随时来找我。"
                    "祝您身体健康，生活愉快！"
                )
            return self._build_response(
                "不好意思，我可能理解错了。那您主要是想咨询什么呢？"
                "是健康方面的问题，还是想了解产品？"
            )

        elif refusal_type == "deny_emergency":
            # 用户否认紧急症状（需要坚持安全原则）
            if "胸痛" in self._get_conversation_context() or "胸闷" in self._get_conversation_context():
                return self._build_response(
                    "我理解您可能觉得是老毛病，但胸痛真的不能轻视。"
                    "为了您的安全，建议您还是去医院检查一下，排除风险。"
                    "如果症状加重，请立即就医！"
                )
            return self._build_response(
                "好的，我了解了。不过如果症状有变化或加重，还是建议您及时就医检查。"
            )

        elif refusal_type == "confirm_end":
            # 用户确认结束
            self.state = SessionState.WELCOME
            return self._build_response(
                "不客气！很高兴能帮到您~如果还有其他问题，随时找我。祝您身体健康！"
            )

        return self._handle_by_state(user_input)

    # --------------------------------------------------------
    # 欢迎态
    # --------------------------------------------------------

    def _handle_welcome(self, user_input: str) -> Dict:
        """处理欢迎/初始状态 - V2增强版"""
        # 安全检查：检测诊断诱导
        if self._check_diagnosis_inducement(user_input):
            resp = "我理解您很担心，但我不能给出疾病诊断。只有医生经过检查才能确定病因。\n\n"
            resp += "建议您：\n"
            resp += "• 如果症状严重或持续，请尽快就医\n"
            resp += "• 可以描述具体症状，我帮您分析可能的方向\n"
            resp += f"\n{DISCLAIMER_TEXT}"
            return self._build_response(resp)

        # 安全检查：检测处方药诱导
        if self._check_prescription_inducement(user_input):
            resp = "我理解您的需求，但我不能开具处方或推荐具体药物。用药需要在医生指导下进行。\n\n"
            resp += "建议您：\n"
            resp += "• 到医院就诊，由医生根据您的情况开具处方\n"
            resp += "• 我可以推荐一些保健产品作为辅助调理\n"
            resp += f"\n{DISCLAIMER_TEXT}"
            return self._build_response(resp)

        # 简单关键词匹配
        if any(kw in user_input for kw in ["你好", "在吗", "您好", "嗨"]):
            resp = "您好！我是泰小虎，您的健康顾问~\n我可以帮您：\n• 解答健康问题\n• 推荐合适的保健品\n• 了解健康知识\n\n请问您今天想咨询什么呢？"
            return self._build_response(resp)

        # 检查是否是追问
        follow_up_keywords = ["功效", "效果", "作用", "成分", "怎么吃", "用法", "服用", "多少钱", "价格", "有用吗"]
        if any(kw in user_input for kw in follow_up_keywords):
            if self.last_recommended:
                return self._handle_product_follow_up(user_input)
            else:
                self.current_intent = IntentType.PRODUCT_CONSULT
                return self._route_by_intent(user_input)

        # 检测画像收集场景（纯数值/性别/症状输入）
        if self._is_profile_input(user_input):
            self.state = SessionState.PROFILE_COLLECT
            return self._handle_profile_collect(user_input)

        # 尝试自动识别意图
        detected = self._auto_detect_intent(user_input)
        if detected:
            self.current_intent = detected
            return self._route_by_intent(user_input)

        # 模糊意图：引导用户说明需求
        vague_keywords = ["我想买", "推荐", "有没有", "给我", "帮我"]
        if any(kw in user_input for kw in vague_keywords):
            self.current_intent = IntentType.PRODUCT_CONSULT
            return self._handle_product_consult(user_input)

        return self._build_response(
            "您好！我是泰小虎，您的健康顾问~\n我可以帮您解答健康问题、推荐保健品、了解健康知识。\n请问您今天想咨询什么呢？"
        )

    def _is_profile_input(self, text: str) -> bool:
        """检测是否是画像收集相关输入（排除纯症状描述）"""
        # 纯年龄数字（2位）
        if re.match(r'^\d{2}\s*$', text.strip()):
            return True
        # 性别词
        if text.strip() in ["男", "女", "男性", "女性"]:
            return True
        # 健康状况词（不是症状，是已确诊的疾病）
        health_status = ["高血压", "糖尿病", "骨质疏松", "血糖高", "血脂高", "有.*病", "确诊"]
        if any(re.search(kw, text) for kw in health_status):
            return True
        # 画像更新相关词
        profile_keywords = ["更新", "资料", "信息", "岁", "年纪", "年龄"]
        if any(kw in text for kw in profile_keywords):
            return True
        return False

    def _check_diagnosis_inducement(self, text: str) -> bool:
        """检测诊断诱导"""
        diagnosis_patterns = [
            "是不是", "是不是得了", "是不是患了", "是不是有",
            "告诉我是什么病", "直接告诉我", "确诊",
            "是不是脑瘤", "是不是癌症", "是不是肿瘤"
        ]
        has_symptom = any(kw in text for kw in ["头疼", "头痛", "恶心", "胸痛", "肚子疼", "难受"])
        has_diagnosis_request = any(kw in text for kw in diagnosis_patterns)
        return has_symptom and has_diagnosis_request

    def _check_prescription_inducement(self, text: str) -> bool:
        """检测处方药诱导"""
        prescription_patterns = [
            "开个", "开药", "药方", "处方",
            "给我开", "给我配药", "吃什么药"
        ]
        return any(kw in text for kw in prescription_patterns)

    def _handle_product_follow_up(self, user_input: str) -> Dict:
        """处理产品追问"""
        products_info = []
        for product in PRODUCT_DATABASE:
            if product['name'] in self.last_recommended:
                products_info.append(product)

        if not products_info:
            self.current_intent = IntentType.PRODUCT_CONSULT
            return self._route_by_intent(user_input)

        if any(kw in user_input for kw in ["功效", "效果", "作用", "有用吗"]):
            resp = "关于刚才推荐的产品：\n\n"
            for p in products_info[:2]:
                resp += f"【{p['name']}】\n"
                resp += f"功效：{p['efficacy']}\n"
                resp += f"适用人群：{p['audience']}\n\n"
            resp += "这些产品都是辅助保健的，不能替代药物治疗哦~"
        elif any(kw in user_input for kw in ["怎么吃", "用法", "服用"]):
            resp = "服用方法如下：\n\n"
            for p in products_info[:2]:
                resp += f"【{p['name']}】\n"
                resp += f"用法：{p['usage']}\n\n"
        elif any(kw in user_input for kw in ["多少钱", "价格"]):
            resp = "关于价格，不同规格和渠道会有差异。建议您：\n"
            resp += "• 点击下方产品卡片查看详情\n"
            resp += "• 或联系客服咨询最新价格\n"
            resp += "• 关注官方活动，经常有优惠哦~"
        else:
            resp = "您问的是刚才推荐的产品吗？\n\n"
            for p in products_info[:2]:
                resp += f"【{p['name']}】\n"
                resp += f"功效：{p['efficacy']}\n"
                resp += f"用法：{p['usage']}\n\n"

        return self._build_response(resp)

    # --------------------------------------------------------
    # 画像收集
    # --------------------------------------------------------

    def _handle_profile_collect(self, user_input: str) -> Dict:
        """处理画像收集 - V3增强版：支持家属画像、画像更新、数值识别"""
        # 检测家属购买场景（优先）
        family_keywords = ["老伴", "老公", "老婆", "妈妈", "爸爸", "母亲", "父亲", "给我.*买"]
        is_for_family = any(re.search(kw, user_input) for kw in family_keywords)
        if is_for_family:
            products = self._match_products(user_input)
            if products:
                resp = "好的，了解您是为家人选购。根据您描述的情况，推荐：\n\n"
                for i, p in enumerate(products[:3], 1):
                    resp += f"{i}.【{p['name']}】\n"
                    resp += f"  功效：{p['efficacy']}\n"
                    resp += f"  适用人群：{p['audience']}\n\n"
                resp += f"{DISCLAIMER_TEXT}"
                self.last_recommended = [p['name'] for p in products[:3]]
                self.state = SessionState.WELCOME
                return self._build_response(resp, need_disclaimer=False)

        # 提取年龄（纯数字也是年龄）
        age_match = re.search(r'(\d{2})\s*[岁年]?', user_input)
        if age_match:
            age = int(age_match.group(1))
            self.user_profile.update_field("age", age, "用户主动提供")

        # 提取性别（男/女/她）
        if "男" in user_input or "先生" in user_input:
            self.user_profile.update_field("gender", "男", "用户主动提供")
        elif "女" in user_input or "女士" in user_input or "她" in user_input:
            self.user_profile.update_field("gender", "女", "用户主动提供")

        # 提取慢性病
        disease_keywords = ["高血压", "糖尿病", "心脏病", "高血脂", "关节炎", "骨质疏松", "痛风", "血糖偏高", "糖尿病前期"]
        diseases = [d for d in disease_keywords if d in user_input]
        if diseases:
            self.user_profile.update_field("chronic_diseases", "、".join(diseases), "用户主动提供")

        # 提取用药
        med_keywords = ["降压药", "降糖药", "胰岛素", "华法林", "抗凝药", "吃药", "服药"]
        meds = [m for m in med_keywords if m in user_input]
        if meds:
            self.user_profile.update_field("current_medication", "、".join(meds), "用户主动提供")

        # 提取健康关注点
        concern_keywords = ["血压", "血糖", "睡眠", "关节", "心脏", "肠胃", "视力", "记忆力", "疲劳", "骨质疏松",
                          "失眠", "头晕", "胃", "腿", "抽筋", "心慌", "胸闷", "头疼", "便秘", "潮热", "盗汗"]
        concerns = [kw for kw in concern_keywords if kw in user_input]
        if concerns:
            self.user_profile.update_field("health_concerns", "、".join(concerns), "用户主动提供")

        self.user_profile.update_completeness()

        # 画像更新场景
        if "更新" in user_input or "资料" in user_input or "确诊" in user_input:
            resp = "好的，我已经记录了您的信息。"
            if self.user_profile.chronic_diseases:
                resp += f"\n\n您目前的健康状况：{self.user_profile.chronic_diseases}"
                resp += "\n\n请注意，以下保健品需要谨慎选择或咨询医生后再服用。请问您想了解哪方面的保健品？"
            else:
                resp += "\n\n请问您想咨询什么健康问题呢？"
            self.state = SessionState.WELCOME
            return self._build_response(resp)

        # 画像已完整，或者只有纯数据输入（58/女等），直接推荐或询问
        if self.user_profile.completeness >= 0.5:
            self.state = SessionState.WELCOME
            # 如果有关注点，直接推荐
            if self.user_profile.health_concerns:
                products = self._match_products(self.user_profile.health_concerns)
                if products:
                    resp = "好的，我了解了您的情况。给您推荐：\n\n"
                    for i, p in enumerate(products[:3], 1):
                        resp += f"{i}.【{p['name']}】 - {p['efficacy']}\n"
                    resp += f"\n{DISCLAIMER_TEXT}"
                    self.last_recommended = [p['name'] for p in products[:3]]
                    return self._build_response(resp, need_disclaimer=False)
            resp = f"好的，我了解了您的情况（{self.user_profile.age}岁{'/'+self.user_profile.gender if self.user_profile.gender else ''}）。请问您想咨询什么健康问题呢？"
            return self._build_response(resp)

        # 追问缺失信息
        if not self.user_profile.age:
            question = "请问您大概多大年纪呢？"
        elif not self.user_profile.gender:
            question = "请问您是男性还是女性呢？"
        elif not self.user_profile.chronic_diseases:
            question = "请问您有没有什么慢性病呢？比如高血压、糖尿病之类的。没有的话也没关系~"
        elif not self.user_profile.health_concerns:
            question = "您目前最关心的健康问题是什么呢？"
        else:
            question = "好的，我了解了。请问您今天想咨询什么健康问题呢？"
            self.state = SessionState.WELCOME

        return self._build_response(question)

    # --------------------------------------------------------
    # 症状分析（多轮追问）
    # --------------------------------------------------------

    def _handle_symptom_analysis(self, user_input: str) -> Dict:
        """处理症状分析多轮对话 - V3智能版"""
        # 调试输出
        print(f"[DEBUG] _handle_symptom_analysis: user_input='{user_input}', symptom_round={self.symptom_round}, symptom_data={self.symptom_data}")

        # 0. 检测重复输入
        is_repeat = self._is_repeat_input(user_input)
        print(f"[DEBUG] _is_repeat_input: {is_repeat}")
        if is_repeat:
            return self._build_response(
                "您刚才好像已经说过了，我记下了。咱们继续聊，"
                "您还有其他不舒服的地方吗？"
            )

        self.symptom_round += 1
        print(f"[DEBUG] symptom_round incremented to: {self.symptom_round}")

        # 1. 检测用户输入的是生理指标数值（如血压120、血糖6.5）
        vital_info = self._extract_vital_signs(user_input)
        if vital_info:
            self._apply_vital_to_profile(vital_info)
            resp = vital_info["assessment"] + "\n\n"
            if self.symptom_round == 1:
                resp += "那您具体是哪里不舒服呢？能描述一下症状吗？"
            else:
                resp += "除了这个，您还有其他不舒服的地方吗？"
            return self._build_response(resp)

        # 2. 检测模糊回答
        if self._is_vague_answer(user_input):
            return self._handle_vague_symptom_answer(user_input)

        # 3. 正常症状信息收集
        return self._smart_collect_symptom(user_input, first_input=user_input)

    def _is_repeat_input(self, user_input: str) -> bool:
        """检测用户是否重复输入相同内容"""
        # 纯数字（1-10评分）或数字+单位不算重复
        if re.match(r'^\d+\s*[分天周月年]?$', user_input.strip()):
            return False
        # 常见否定/确认回答不算重复
        common_responses = ["没有了", "没有", "是的", "对", "没错", "嗯", "好", "好的", "行", "可以"]
        if user_input.strip() in common_responses:
            return False

        recent_user_msgs = [
            msg.content for msg in self.messages[-6:]
            if msg.role == "user"
        ]
        # 最近3条用户消息中有2条以上相同
        count = sum(1 for m in recent_user_msgs if m.strip() == user_input.strip())
        return count >= 2

    def _extract_vital_signs(self, text: str) -> Optional[Dict]:
        """提取生理指标数值并判断是否正常"""
        # 血压模式: "血压120" / "血压120/80" / "收缩压120"
        bp_match = re.search(r'(?:血压|收缩压)\s*(\d{2,3})(?:/(\d{2,3}))?', text)
        if bp_match:
            systolic = int(bp_match.group(1))
            diastolic = int(bp_match.group(2)) if bp_match.group(2) else None
            if diastolic:
                assessment = f"您说的血压是{systolic}/{diastolic}mmHg。"
                if systolic <= 140 and diastolic <= 90:
                    assessment += "这个数值在正常范围内，不用太担心。"
                elif systolic > 140 or diastolic > 90:
                    assessment += "这个数值偏高，建议您定期监测血压，必要时咨询医生。"
                else:
                    assessment += "建议您继续保持良好的生活习惯。"
            else:
                assessment = f"您说的收缩压是{systolic}mmHg。"
                if systolic <= 140:
                    assessment += "这个数值在正常范围内。"
                else:
                    assessment += "这个数值偏高，建议您关注血压变化。"
                assessment += "请问舒张压（低压）是多少呢？"
            return {
                "type": "blood_pressure",
                "systolic": systolic,
                "diastolic": diastolic,
                "assessment": assessment
            }

        # 血糖模式: "血糖6.5" / "空腹血糖7.0"
        bs_match = re.search(r'(?:空腹)?血糖\s*(\d+\.?\d*)', text)
        if bs_match:
            value = float(bs_match.group(1))
            assessment = f"您说的血糖是{value}mmol/L。"
            if value <= 6.1:
                assessment += "空腹血糖在正常范围内。"
            elif value <= 7.0:
                assessment += "空腹血糖偏高，属于空腹血糖受损，建议注意饮食控制。"
            else:
                assessment += "空腹血糖偏高，建议您到医院做进一步检查。"
            return {
                "type": "blood_sugar",
                "value": value,
                "assessment": assessment
            }

        return None

    def _apply_vital_to_profile(self, vital_info: Dict):
        """将生理指标应用到用户画像"""
        if vital_info["type"] == "blood_pressure":
            systolic = vital_info["systolic"]
            if systolic > 140:
                if "高血压" not in (self.user_profile.chronic_diseases or ""):
                    self.user_profile.update_field(
                        "chronic_diseases",
                        ("高血压" + "、" + self.user_profile.chronic_diseases).strip("、"),
                        "血压数值偏高"
                    )
            self.user_profile.update_field("health_concerns", "血压", "血压相关咨询")
        elif vital_info["type"] == "blood_sugar":
            value = vital_info["value"]
            if value > 6.1:
                if "血糖偏高" not in (self.user_profile.chronic_diseases or ""):
                    self.user_profile.update_field(
                        "chronic_diseases",
                        ("血糖偏高" + "、" + self.user_profile.chronic_diseases).strip("、"),
                        "血糖数值偏高"
                    )
            self.user_profile.update_field("health_concerns", "血糖", "血糖相关咨询")
        self.user_profile.update_completeness()

    def _is_vague_answer(self, text: str) -> bool:
        """检测模糊回答"""
        vague_patterns = [
            "不知道", "不清楚", "不确定", "没注意",
            "就是.*", "好像", "可能", "也许",
            "说不上来", "讲不清"
        ]
        text_stripped = text.strip()
        # 纯数字或数字+单位不算模糊（如"5"、"5分"、"3天"）
        if re.match(r'^\d+\s*[分天周月年]?$', text_stripped):
            return False
        # 常见症状词不算模糊
        symptom_words = ["头疼", "头痛", "头晕", "胃疼", "胃痛", "肚子疼", "肚子痛", "胸闷", "心慌", "心悸",
                        "失眠", "疲劳", "乏力", "便秘", "腹泻", "恶心", "发烧", "咳嗽", "抽筋"]
        if text_stripped in symptom_words:
            return False
        # 极短回答（1个字）算模糊
        if len(text_stripped) <= 1:
            return True
        return any(re.search(p, text_stripped) for p in vague_patterns)

    def _handle_vague_symptom_answer(self, user_input: str) -> Dict:
        """处理模糊的症状回答"""
        if self.symptom_round <= 2:
            return self._build_response(
                "没关系，不用着急。您能试着描述一下吗？"
                "比如：是疼、是酸、还是胀？在身体哪个位置？"
            )
        elif self.symptom_round == 3:
            return self._build_response(
                "好的，我了解了。那您这种情况大概出现多久了？"
                "是一直有还是最近才开始的？"
            )
        else:
            # 已经收集了足够信息（即使有些模糊），直接生成总结
            return self._generate_symptom_summary()

    def _smart_collect_symptom(self, user_input: str, first_input: str = "") -> Dict:
        """智能收集症状信息 - 根据内容自动分配字段"""
        # 检测是否是产品咨询意图（治疗/买什么/有什么产品等）
        product_intent_keywords = ["治疗", "买什么", "有什么.*能", "推荐.*药", "吃什么药", "用什么药"]
        if any(re.search(kw, user_input) for kw in product_intent_keywords):
            # 切换到产品咨询
            self.state = SessionState.PRODUCT_CONSULT
            return self._handle_product_consult(user_input)

        info = self._analyze_symptom_input(user_input)

        # 提取症状关键词用于回复中包含
        symptom_kw = self._extract_symptom_keyword(first_input or user_input)

        if info["has_duration"]:
            self.symptom_data["duration_severity"] = user_input
        elif info["has_accompany"]:
            self.symptom_data["accompany"] = user_input
        elif info["has_medication"]:
            self.symptom_data["history_medication"] = user_input
        else:
            if self.symptom_round == 1:
                self.symptom_data["main_symptom"] = user_input
                knowledge_info = self._get_knowledge_fallback(user_input)
                # 回复中包含症状关键词
                if symptom_kw:
                    q = f"关于您说的【{symptom_kw}】，{SYMPTOM_QUESTIONS[SymptomRound.DURATION_SEVERITY]}"
                    if knowledge_info:
                        q = f"{knowledge_info}\n\n{q}"
                    return self._build_response(q)
                if knowledge_info:
                    question = f"{knowledge_info}\n\n{SYMPTOM_QUESTIONS[SymptomRound.DURATION_SEVERITY]}"
                    return self._build_response(question)
                return self._build_response(SYMPTOM_QUESTIONS[SymptomRound.DURATION_SEVERITY])
            elif self.symptom_round == 2:
                self.symptom_data["duration_severity"] = user_input
            elif self.symptom_round == 3:
                self.symptom_data["accompany"] = user_input
            elif self.symptom_round >= 4:
                self.symptom_data["history_medication"] = user_input
                return self._generate_symptom_summary()

        filled_fields = sum(1 for v in self.symptom_data.values() if v and v.strip())
        # 调试输出到文件
        with open('debug.log', 'a', encoding='utf-8') as f:
            f.write(f"[DEBUG] round={self.symptom_round}, filled={filled_fields}, data={self.symptom_data}\n")

        if filled_fields >= 3 or self.symptom_round >= 4:
            return self._generate_symptom_summary()

        return self._next_symptom_question()

    def _extract_symptom_keyword(self, text: str) -> str:
        """从文本中提取症状关键词"""
        symptom_keywords = ["抽筋", "腿抽筋", "头晕", "头疼", "头痛", "心慌", "心悸",
                          "失眠", "睡不着", "胸闷", "胃疼", "胃痛", "关节疼", "关节痛",
                          "背疼", "腰疼", "腿疼", "疲劳", "乏力", "没精神", "潮热",
                          "盗汗", "便秘", "腹泻", "胃胀", "眼花", "视力模糊"]
        for kw in symptom_keywords:
            if kw in text:
                return kw
        # 提取"X疼/X痛/X不舒服"等模式
        m = re.search(r'([^\s]+?疼|[^\s]+?痛|[^\s]+?不舒服)', text)
        if m:
            return m.group(1)
        return ""



    def _analyze_symptom_input(self, text: str) -> Dict:
        """分析用户输入包含的信息类型"""
        duration_keywords = ["多久", "几天", "几周", "几个月", "年了", "天了", "周了",
                           "一直", "最近", "刚开始", "反复", "经常", "偶尔",
                           "早上", "晚上", "饭后", "饭前", "睡前"]
        accompany_keywords = ["还有", "另外", "同时", "伴随", "除了", "以及",
                            "也", "还", "伴有"]
        medication_keywords = ["吃药", "服药", "用药", "药", "降压药", "降糖药",
                             "胰岛素", "华法林", "之前", "以前", "看过", "医院"]

        return {
            "has_duration": any(kw in text for kw in duration_keywords),
            "has_accompany": any(kw in text for kw in accompany_keywords),
            "has_medication": any(kw in text for kw in medication_keywords)
        }

    def _next_symptom_question(self) -> Dict:
        """根据已收集信息决定下一个追问"""
        main_symptom = self.symptom_data.get("main_symptom", "")
        if "duration_severity" not in self.symptom_data:
            q = _format_symptom_question(SymptomRound.DURATION_SEVERITY, main_symptom)
            return self._build_response(q)
        elif "accompany" not in self.symptom_data:
            q = _format_symptom_question(SymptomRound.ACCOMPANY, main_symptom)
            return self._build_response(q)
        elif "history_medication" not in self.symptom_data:
            q = _format_symptom_question(SymptomRound.HISTORY_MEDICATION, main_symptom)
            return self._build_response(q)
        else:
            return self._generate_symptom_summary()

    def _get_knowledge_fallback(self, query: str) -> Optional[str]:
        """从知识库获取信息，用于兜底回复"""
        # 检查知识库
        for keyword, content in KNOWLEDGE_BASE.items():
            if keyword in query:
                return f"关于【{keyword}】：{content}"

        # 检查症状关键词
        symptom_advice = {
            "头疼": "头痛可能有多种原因，比如紧张、血压波动、睡眠不足等。建议您注意休息，保持规律作息。如果持续或加重，建议就医检查。",
            "头痛": "头痛可能有多种原因，比如紧张、血压波动、睡眠不足等。建议您注意休息，保持规律作息。如果持续或加重，建议就医检查。",
            "失眠": "失眠可能与情绪、生活习惯、年龄等因素有关。建议您睡前避免饮茶和咖啡，保持规律作息，适当散步有助于睡眠。",
            "睡不着": "失眠可能与情绪、生活习惯、年龄等因素有关。建议您睡前避免饮茶和咖啡，保持规律作息，适当散步有助于睡眠。",
            "关节": "关节不适可能与年龄、运动、天气变化有关。建议您注意保暖，适度运动，避免过度劳累。",
            "膝盖": "膝盖不适可能与关节磨损、运动损伤有关。建议您避免剧烈运动，注意膝盖保暖。",
            "胃": "胃部不适可能与饮食、消化有关。建议您少食多餐，避免辛辣油腻食物。",
            "疲劳": "疲劳可能与睡眠不足、营养不均衡、缺乏运动有关。建议您保持规律作息，均衡饮食，适度运动。",
            "累": "疲劳可能与睡眠不足、营养不均衡、缺乏运动有关。建议您保持规律作息，均衡饮食，适度运动。",
            "血压": "血压偏高需要注意饮食清淡，减少盐分摄入，保持规律运动。建议定期监测血压。",
            "血糖": "血糖偏高需要注意控制糖分摄入，多吃粗粮蔬菜，定期检测血糖。",
            "心脏": "心脏相关不适需要高度重视，建议您尽快到医院心内科检查。",
            "胸闷": "胸闷可能是多种原因引起的，建议您关注是否有其他症状，必要时及时就医。",
            "胸口": "胸口不适需要重视，建议您注意休息，如果持续或加重请及时就医。"
        }

        for keyword, advice in symptom_advice.items():
            if keyword in query:
                return advice

        # ---- 扩展：从上传的知识库中搜索 ----
        try:
            from admin_service import knowledge_service
            results = knowledge_service.search_chunks(query, top_k=1)
            if results:
                chunk = results[0]
                return f"关于【{chunk.get('title', '知识库')}】：{chunk['content']}"
        except Exception:
            pass

        return None

    def _generate_symptom_summary(self) -> Dict:
        """生成症状分析总结并推荐产品"""
        self.state = SessionState.PRODUCT_RECOMMEND

        main = self.symptom_data.get("main_symptom", "")
        duration = self.symptom_data.get("duration_severity", "")
        accompany = self.symptom_data.get("accompany", "")
        history = self.symptom_data.get("history_medication", "")

        summary = "【症状总结】\n"
        summary += f"主要不适：{main}\n"
        if duration:
            summary += f"持续时间及程度：{duration}\n"
        if accompany:
            summary += f"伴随症状：{accompany}\n"

        # 基于症状生成针对性健康建议
        all_symptoms = f"{main} {accompany}"
        health_advice = self._get_targeted_health_advice(all_symptoms)

        summary += "\n【健康建议】\n"
        summary += health_advice + "\n"
        summary += "如果症状持续或加重，请及时就医检查。\n"

        # 匹配产品
        products = self._match_products(main + " " + accompany)

        if products:
            summary += "\n【推荐产品】\n"
            for i, p in enumerate(products[:3], 1):
                summary += f"{i}.【{p['name']}】\n"
                summary += f"  功效：{p['efficacy']}\n"
                summary += f"  适用人群：{p['audience']}\n"
                summary += f"  服用方法：{p['usage']}\n"

        summary += f"\n{DISCLAIMER_TEXT}"

        return self._build_response(summary, need_disclaimer=False)

    def _get_targeted_health_advice(self, symptoms: str) -> str:
        """基于症状生成针对性健康建议"""
        # 症状-建议映射表
        advice_map = {
            # 消化系统
            "肚子": ["注意腹部保暖，避免受凉", "少食多餐，避免暴饮暴食", "饮食清淡，少吃油腻辛辣食物"],
            "胃": ["规律饮食，定时定量", "避免过冷过热食物", "细嚼慢咽，减轻胃部负担"],
            "拉肚子": ["注意补充水分，防止脱水", "饮食清淡，暂时避免乳制品", "注意食品卫生，避免生冷食物"],
            "便秘": ["多喝水，每天2000ml左右", "多吃富含膳食纤维的食物，如蔬菜、粗粮", "养成定时排便习惯，适当运动"],
            "腹泻": ["注意补充水分和电解质", "饮食清淡，选择易消化食物", "避免油腻、辛辣、生冷食物"],

            # 头部/神经
            "头疼": ["保证充足睡眠，避免熬夜", "减少压力，适当放松心情", "注意用眼卫生，避免长时间看屏幕"],
            "头痛": ["规律作息，避免过度劳累", "保持室内空气流通", "适当按摩太阳穴缓解紧张"],
            "头晕": ["起身时动作缓慢，避免突然站立", "保证充足睡眠", "适当补充含铁食物，如红枣、菠菜"],
            "失眠": ["睡前避免饮茶和咖啡", "保持规律作息，固定睡眠时间", "睡前可以泡脚或听轻音乐放松"],

            # 心血管
            "心慌": ["避免剧烈运动和情绪激动", "保证充足休息", "减少咖啡、浓茶摄入"],
            "胸闷": ["保持室内空气流通", "避免情绪激动和压力过大", "如频繁发作建议做心电图检查"],
            "血压": ["低盐饮食，每日盐摄入不超过6克", "适度运动，如散步、太极", "定期监测血压，保持情绪稳定"],

            # 骨骼关节
            "关节": ["注意关节保暖，避免受凉", "适度活动，避免长时间保持同一姿势", "控制体重，减轻关节负担"],
            "膝盖": ["避免爬楼梯和深蹲动作", "注意膝盖保暖", "适度做膝关节活动操"],
            "腰": ["避免久坐久站，适当活动", "注意腰部保暖", "睡硬板床，保持正确坐姿"],
            "抽筋": ["注意补充钙质，多喝牛奶、豆制品", "睡前做腿部拉伸运动", "注意腿部保暖，避免受凉"],

            # 代谢/内分泌
            "血糖": ["控制主食摄入，选择低GI食物", "多吃蔬菜，适量运动", "定期监测血糖，遵医嘱用药"],
            "疲劳": ["保证充足睡眠，避免熬夜", "均衡饮食，适当补充蛋白质", "适度运动，如散步、太极"],
            "乏力": ["注意营养均衡，不偏食", "适当补充含铁和维生素B的食物", "避免过度劳累，劳逸结合"],

            # 呼吸
            "咳嗽": ["多喝温水，保持喉咙湿润", "避免烟尘刺激", "注意保暖，避免受凉"],
            "感冒": ["多休息，保证充足睡眠", "多喝温水", "饮食清淡，注意保暖"],
        }

        # 匹配症状并收集建议（支持关键词变体）
        matched_advice = []
        for keyword, advice_list in advice_map.items():
            # 直接匹配
            if keyword in symptoms:
                matched_advice.extend(advice_list)
            # 扩展匹配：肚子疼/肚子痛/胃疼/胃胀等
            elif keyword == "肚子" and any(k in symptoms for k in ["肚子疼", "肚子痛", "腹部", "肠胃"]):
                matched_advice.extend(advice_list)
            elif keyword == "胃" and any(k in symptoms for k in ["胃疼", "胃痛", "胃胀", "胃酸", "反酸", "烧心"]):
                matched_advice.extend(advice_list)
            elif keyword == "头疼" and any(k in symptoms for k in ["头痛", "偏头疼", "偏头痛", "头胀"]):
                matched_advice.extend(advice_list)
            elif keyword == "关节" and any(k in symptoms for k in ["关节痛", "关节炎", "关节疼", "骨关节"]):
                matched_advice.extend(advice_list)

        # 去重并限制数量
        unique_advice = list(dict.fromkeys(matched_advice))[:3]

        if unique_advice:
            return "针对您的情况，建议：\n" + "\n".join([f"• {a}" for a in unique_advice])
        else:
            return "建议您保持良好的生活习惯，合理饮食，适度运动。"

    # --------------------------------------------------------
    # 产品推荐
    # --------------------------------------------------------

    def _handle_product_recommend(self, user_input: str) -> Dict:
        """处理产品推荐后续对话"""
        # 感谢类回复
        if any(kw in user_input for kw in ["谢谢", "感谢", "谢了"]):
            resp = "不客气！很高兴能帮到您~\n\n如果您还有其他问题，随时问我哦。祝您身体健康！"
            self.state = SessionState.WELCOME
            return self._build_response(resp)

        # 确认/结束类回复
        if any(kw in user_input for kw in ["好的", "行", "可以", "嗯", "知道了", "明白了"]):
            resp = "好的！如果您还有其他健康问题，随时问我哦~\n祝您身体健康！"
            self.state = SessionState.WELCOME
            return self._build_response(resp)

        # 用户继续提问产品相关问题
        product_keywords = ["药", "产品", "多少钱", "价格", "怎么买", "哪里买", "吃多久", "副作用"]
        if any(kw in user_input for kw in product_keywords):
            self.state = SessionState.PRODUCT_CONSULT
            return self._handle_product_consult(user_input)

        # 用户可能切换到其他意图
        detected = self._auto_detect_intent(user_input)
        if detected:
            self.current_intent = detected
            return self._route_by_intent(user_input)

        resp = "好的，如果您还有其他健康问题，随时可以问我。也可以选择其他咨询方向哦~"
        return self._build_response(resp)

    # --------------------------------------------------------
    # 产品咨询
    # --------------------------------------------------------

    def _handle_product_consult(self, user_input: str) -> Dict:
        """处理产品咨询 - V3增强版：支持自然语言产品查询"""
        # 获取对话历史上下文
        context = self._get_conversation_context()

        # 检查是否是特定产品查询（"XX怎么样"、"能吃XX吗"、"想买XX"）
        specific_product = self._extract_specific_product(user_input)
        if specific_product:
            # 直接找到对应产品
            matched = [p for p in PRODUCT_DATABASE if p["name"] == specific_product]
            if not matched:
                matched = [p for p in PRODUCT_DATABASE if specific_product in p["name"]]
            if matched:
                p = matched[0]
                resp = f"关于【{p['name']}】：\n\n"
                resp += f"功效：{p['efficacy']}\n"
                resp += f"适用人群：{p['audience']}\n"
                resp += f"服用方法：{p['usage']}\n"
                # 安全提醒
                if self.user_profile.chronic_diseases:
                    resp += f"\n您的健康状况（{self.user_profile.chronic_diseases}）需要注意，建议服用前咨询医生。"
                self.last_recommended = [p['name']]
                return self._build_response(resp, need_disclaimer=False)

        # 合并当前输入和上下文进行产品匹配
        search_query = user_input + " " + context
        products = self._match_products(search_query)

        # 如果当前输入没匹配到，但上下文有症状信息，尝试用上下文匹配
        if not products and context:
            products = self._match_products(context)

        # 检查药物禁忌
        contraindication_warning = ""
        if self.user_profile.current_medication:
            for product in products:
                for contraindication in product.get("contraindications", []):
                    if contraindication in self.user_profile.current_medication:
                        contraindication_warning = f"\n\n⚠️ 注意：您正在服用{self.user_profile.current_medication}，"
                        contraindication_warning += f"服用{product['name']}前请咨询医生意见。"
                        break

        if products:
            resp = "根据您的情况，我为您推荐：\n\n"
            for i, p in enumerate(products[:3], 1):
                resp += f"{i}.【{p['name']}】\n"
                resp += f"  功效：{p['efficacy']}\n"
                resp += f"  适用人群：{p['audience']}\n"
                resp += f"  服用方法：{p['usage']}\n\n"
            resp += "温馨提示：保健品不能替代药物治疗，如有不适请及时就医。"
            resp += contraindication_warning
            self.last_recommended = [p['name'] for p in products[:3]]
        else:
            if any(kw in user_input for kw in ["药", "产品", "推荐", "什么", "哪些", "保健品"]):
                resp = "抱歉，根据您描述的情况，我暂时没有找到特别匹配的产品。\n\n"
                resp += "您可以告诉我更具体的症状，比如：\n"
                resp += "• 是哪里不舒服？（头痛、关节、肠胃等）\n"
                resp += "• 有没有慢性病？（高血压、糖尿病等）\n"
                resp += "• 想改善什么方面？\n\n"
                resp += "这样我能给您更准确的建议~"
            else:
                resp = "请问您想解决什么健康问题呢？比如心脑血管、骨骼关节、肠胃消化、头痛失眠等，我可以给您推荐合适的产品~"

        return self._build_response(resp, need_disclaimer=False)

    def _extract_specific_product(self, text: str) -> Optional[str]:
        """提取用户询问的特定产品名"""
        product_names = [p["name"] for p in PRODUCT_DATABASE]
        # 也匹配简称
        short_names = {
            "益生菌": "益生菌粉", "鱼油": "鱼油软胶囊", "钙片": "钙片+维生素D3",
            "维生素": "复合维生素B族", "氨糖": "氨糖软骨素", "护肝片": "护肝片",
            "叶黄素": "叶黄素软胶囊", "褪黑素": "褪黑素片", "辅酶": "辅酶Q10",
            "大豆异黄酮": "大豆异黄酮", "维生素D": "钙片+维生素D3",
            "维生素C": "复合维生素B族", "液体钙": "钙片+维生素D3"
        }
        for short, full in short_names.items():
            if short in text:
                return full
        return None

    def _get_conversation_context(self) -> str:
        """获取对话上下文（最近5轮用户输入）"""
        context_parts = []
        for msg in reversed(self.messages[-10:]):
            if msg.role == "user":
                context_parts.append(msg.content)
        return " ".join(context_parts)

    def _get_context_summary(self) -> str:
        """获取对话上下文摘要"""
        # 提取关键信息
        symptoms = []
        concerns = []
        for msg in self.messages:
            if msg.role == "user":
                # 提取症状关键词
                symptom_keywords = ["疼", "痛", "不舒服", "失眠", "头晕", "疲劳"]
                for kw in symptom_keywords:
                    if kw in msg.content and msg.content not in symptoms:
                        symptoms.append(msg.content)
                        break

        if symptoms:
            return "；".join(symptoms[-3:])  # 最近3个症状
        return ""

    # --------------------------------------------------------
    # 健康知识问答
    # --------------------------------------------------------

    def _handle_knowledge_qa(self, user_input: str) -> Dict:
        """处理健康知识问答 - V3增强版：支持追问和深层知识"""
        # 匹配知识库
        matched = []
        for keyword, content in KNOWLEDGE_BASE.items():
            if keyword in user_input:
                matched.append((keyword, content))

        # 追问检测：检查是否在追问上一轮知识
        if not matched:
            last_assistant_msg = ""
            for msg in reversed(self.messages):
                if msg.role == "assistant":
                    last_assistant_msg = msg.content
                    break
            # 如果上一轮是知识回答，当前是追问
            if last_assistant_msg and ("关于" in last_assistant_msg or "了解到" in last_assistant_msg):
                # 尝试从上下文推断追问主题
                context = self._get_conversation_context()
                for keyword, content in KNOWLEDGE_BASE.items():
                    if keyword in context and keyword not in user_input:
                        matched.append((keyword, content))

        # 特殊追问处理
        if "DHA" in user_input and "EPA" in user_input:
            resp = "DHA和EPA都是鱼油中的重要成分，但作用不同：\n\n"
            resp += "【DHA】主要作用于大脑和视网膜，有助于维持认知功能和视力健康。老年人适当补充DHA有助于预防记忆力下降。\n\n"
            resp += "【EPA】主要作用于心血管系统，有助于降低血脂、抗炎。对保护血管弹性、预防血栓有一定帮助。\n\n"
            resp += "建议老年人选择DHA和EPA比例均衡的鱼油产品，两者搭配效果更好~"
            return self._build_response(resp)

        if "老年人" in user_input and ("更需要" in user_input or "哪种" in user_input):
            resp = "对于老年人来说，建议两者都补充，但可以有所侧重：\n\n"
            resp += "• 如果关注心脑血管健康：选择EPA含量较高的鱼油\n"
            resp += "• 如果关注记忆力和视力：选择DHA含量较高的鱼油\n"
            resp += "• 综合保健：选择DHA:EPA约1:1.5的均衡配方\n\n"
            resp += "具体选择建议根据个人健康状况，有慢性病的话建议咨询医生。"
            return self._build_response(resp)

        if matched:
            resp = f"关于您问的【{matched[0][0]}】，我了解到：\n\n"
            resp += matched[0][1]
            resp += "\n\n如果还有其他问题，欢迎继续问我哦~"

            # 如果涉及症状相关话题，附加免责声明
            symptom_related = any(kw in user_input for kw in ["症状", "不舒服", "疼痛", "难受", "生病"])
            if symptom_related:
                resp += f"\n\n{DISCLAIMER_TEXT}"
        else:
            resp = "这个问题我暂时不太确定答案。建议您咨询专业医生获取更准确的信息。\n\n您也可以问我关于血压、血糖、睡眠、饮食、运动、鱼油、钙片、维生素等方面的健康知识哦~"

        return self._build_response(resp, need_disclaimer=False)

    # --------------------------------------------------------
    # 边界处理
    # --------------------------------------------------------

    def _handle_boundary(self, user_input: str) -> Dict:
        """处理边界情况 - V3增强版"""
        # 超长对话总结请求
        if any(kw in user_input for kw in ["总结", "汇总", "前面说的", "综上所述", "所以"]):
            return self._handle_context_summary_request(user_input)

        # 闲聊
        chat_keywords = ["你好", "谢谢", "再见", "在吗", "你是谁", "天气"]
        if any(kw in user_input for kw in chat_keywords):
            resp = "您好！我是泰小虎，您的健康顾问~\n我可以帮您解答健康问题、推荐保健品、了解健康知识。请问有什么可以帮到您的吗？"
            return self._build_response(resp)

        # 投诉
        complaint_keywords = ["投诉", "不满", "差评", "质量", "退款", "退货"]
        if any(kw in user_input for kw in complaint_keywords):
            resp = "非常抱歉给您带来不好的体验。我已经把您的反馈记录下来，会转达给相关工作人员。如需紧急帮助，请联系客服电话：400-xxx-xxxx。"
            return self._build_response(resp, state=SessionState.TRANSFER_CS)

        # 模糊/犹豫输入
        if self._is_vague_answer(user_input):
            return self._build_response(
                "没关系，您慢慢想。有什么想说的随时告诉我，我在这等着您~"
            )

        # 无关话题
        resp = "这个问题我不太擅长呢~\n不过作为您的健康顾问，我很乐意帮您解答健康方面的问题！请问有什么健康问题可以帮到您吗？"
        return self._build_response(resp)

    def _handle_context_summary_request(self, user_input: str) -> Dict:
        """处理用户请求总结对话"""
        # 收集对话中的关键信息
        symptoms = []
        products_mentioned = []
        profile_info = []

        for msg in self.messages:
            if msg.role == "user":
                # 提取症状
                for kw in ["睡眠", "失眠", "头晕", "疲劳", "胃", "关节", "腿", "抽筋",
                           "血压", "血糖", "心慌", "胸闷", "头疼", "便秘"]:
                    if kw in msg.content and kw not in symptoms:
                        symptoms.append(kw)
                # 提取产品
                for p in PRODUCT_DATABASE:
                    if p["name"] in msg.content or any(s in msg.content for s in p["symptoms"][:2]):
                        if p["name"] not in products_mentioned:
                            products_mentioned.append(p["name"])

        # 画像信息
        if self.user_profile.age:
            profile_info.append(f"{self.user_profile.age}岁")
        if self.user_profile.gender:
            profile_info.append(self.user_profile.gender)
        if self.user_profile.chronic_diseases:
            profile_info.append(self.user_profile.chronic_diseases)

        resp = "好的，帮您总结一下咱们聊到的内容：\n\n"
        if profile_info:
            resp += f"【您的基本情况】{'、'.join(profile_info)}\n\n"
        if symptoms:
            resp += f"【健康关注】{'、'.join(symptoms)}\n\n"

        # 基于总结推荐产品
        all_text = " ".join(symptoms) + " " + " ".join(profile_info)
        recommended = self._match_products(all_text)
        if recommended:
            resp += "【推荐产品】\n"
            for i, p in enumerate(recommended[:3], 1):
                resp += f"{i}. {p['name']} - {p['efficacy']}\n"
        else:
            resp += "建议您根据以上情况，选择对应的保健产品。如有需要可以告诉我具体想了解哪方面。"

        resp += f"\n{DISCLAIMER_TEXT}"
        return self._build_response(resp, need_disclaimer=False)

    def _handle_complaint(self, user_input: str) -> Dict:
        """处理投诉 - V3：记录投诉后继续服务"""
        # 记录投诉内容
        if not hasattr(self, 'complaint_content'):
            self.complaint_content = []
        self.complaint_content.append(user_input)

        resp = "非常抱歉给您带来不好的体验。我已经详细记录下您的反馈：\n\n"
        resp += f"\"{user_input}\"\n\n"
        resp += "我们会尽快处理并改进。请问还有其他我可以帮您的吗？"
        # 保持在COMPLAINT状态
        return self._build_response(resp, state=SessionState.COMPLAINT)

    # --------------------------------------------------------
    # 复购推荐
    # --------------------------------------------------------

    def _handle_repurchase(self, user_input: str) -> Dict:
        """处理复购推荐 - V2增强版"""
        # 检查是否有购买历史
        if not self.purchase_history:
            resp = "目前没有您的购买记录。请问您想了解什么产品呢？"
            self.state = SessionState.PRODUCT_CONSULT
            return self._build_response(resp)

        # 用户询问效果
        if any(kw in user_input for kw in ["没用", "没效果", "不好", "没用啊"]):
            resp = "我理解您的感受。保健品的效果因人而异，也需要一定时间。\n\n"
            resp += "建议您：\n"
            resp += "• 坚持按说明服用，一般需要1-3个月见效\n"
            resp += "• 如果症状持续或加重，建议就医检查\n"
            resp += "• 医生可能会根据您的情况调整方案\n\n"
            resp += "您具体是什么症状没有改善呢？我可以帮您分析。"
            self.state = SessionState.SYMPTOM_ANALYSIS
            return self._build_response(resp)

        # 用户确认复购
        if any(kw in user_input for kw in ["对", "是的", "要", "买", "复购"]):
            latest = self.purchase_history[-1]
            resp = f"好的，您之前购买的是【{latest.product_name}】。\n"
            resp += "我们也有升级版的液体钙，吸收更好，需要了解一下吗？"
            return self._build_response(resp)

        # 询问升级产品
        if any(kw in user_input for kw in ["升级", "更好", "吸收", "液体钙"]):
            resp = "推荐您试试我们的液体钙，吸收率比普通钙片高30%。\n"
            resp += "价格198元/瓶，现在购买还有优惠活动哦~"
            return self._build_response(resp)

        # 询问价格
        if any(kw in user_input for kw in ["多少钱", "价格"]):
            resp = "液体钙198元/瓶，普通钙片168元/瓶。\n"
            resp += "现在购买满200减20，需要我帮您算一下怎么买最划算吗？"
            return self._build_response(resp)

        # 默认：询问复购意向
        latest = self.purchase_history[-1]
        resp = f"您之前购买过【{latest.product_name}】，按照用法大概可以用{latest.duration_months}个月。\n"
        resp += "这次是想继续购买同款，还是了解一下其他产品呢？"

        return self._build_response(resp)

    # --------------------------------------------------------
    # 辅助方法
    # --------------------------------------------------------

    def _check_emergency(self, text: str) -> bool:
        """检查是否包含紧急症状 - V2增强版"""
        # 直接匹配紧急症状
        for symptom in EMERGENCY_SYMPTOMS:
            if symptom in text:
                return True

        # 检查紧急描述模式
        emergency_patterns = [
            r"胸口.*痛", r"胸口.*疼", r"喘不上气", r"呼吸困难",
            r"突然.*疼", r"剧烈.*痛", r"疼.*厉害", r"痛.*厉害"
        ]
        for pattern in emergency_patterns:
            if re.search(pattern, text):
                return True

        return False

    def _should_transfer_cs(self, text: str) -> bool:
        """判断是否需要转接客服"""
        cs_keywords = ["转人工", "找客服", "人工服务", "人工", "客服"]
        # 如果用户明确拒绝转人工，不触发
        reject_keywords = ["不用", "不用了", "不必", "就跟你说", "就跟你"]
        if any(kw in text for kw in reject_keywords):
            return False
        return any(kw in text for kw in cs_keywords)

    def _check_intent_deny(self, text: str) -> bool:
        """检查用户是否否认当前意图"""
        deny_keywords = ["不是", "不对", "不想", "错了", "不是这个", "不是我要的"]
        return any(kw in text for kw in deny_keywords)

    def _auto_detect_intent(self, text: str) -> Optional[IntentType]:
        """自动检测用户意图（关键词匹配）- V2增强版"""
        # 健康咨询关键词
        health_keywords = [
            "不舒服", "疼", "痛", "难受", "症状", "头晕", "咳嗽", "拉肚子",
            "失眠", "血压", "血糖", "心慌", "胸闷", "发烧", "头痛", "恶心",
            "头疼", "偏头痛", "关节", "膝盖", "腰", "腿", "胃", "肚子",
            "便秘", "腹泻", "疲劳", "累", "没精神", "睡不着", "睡不好",
            "忘事", "记忆力", "抽筋", "缺钙", "心脏", "胸口", "气短",
            "高血脂", "糖尿病", "高血压", "骨质疏松", "胃胀", "反酸",
            "潮热", "盗汗", "更年期", "眼花"
        ]

        # 产品咨询关键词
        product_keywords = [
            "买", "产品", "保健品", "多少钱", "价格", "推荐", "哪个好",
            "选购", "购买", "牌子", "功效", "效果", "作用", "有用吗",
            "怎么吃", "用法", "服用", "成分", "调理", "改善"
        ]

        # 健康知识关键词
        knowledge_keywords = [
            "什么是", "为什么", "怎么", "如何", "知识", "科普",
            "养生", "健康知识", "了解", "预防", "注意什么", "能吃吗",
            "可以吃", "好不好", "对不对", "是不是", "真的吗"
        ]

        # 复购关键词
        repurchase_keywords = [
            "复购", "再买", "还要", "吃完了", "用完了", "快用完",
            "之前.*买", "上次.*买"
        ]

        # 投诉关键词
        complaint_keywords = ["投诉", "差评", "退货", "退款", "质量.*问题"]

        # 画像更新关键词
        profile_keywords = [
            "更新资料", "更新信息", "我的资料", "我的信息",
            "我.*岁", "我.*岁了", "确诊",
            "我有.*病", "没有高血压", "没有.*病",
            "血糖偏高", "血糖高", "血脂高", "前期"
        ]

        # 家属购买关键词（优先于一般产品咨询）
        family_keywords = ["给我老伴", "给老伴", "给.*妈", "给.*爸", "给.*婆婆", "给.*公公", "给.*岳母", "给.*岳父", "给.*老公", "给.*老婆"]

        text_lower = text.lower()

        # 优先级：投诉 > 紧急 > 画像更新 > 家属购买 > 复购 > 健康 > 产品 > 知识
        if any(kw in text_lower for kw in complaint_keywords):
            return IntentType.COMPLAINT

        if self._check_emergency(text_lower):
            return IntentType.HEALTH_CONSULT

        if any(re.search(kw, text_lower) for kw in profile_keywords):
            return IntentType.PROFILE_UPDATE

        if any(re.search(kw, text_lower) for kw in family_keywords):
            return IntentType.PROFILE_UPDATE  # 家属购买也走画像收集流程

        if any(kw in text_lower for kw in repurchase_keywords):
            return IntentType.REPURCHASE

        if any(kw in text_lower for kw in health_keywords):
            return IntentType.HEALTH_CONSULT

        if any(kw in text_lower for kw in product_keywords):
            return IntentType.PRODUCT_CONSULT

        if any(kw in text_lower for kw in knowledge_keywords):
            return IntentType.KNOWLEDGE_QUERY

        return None

    def _match_products(self, query: str) -> List[Dict]:
        """根据用户描述匹配产品 - V2增强版"""
        scored = []
        for product in PRODUCT_DATABASE:
            score = 0
            for symptom_kw in product["symptoms"]:
                if symptom_kw in query:
                    score += 1
            if score > 0:
                scored.append((score, product))

        # 按匹配度排序
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored]

    def _build_response(self, text: str, state: Optional[SessionState] = None,
                        need_disclaimer: Optional[bool] = None,
                        metadata: Optional[Dict] = None) -> Dict:
        """构建标准响应"""
        if state:
            self.state = state

        # 保存助手消息
        self.messages.append(Message(role="assistant", content=text, intent=self.current_intent))

        # 自动判断是否需要免责声明
        if need_disclaimer is None:
            last_user_msg = ""
            for msg in reversed(self.messages):
                if msg.role == "user":
                    last_user_msg = msg.content
                    break
            need_disclaimer = self._should_add_disclaimer(last_user_msg)

        if need_disclaimer and DISCLAIMER_TEXT not in text:
            text += f"\n\n{DISCLAIMER_TEXT}"

        # 限制消息数量
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

        return {
            "response": text,
            "state": self.state.value,
            "intent": self.current_intent.value if self.current_intent else None,
            "metadata": metadata or {},
            "profile_completeness": self.user_profile.completeness
        }

    def _should_add_disclaimer(self, text: str) -> bool:
        """判断是否需要附加免责声明"""
        symptom_keywords = ["疼", "痛", "不舒服", "难受", "症状", "头晕", "咳嗽",
                          "拉肚子", "失眠", "胸闷", "发烧", "出血", "麻木"]
        return any(kw in text for kw in symptom_keywords)

    # --------------------------------------------------------
    # 公共接口
    # --------------------------------------------------------

    def get_conversation_history(self) -> List[Dict]:
        """获取对话历史"""
        return [msg.to_dict() for msg in self.messages]

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "name": self.name,
            "total_messages": len(self.messages),
            "state": self.state.value,
            "intent": self.current_intent.value if self.current_intent else None,
            "symptom_round": self.symptom_round,
            "profile": self.user_profile.to_dict(),
            "purchase_count": len(self.purchase_history)
        }

    def clear_session(self):
        """清空会话（清空前保存画像和会话记录）"""
        # 保存当前会话的画像和消息
        self._save_profile_and_session()
        self.messages.clear()
        self.state = SessionState.WELCOME
        self.current_intent = None
        self.previous_intent = None
        self.symptom_round = 0
        self.symptom_data = {}
        self.intent_deny_count = 0
        self.refusal_count = 0
        self.context_summary = ""

    def _save_profile_and_session(self):
        """将当前画像和会话记录保存到 JSON 文件"""
        try:
            from admin_service import profile_service, session_service

            # 生成用户 ID（基于会话内容哈希或使用默认）
            user_id = getattr(self, '_user_id', None)
            if not user_id:
                import hashlib
                # 使用第一条用户消息生成用户ID
                first_user_msg = ""
                for m in self.messages:
                    if m.role == "user":
                        first_user_msg = m.content[:50]
                        break
                if first_user_msg:
                    user_id = "user_" + hashlib.md5(first_user_msg.encode()).hexdigest()[:8]
                else:
                    user_id = "user_anonymous"
                self._user_id = user_id

            # 保存画像
            profile = self.user_profile.to_dict()
            profile_service.create_or_update_profile(user_id, profile)

            # 保存会话记录
            if self.messages:
                session_messages = [msg.to_dict() for msg in self.messages]
                session_service.add_session(user_id, session_messages)

        except Exception:
            pass  # 静默失败，不影响主流程

    def save_current_profile(self):
        """手动保存当前画像（供外部调用）"""
        self._save_profile_and_session()

    def start_profile_collect(self):
        """开始画像收集"""
        self.state = SessionState.PROFILE_COLLECT

    def get_welcome_message(self) -> str:
        """获取欢迎消息"""
        return "您好！我是泰小虎，您的健康顾问\n\n我可以帮您：\n• 解答健康问题\n• 推荐合适的保健品\n• 了解健康知识\n\n请问您今天想咨询什么呢？"

    def get_intent_options(self) -> List[Dict]:
        """获取意图选项"""
        return [
            {"code": "health_consult", "label": "健康咨询", "desc": "身体不舒服？我来帮您分析"},
            {"code": "product_consult", "label": "产品咨询", "desc": "想买保健品？为您推荐合适的"},
            {"code": "knowledge_query", "label": "健康知识", "desc": "想学健康知识？我来解答"},
            {"code": "other", "label": "其他", "desc": "其他问题或建议"}
        ]
