"""
泰小虎智能体 - Orchestrator总控模块
负责每轮对话的决策和状态流转
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


class SessionState(Enum):
    """会话状态枚举"""
    WELCOME = "welcome"
    EMERGENCY_CHECK = "emergency_check"
    EMERGENCY = "emergency"
    INTENT_SWITCH_CHECK = "intent_switch_check"
    INTENT_CONFIRM = "intent_confirm"
    PROFILE_CHECK = "profile_check"
    PROFILE_COLLECT = "profile_collect"
    ROUTING = "routing"
    SYMPTOM_COLLECTION = "symptom_collection"
    SYMPTOM_ANALYSIS = "symptom_analysis"
    RAG_RETRIEVAL = "rag_retrieval"
    RECOMMENDATION = "recommendation"
    PRODUCT_CARD = "product_card"
    PRODUCT_CONSULT = "product_consult"
    KNOWLEDGE_QA = "knowledge_qa"
    REPURCHASE = "repurchase"
    CUSTOMER_SERVICE = "customer_service"
    BOUNDARY = "boundary"
    CONVERSATION_END = "conversation_end"


class IntentType(Enum):
    """意图类型枚举"""
    HEALTH_CONSULT = "health_consult"
    PRODUCT_CONSULT = "product_consult"
    KNOWLEDGE_QUERY = "knowledge_query"
    REPURCHASE = "repurchase"
    CUSTOMER_SERVICE = "customer_service"
    COMPLAINT = "complaint"
    PROFILE_UPDATE = "profile_update"
    OTHER = "other"


class NextAction(Enum):
    """下一步动作枚举"""
    ASK_FOLLOWUP = "ask_followup"
    RECOMMEND_PRODUCT = "recommend_product"
    PROVIDE_KNOWLEDGE = "provide_knowledge"
    COLLECT_PROFILE = "collect_profile"
    CONFIRM_INTENT = "confirm_intent"
    EMERGENCY_WARNING = "emergency_warning"
    TRANSFER_HUMAN = "transfer_human"
    END_CONVERSATION = "end_conversation"
    GENERAL_RESPONSE = "general_response"


@dataclass
class UserProfile:
    """用户画像"""
    name: str = ""
    age: int = 0
    gender: str = ""
    chronic_diseases: str = ""
    allergy_history: str = ""
    current_medication: str = ""
    health_concerns: str = ""
    completeness: float = 0.0
    
    def update_completeness(self):
        """更新完整度"""
        fields = [self.age, self.gender, self.chronic_diseases,
                  self.current_medication, self.health_concerns]
        filled = sum(1 for f in fields if f)
        self.completeness = filled / len(fields)


@dataclass
class ShortTermMemory:
    """短期记忆"""
    main_symptom: str = ""
    duration: str = ""
    severity: str = ""
    accompany_symptoms: List[str] = field(default_factory=list)
    triggers: List[str] = field(default_factory=list)
    relieving_factors: List[str] = field(default_factory=list)
    related_diseases: List[str] = field(default_factory=list)


@dataclass
class ProductRecommendation:
    """产品推荐记录"""
    product_name: str = ""
    reason: str = ""
    contraindications_checked: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    user_response: str = ""


@dataclass
class ConversationContext:
    """统一对话上下文"""
    session_id: str = ""
    user_id: str = ""
    profile: UserProfile = field(default_factory=UserProfile)
    short_term_memory: ShortTermMemory = field(default_factory=ShortTermMemory)
    current_intent: Optional[IntentType] = None
    previous_intent: Optional[IntentType] = None
    intent_history: List[Dict] = field(default_factory=list)
    symptom_data: Dict[str, Any] = field(default_factory=dict)
    question_history: List[str] = field(default_factory=list)
    conversation_history: List[Dict] = field(default_factory=list)  # 对话历史记录
    recommended_products: List[ProductRecommendation] = field(default_factory=list)
    refused_products: List[str] = field(default_factory=list)
    current_discussed_product: str = ""  # 当前讨论的产品名称
    context_summary: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    turn_count: int = 0
    last_intent_confirm: bool = False
    
    def update_intent(self, new_intent: IntentType, trigger: str = ""):
        """更新意图并记录历史"""
        if self.current_intent and new_intent != self.current_intent:
            self.previous_intent = self.current_intent
            self.intent_history.append({
                "from": self.current_intent.value,
                "to": new_intent.value,
                "trigger": trigger,
                "timestamp": datetime.now().isoformat()
            })
        self.current_intent = new_intent
        self.updated_at = datetime.now()


@dataclass
class OrchestratorDecision:
    """Orchestrator决策输出"""
    state: SessionState
    next_action: NextAction
    intent: IntentType
    intent_confidence: float = 0.0
    is_intent_switched: bool = False
    need_profile_update: bool = False
    missing_profile_fields: List[str] = field(default_factory=list)
    need_rag: bool = False
    rag_results: List[Dict] = field(default_factory=list)
    can_recommend: bool = False
    recommended_products: List[str] = field(default_factory=list)
    avoid_duplicates: List[str] = field(default_factory=list)
    response: str = ""
    need_disclaimer: bool = True
    card_type: str = ""
    is_emergency: bool = False
    emergency_level: str = ""
    should_end: bool = False


class SafetyGuard:
    """安全守卫模块 - 紧急症状检测
    
    基于症状分级标准：
    - 高危（红色预警）：生命体征不稳定或存在即刻致死风险，立即拨打120
    - 中危（黄色预警）：暂无即刻致死风险，但病情可能急剧恶化，尽快就诊（<1小时）
    """
    
    # ==================== 高危症状（红色预警）====================
    
    # 2.1 循环系统危象
    HIGH_RISK_CIRCULATION = [
        "压榨性胸痛", "胸痛伴大汗", "胸痛濒死感", "胸痛放射",
        "意识丧失", "晕厥", "突然倒地", "呼之不应",
        "心跳极快", "心率超过130", "心跳超过130",
        "心跳极慢", "心率低于40", "心跳不到40",
        "心悸伴呼吸困难", "心悸伴气促", "心悸伴面色苍白"
    ]
    
    # 2.2 呼吸与气道危象
    HIGH_RISK_RESPIRATORY = [
        "窒息", "气道梗阻", "无法说话", "无法咳嗽", "无法呼吸", "面色青紫",
        "严重呼吸困难", "静息气促", "口唇发紫", "发绀", "端坐呼吸",
        "急性喉梗阻", "声音嘶哑", "犬吠样咳嗽", "吸气性喘鸣",
        "重度哮喘", "哮喘发作", "呼吸急促", "说话困难", "血氧下降"
    ]
    
    # 2.3 神经与脑血管危象
    HIGH_RISK_NEUROLOGICAL = [
        "中风", "口角歪斜", "口眼歪斜", "单侧肢体无力", "单侧肢体麻木",
        "言语不清", "构音障碍", "说话含糊", "失语",
        "意识障碍", "嗜睡", "烦躁不安", "胡言乱语",
        "癫痫持续", "抽搐超过5分钟", "连续抽搐", "抽搐无意识恢复",
        "剧烈头痛", "雷击样头痛", "爆炸性头痛", "突发剧烈头痛"
    ]
    
    # 2.4 出血与创伤
    HIGH_RISK_HEMORRHAGE = [
        "失血性休克", "喷涌状出血", "皮肤湿冷", "脉搏细速", "意识淡漠",
        "消化道大出血", "呕血", "鲜红血", "咖啡色血", "柏油样黑便",
        "创伤性休克", "严重外伤", "大出血", "血压下降", "心率增快",
        "产科大出血", "产后大出血", "阴道大量出血"
    ]
    
    # 2.5 其他致命急症
    HIGH_RISK_OTHER = [
        "严重过敏", "全身皮疹", "喉头水肿", "过敏性休克",
        "剧烈腹痛", "刀割样疼痛", "腹部僵硬", "板状腹",
        "急性中毒", "毒物接触", "中毒昏迷", "中毒呼吸困难",
        "糖尿病急症", "意识模糊", "过度呼吸", "Kussmaul呼吸", "低血糖昏迷",
        "主动脉夹层", "内脏穿孔"
    ]
    
    # 合并所有高危症状
    HIGH_RISK_SYMPTOMS = (
        HIGH_RISK_CIRCULATION + 
        HIGH_RISK_RESPIRATORY + 
        HIGH_RISK_NEUROLOGICAL + 
        HIGH_RISK_HEMORRHAGE + 
        HIGH_RISK_OTHER
    )
    
    # ==================== 中危症状（黄色预警）====================
    
    # 3.1 高热与感染
    MEDIUM_RISK_INFECTION = [
        "持续高热", "高烧不退", "体温超过39", "烧到39度", "服用退热药无效",
        "寒战", "高热寒战", "发热寒战",
        "惊厥", "抽搐", "发热抽搐", "高热惊厥",
        "全身感染", "精神萎靡", "食欲不振", "尿量减少",
        "局部感染", "红肿热痛", "脓肿", "蜂窝织炎"
    ]
    
    # 3.2 疼痛异常
    MEDIUM_RISK_PAIN = [
        "急性腹痛", "剧烈腹痛", "阑尾炎", "肾结石", "胆囊炎",
        "关节肿痛", "单个关节红肿", "痛风", "感染性关节炎",
        "腰背疼痛", "突发腰痛", "腰痛伴血尿", "主动脉瘤",
        "胸壁疼痛", "深呼吸胸痛", "咳嗽胸痛", "肋软骨炎", "肺炎胸痛"
    ]
    
    # 3.3 感官与肢体
    MEDIUM_RISK_SENSORY = [
        "视力骤降", "突然失明", "单眼失明", "双眼失明", "视物重影",
        "听力骤降", "突然耳聋",
        "肢体功能障碍", "行走不稳", "共济失调", "肢体麻木",
        "面神经麻痹", "口角歪斜", "闭眼不全", "面神经炎",
        "肢体无力", "渐进性乏力", "影响活动"
    ]
    
    # 3.4 泌尿与消化
    MEDIUM_RISK_URINARY_GI = [
        "尿潴留", "排不出尿", "完全排不出", "下腹胀痛",
        "频繁呕吐", "频繁腹泻", "明显口干", "眼窝凹陷", "中度脱水", "重度脱水",
        "持续腹胀", "嗳气", "食欲减退", "消化不良",
        "血尿", "无痛性血尿", "肉眼血尿"
    ]
    
    # 3.5 其他症状
    MEDIUM_RISK_OTHER = [
        "皮疹伴发热", "全身皮疹", "发热皮疹", "传染性疾病",
        "出血异常", "非经期出血", "阴道出血", "咯血", "便血",
        "精神异常", "行为异常", "言语混乱", "精神疾病",
        "药物反应", "用药后皮疹", "用药后瘙痒", "用药后呼吸困难"
    ]
    
    # 合并所有中危症状
    MEDIUM_RISK_SYMPTOMS = (
        MEDIUM_RISK_INFECTION + 
        MEDIUM_RISK_PAIN + 
        MEDIUM_RISK_SENSORY + 
        MEDIUM_RISK_URINARY_GI + 
        MEDIUM_RISK_OTHER
    )
    
    def check(self, user_input: str) -> Optional[Dict]:
        """
        检查是否包含紧急症状
        
        Returns:
            Dict or None: 如果检测到紧急症状返回详情，否则返回None
        """
        user_input_lower = user_input.lower()
        detected_high_risk = []
        detected_medium_risk = []
        
        # 检查高危症状
        for symptom in self.HIGH_RISK_SYMPTOMS:
            if symptom in user_input_lower:
                detected_high_risk.append(symptom)
        
        # 如果检测到高危症状
        if detected_high_risk:
            # 根据症状类型生成更具体的回复
            response = self._generate_high_risk_response(detected_high_risk, user_input_lower)
            return {
                "is_emergency": True,
                "emergency_level": "high",
                "detected_symptoms": detected_high_risk,
                "response": response,
                "should_end": True
            }
        
        # 检查中危症状
        for symptom in self.MEDIUM_RISK_SYMPTOMS:
            if symptom in user_input_lower:
                detected_medium_risk.append(symptom)
        
        # 如果检测到中危症状
        if detected_medium_risk:
            response = self._generate_medium_risk_response(detected_medium_risk)
            return {
                "is_emergency": True,
                "emergency_level": "medium",
                "detected_symptoms": detected_medium_risk,
                "response": response,
                "should_end": False
            }
        
        return None
    
    def _generate_high_risk_response(self, symptoms: List[str], user_input: str) -> str:
        """生成高危症状回复"""
        # 根据症状类别生成针对性回复
        circulation_keywords = ["胸痛", "心跳", "心悸", "意识丧失", "晕厥"]
        respiratory_keywords = ["窒息", "呼吸困难", "喉梗阻", "哮喘"]
        neurological_keywords = ["中风", "抽搐", "癫痫", "头痛", "意识障碍"]
        hemorrhage_keywords = ["出血", "呕血", "便血", "休克"]
        
        # 检查是否匹配特定类别
        has_circulation = any(kw in user_input for kw in circulation_keywords)
        has_respiratory = any(kw in user_input for kw in respiratory_keywords)
        has_neurological = any(kw in user_input for kw in neurological_keywords)
        has_hemorrhage = any(kw in user_input for kw in hemorrhage_keywords)
        
        base_response = "【紧急提醒】您描述的症状可能存在严重健康风险！"
        
        if has_circulation:
            base_response += "\n\n【心脏/循环问题】可能是急性心梗、严重心律失常等，"
        elif has_respiratory:
            base_response += "\n\n【呼吸问题】可能是气道梗阻、重度哮喘等，"
        elif has_neurological:
            base_response += "\n\n【神经问题】可能是中风、脑出血等，"
        elif has_hemorrhage:
            base_response += "\n\n【出血问题】可能是失血性休克等，"
        
        base_response += "\n\n请您【立即拨打120急救电话】，或让家人马上送您去最近的医院急诊科！"
        base_response += "\n\n在等待救援期间："
        base_response += "\n• 保持冷静，不要慌张"
        base_response += "\n• 停止一切活动，保持安静"
        base_response += "\n• 如果有家人在场，请让他们陪同"
        base_response += "\n• 准备好身份证、医保卡"
        
        return base_response
    
    def _generate_medium_risk_response(self, symptoms: List[str]) -> str:
        """生成中危症状回复"""
        base_response = "【重要提醒】您描述的症状需要引起重视！"
        base_response += "\n\n建议您【尽快到医院急诊科就诊】（最好在1小时内），排除潜在风险。"
        base_response += "\n\n在就医前请注意："
        base_response += "\n• 避免剧烈活动，保持休息"
        base_response += "\n• 记录症状出现的时间和变化"
        base_response += "\n• 如果症状加重，请立即拨打120"
        base_response += "\n\n如需帮助，我也可以帮您转接人工客服。"
        
        return base_response


class IntentRouter:
    """意图路由模块 - 意图识别与切换检测"""
    
    # 意图切换关键词模式
    SWITCH_PATTERNS = {
        IntentType.PRODUCT_CONSULT: [
            r"对了.*产品", r"对了.*怎么样", r"对了.*多少钱", r"对了.*推荐",
            r"那.*产品", r"那.*推荐", r"那.*钙片", r"那.*鱼油", r"那.*维生素",
            r"给我推荐", r"有什么产品", r"买什么", r"哪个好",
            r"多少钱", r"价格", r"怎么买", r"有.*吗",
            r"我想买", r"给我.*买", r"一起发过来", r"还想买",
            r"泰吉眠", r"泰美畅", r"适合什么人", r"多少钱一瓶"
        ],
        IntentType.HEALTH_CONSULT: [
            r"其实.*", r"对了.*不舒服", r"对了.*疼", r"对了.*痛",
            r"我.*症状", r"我.*不舒服", r"我.*疼", r"我.*痛", r"我.*难受",
            r"是不是.*病", r"是不是.*问题", r"怎么回事",
            r"你先帮我看看", r"帮我看看", r"还是疼", r"还是.*不舒服",
            r"胸痛", r"胸闷", r"头疼", r"头晕", r"失眠", r"睡不着",
            r"已经.*", r"持续.*", r"有一段时间", r"有一阵子了",  # 回答症状持续时间
            r"多久了", r"几天了", r"多长时间", r"多久",  # 询问持续时间
            r"每次.*都", r"经常.*疼", r"经常.*不舒服"  # 描述症状频率
        ],
        IntentType.KNOWLEDGE_QUERY: [
            r"为什么", r"什么原因", r"怎么回事", r"有什么作用",
            r"有什么好处", r"有什么用", r"是什么", r"有什么区别",
            r"想先了解", r"了解一下", r"什么造成的"
        ],
        IntentType.COMPLAINT: [
            r"投诉", r"差评", r"退货", r"退款", r"质量.*问题", r"发货.*慢",
            r"APP.*闪退", r"闪退", r"不好用", r"有问题"
        ],
        IntentType.CUSTOMER_SERVICE: [
            r"找人工", r"人工客服", r"转人工", r"客服", r"人工"
        ],
        IntentType.REPURCHASE: [
            r"复购", r"再买", r"还要.*", r"还要买", r"之前.*买", r"上次.*买",
            r"吃完了", r"用完了", r"快用完"
        ]
    }
    
    # 意图确认关键词
    INTENT_CONFIRM_PATTERNS = {
        IntentType.HEALTH_CONSULT: ["不舒服", "疼", "痛", "症状", "病", "难受", "感觉"],
        IntentType.PRODUCT_CONSULT: ["产品", "买", "多少钱", "价格", "推荐", "功效", "适合"],
        IntentType.KNOWLEDGE_QUERY: ["为什么", "是什么", "怎么", "知识", "作用", "好处"]
    }
    
    def detect_switch(self, user_input: str, current_intent: Optional[IntentType]) -> Optional[IntentType]:
        """
        检测意图切换
        
        Returns:
            IntentType or None: 如果检测到切换返回新意图，否则返回None
        """
        user_input_lower = user_input.lower()
        
        # 优先检查是否应该切换到健康咨询（症状关键词优先）
        symptom_keywords = [
            "疼", "痛", "不舒服", "症状", "难受", "头晕",
            "失眠", "睡不着", "睡不好", "睡眠", "睡眠不好",
            "疲劳", "乏力", "没精神", "疲倦",
            "焦虑", "心慌", "紧张",
            "便秘", "消化", "胃",
            "血压高", "血糖高", "血脂高"
        ]
        if any(kw in user_input for kw in symptom_keywords) and current_intent != IntentType.HEALTH_CONSULT:
            return IntentType.HEALTH_CONSULT
        
        # 检查切换模式
        for intent_type, patterns in self.SWITCH_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, user_input_lower):
                    # 如果检测到不同意图，返回新意图
                    if intent_type != current_intent:
                        return intent_type
        
        # 检查当前意图是否仍然有效
        if current_intent:
            is_valid = self._validate_current_intent(user_input_lower, current_intent)
            if not is_valid:
                # 当前意图不再有效，尝试检测新意图
                new_intent = self._auto_detect_intent(user_input_lower)
                if new_intent and new_intent != current_intent:
                    return new_intent
        
        return None
    
    def _validate_current_intent(self, user_input: str, current_intent: IntentType) -> bool:
        """验证当前意图是否仍然有效"""
        if current_intent == IntentType.HEALTH_CONSULT:
            # 症状关键词
            health_keywords = ["疼", "痛", "不舒服", "症状", "病", "难受", "感觉"]
            # 症状持续时间描述（回答追问）
            duration_keywords = ["已经", "持续", "有一段时间", "有一阵子", "多久了", "几天了", "多长时间"]
            # 症状频率描述
            frequency_keywords = ["每次", "经常", "有时候", "偶尔", "总是", "一直"]
            # 改善建议请求（保持健康咨询意图）
            improvement_keywords = ["改善", "缓解", "解决", "治疗方法", "怎么调理", "如何治疗", "办法"]
            
            has_symptom = any(kw in user_input for kw in health_keywords)
            has_duration = any(kw in user_input for kw in duration_keywords)
            has_frequency = any(kw in user_input for kw in frequency_keywords)
            has_improvement = any(kw in user_input for kw in improvement_keywords)
            
            return has_symptom or has_duration or has_frequency or has_improvement
        
        elif current_intent == IntentType.PRODUCT_CONSULT:
            product_keywords = ["产品", "买", "多少钱", "价格", "推荐", "功效", "适合"]
            return any(kw in user_input for kw in product_keywords)
        
        elif current_intent == IntentType.KNOWLEDGE_QUERY:
            knowledge_keywords = ["为什么", "是什么", "怎么", "知识", "作用"]
            return any(kw in user_input for kw in knowledge_keywords)
        
        return True
    
    def _auto_detect_intent(self, user_input: str) -> Optional[IntentType]:
        """自动检测意图"""
        # 健康咨询关键词（优先匹配症状）
        health_keywords = [
            "疼", "痛", "不舒服", "症状", "病", "难受", "头晕",
            "失眠", "睡不着", "睡不好", "睡眠", "睡眠不好",
            "疲劳", "乏力", "没精神", "疲倦",
            "焦虑", "心慌", "紧张",
            "便秘", "消化", "胃",
            "血压高", "血糖高", "血脂高"
        ]
        if any(kw in user_input for kw in health_keywords):
            return IntentType.HEALTH_CONSULT
        
        # 产品咨询关键词（包含产品名称）
        product_keywords = [
            "产品", "买", "多少钱", "价格", "推荐", "功效", "适合什么人",
            "泰吉眠", "泰美畅", "智忆高", "安美来",  # 产品名称
            "益生菌", "胶原蛋白", "磷脂酰丝氨酸", "茶氨酸"  # 成分/产品类型
        ]
        if any(kw in user_input for kw in product_keywords):
            return IntentType.PRODUCT_CONSULT
        
        # 知识查询关键词
        knowledge_keywords = ["为什么", "是什么", "怎么", "知识"]
        if any(kw in user_input for kw in knowledge_keywords):
            return IntentType.KNOWLEDGE_QUERY
        
        return IntentType.OTHER


class ProfileExtractor:
    """画像抽取模块 - 从自然语言中抽取画像信息"""
    
    # 年龄提取模式
    AGE_PATTERNS = [
        r'(\d+)\s*岁',
        r'(\d+)\s*周岁',
        r'今年\s*(\d+)',
        r'(\d+)\s*多了',
        r'(\d+)\s*出头'
    ]
    
    # 性别提取模式
    GENDER_PATTERNS = {
        '男': [r'男', r'先生', r'大爷', r'叔叔', r'男士'],
        '女': [r'女', r'女士', r'阿姨', r'大妈', r'奶奶']
    }
    
    # 慢性病关键词
    CHRONIC_DISEASES = [
        "高血压", "糖尿病", "高血糖", "心脏病", "冠心病", "心绞痛",
        "高血脂", "脂肪肝", "痛风", "关节炎", "骨质疏松", "哮喘",
        "慢性支气管炎", "胃病", "胃炎", "胃溃疡", "肾病", "肝病",
        "甲状腺", "甲亢", "甲减", "贫血", "抑郁症", "焦虑症"
    ]
    
    def extract(self, user_input: str, current_profile: UserProfile) -> Dict:
        """
        从用户输入中抽取画像信息
        
        Returns:
            Dict: 抽取结果
        """
        extracted = {}
        
        # 提取年龄
        age = self._extract_age(user_input)
        if age and not current_profile.age:
            extracted['age'] = age
        
        # 提取性别
        gender = self._extract_gender(user_input)
        if gender and not current_profile.gender:
            extracted['gender'] = gender
        
        # 提取慢性病
        diseases = self._extract_chronic_diseases(user_input)
        if diseases and not current_profile.chronic_diseases:
            extracted['chronic_diseases'] = diseases
        
        # 提取用药
        medication = self._extract_medication(user_input)
        if medication and not current_profile.current_medication:
            extracted['current_medication'] = medication
        
        # 计算缺失字段
        all_fields = ['age', 'gender', 'chronic_diseases', 'current_medication', 'health_concerns']
        missing = [f for f in all_fields if not getattr(current_profile, f) and f not in extracted]
        
        # 计算完整度
        filled_count = sum(1 for f in all_fields if getattr(current_profile, f) or f in extracted)
        completeness = filled_count / len(all_fields)
        
        return {
            "extracted_fields": extracted,
            "missing_fields": missing,
            "completeness": completeness,
            "need_ask": completeness < 0.6 and len(missing) > 0
        }
    
    def _extract_age(self, user_input: str) -> Optional[int]:
        """提取年龄"""
        for pattern in self.AGE_PATTERNS:
            match = re.search(pattern, user_input)
            if match:
                age = int(match.group(1))
                if 18 <= age <= 120:
                    return age
        return None
    
    def _extract_gender(self, user_input: str) -> Optional[str]:
        """提取性别"""
        for gender, patterns in self.GENDER_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, user_input):
                    return gender
        return None
    
    def _extract_chronic_diseases(self, user_input: str) -> Optional[str]:
        """提取慢性病"""
        found = []
        for disease in self.CHRONIC_DISEASES:
            if disease in user_input:
                found.append(disease)
        return "、".join(found) if found else None
    
    def _extract_medication(self, user_input: str) -> Optional[str]:
        """提取用药信息"""
        # 简单的用药提取模式
        patterns = [
            r'吃(着)?(.+?)(药|片|胶囊|颗粒)',
            r'服用(.+?)(药|片|胶囊|颗粒)',
            r'在吃(.+)',
            r'吃着(.+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, user_input)
            if match:
                return match.group(2) if match.lastindex >= 2 else match.group(1)
        return None


class Orchestrator:
    """
    Orchestrator总控器
    负责每轮对话的决策和状态流转
    """
    
    def __init__(self):
        self.safety_guard = SafetyGuard()
        self.intent_router = IntentRouter()
        self.profile_extractor = ProfileExtractor()
    
    def decide(self, user_input: str, context: ConversationContext) -> OrchestratorDecision:
        """
        核心决策流程
        
        Args:
            user_input: 用户输入
            context: 对话上下文
            
        Returns:
            OrchestratorDecision: 决策结果
        """
        # 更新轮数
        context.turn_count += 1
        
        # Step 1: 紧急症状检测（最高优先级）
        emergency = self.safety_guard.check(user_input)
        if emergency:
            return OrchestratorDecision(
                state=SessionState.EMERGENCY,
                next_action=NextAction.EMERGENCY_WARNING,
                intent=IntentType.HEALTH_CONSULT,
                is_emergency=True,
                emergency_level=emergency["emergency_level"],
                response=emergency["response"],
                should_end=emergency["should_end"]
            )
        
        # Step 1b: 症状提取（无论意图如何，先提取症状）
        self._extract_symptom(user_input, context)
        
        # Step 2: 推荐请求/拒绝检测（在意图切换之前，优先处理）
        is_recommend_request = False
        is_refuse_recommend = False
        if context.current_intent == IntentType.HEALTH_CONSULT:
            recommend_keywords = ["推荐", "有什么产品", "买什么", "哪个好", "试试", "给我介绍", "有什么适合"]
            refuse_keywords = ["不想买", "不需要", "先不买", "不想产品", "不买", "不要产品", "先不考虑", "只想要建议", "有其他方法"]
            if any(kw in user_input for kw in refuse_keywords):
                is_refuse_recommend = True
            elif any(kw in user_input for kw in recommend_keywords):
                is_recommend_request = True
        
        # Step 2b: 意图切换检测（推荐请求和拒绝时不切换）
        switched_intent = None
        if not is_recommend_request and not is_refuse_recommend:
            switched_intent = self.intent_router.detect_switch(user_input, context.current_intent)
        
        if switched_intent:
            # 自动切换意图（根据业务规则）
            context.update_intent(switched_intent, trigger="auto_detect")
            return self._route_by_intent(user_input, context, is_switch=True)
        
        # Step 3: 画像抽取
        profile_result = self.profile_extractor.extract(user_input, context.profile)
        if profile_result["extracted_fields"]:
            # 更新画像
            for field, value in profile_result["extracted_fields"].items():
                setattr(context.profile, field, value)
            context.profile.update_completeness()
        
        # Step 3b: 症状提取（健康咨询意图下）
        if context.current_intent == IntentType.HEALTH_CONSULT:
            self._extract_symptom(user_input, context)
        
        # Step 4: 画像完整性检查（推荐请求和拒绝推荐时跳过画像收集）
        if profile_result["need_ask"] and context.current_intent == IntentType.HEALTH_CONSULT:
            # 渐进式收集：不是强制，可以延迟
            # 但如果用户主动要求推荐或拒绝推荐，跳过画像收集
            if not is_recommend_request and not is_refuse_recommend and context.turn_count <= 3:  # 前3轮尝试收集
                return OrchestratorDecision(
                    state=SessionState.PROFILE_COLLECT,
                    next_action=NextAction.COLLECT_PROFILE,
                    intent=context.current_intent or IntentType.HEALTH_CONSULT,
                    need_profile_update=True,
                    missing_profile_fields=profile_result["missing_fields"],
                    response=self._generate_profile_question(profile_result["missing_fields"])
                )
        
        # Step 5: 如果没有当前意图，尝试自动检测
        if not context.current_intent:
            auto_intent = self.intent_router._auto_detect_intent(user_input)
            if auto_intent:
                context.update_intent(auto_intent, trigger="auto_detect")
                # 如果是健康咨询，提取症状
                if auto_intent == IntentType.HEALTH_CONSULT:
                    self._extract_symptom(user_input, context)
                return self._route_by_intent(user_input, context)
        
        # Step 6: 根据当前意图路由
        if context.current_intent:
            # 如果在健康咨询中用户主动要求推荐，触发产品推荐
            if is_recommend_request and context.current_intent == IntentType.HEALTH_CONSULT:
                return OrchestratorDecision(
                    state=SessionState.RECOMMENDATION,
                    next_action=NextAction.RECOMMEND_PRODUCT,
                    intent=IntentType.HEALTH_CONSULT,
                    need_rag=True,
                    response=""  # 由产品推荐模块生成
                )
            # 如果在健康咨询中用户拒绝产品推荐，给出健康建议
            if is_refuse_recommend and context.current_intent == IntentType.HEALTH_CONSULT:
                return OrchestratorDecision(
                    state=SessionState.SYMPTOM_COLLECTION,
                    next_action=NextAction.GENERAL_RESPONSE,
                    intent=IntentType.HEALTH_CONSULT,
                    response=""  # 由LLM生成健康建议
                )
            return self._route_by_intent(user_input, context)
        
        # 默认处理
        return OrchestratorDecision(
            state=SessionState.WELCOME,
            next_action=NextAction.GENERAL_RESPONSE,
            intent=IntentType.OTHER,
            response="您好！我是泰小虎，您的健康顾问。请问有什么可以帮到您的？"
        )
    
    def _extract_symptom(self, user_input: str, context: ConversationContext):
        """从用户输入中提取症状信息"""
        print(f"[DEBUG] _extract_symptom called with: {user_input}")
        # 常见症状关键词（注意：疾病名称如高血压、糖尿病不应作为症状）
        symptom_keywords = {
            "失眠": ["失眠", "睡不着", "睡不好", "睡眠不好", "入睡困难", "睡眠不太好", "睡不好觉", "觉少", "睡眠差"],
            "头痛": ["头疼", "头痛", "头胀", "头部不适", "头昏"],
            "胃痛": ["胃疼", "胃痛", "胃胀", "胃不舒服", "消化不良", "肠胃不适"],
            "便秘": ["便秘", "排便困难", "大便不通", "排便不畅"],
            "感冒": ["感冒", "发烧", "咳嗽", "流鼻涕", "鼻塞", "嗓子疼"],
            "疲劳": ["疲劳", "乏力", "没精神", "疲倦", "累", "没力气"],
            "焦虑": ["焦虑", "焦虑不安", "心慌", "紧张", "压力大", "烦躁"],
            "记忆力差": ["记忆力", "记性", "忘事", "健忘", "记不住"],
        }
        
        # 如果已经有主症状，且当前输入没有新的症状关键词，不覆盖
        existing_symptom = context.short_term_memory.main_symptom if context.short_term_memory else None
        
        # 提取症状
        for symptom, keywords in symptom_keywords.items():
            if any(kw in user_input for kw in keywords):
                # 只有当没有已存在的症状，或者新症状与已存在症状不同时，才更新
                if not existing_symptom or (symptom != existing_symptom and existing_symptom not in ["高血压", "糖尿病"]):
                    context.short_term_memory.main_symptom = symptom
                    print(f"[DEBUG] Extracted symptom: {symptom}")
                break
    
    def _route_by_intent(self, user_input: str, context: ConversationContext, is_switch: bool = False) -> OrchestratorDecision:
        """根据意图路由到对应处理模块"""
        intent = context.current_intent
        
        if intent == IntentType.HEALTH_CONSULT:
            return OrchestratorDecision(
                state=SessionState.SYMPTOM_COLLECTION,
                next_action=NextAction.ASK_FOLLOWUP,
                intent=intent,
                need_rag=True,
                response="您好！请问哪里不舒服？能详细说说吗？"
            )
        
        elif intent == IntentType.PRODUCT_CONSULT:
            return OrchestratorDecision(
                state=SessionState.PRODUCT_CONSULT,
                next_action=NextAction.PROVIDE_KNOWLEDGE,
                intent=intent,
                need_rag=True,
                response=""  # 由产品咨询模块生成
            )
        
        elif intent == IntentType.KNOWLEDGE_QUERY:
            return OrchestratorDecision(
                state=SessionState.KNOWLEDGE_QA,
                next_action=NextAction.PROVIDE_KNOWLEDGE,
                intent=intent,
                need_rag=True,
                response=""  # 由知识问答模块生成
            )
        
        elif intent == IntentType.REPURCHASE:
            return OrchestratorDecision(
                state=SessionState.REPURCHASE,
                next_action=NextAction.RECOMMEND_PRODUCT,
                intent=intent,
                response="您好！请问是想复购之前的产品吗？"
            )
        
        elif intent == IntentType.CUSTOMER_SERVICE:
            return OrchestratorDecision(
                state=SessionState.CUSTOMER_SERVICE,
                next_action=NextAction.TRANSFER_HUMAN,
                intent=intent,
                response="好的，我帮您转接人工客服，请稍等~"
            )
        
        elif intent == IntentType.COMPLAINT:
            return OrchestratorDecision(
                state=SessionState.BOUNDARY,
                next_action=NextAction.TRANSFER_HUMAN,
                intent=intent,
                response="非常抱歉给您带来不好的体验。我已经记录下来了，会尽快处理。"
            )
        
        else:
            return OrchestratorDecision(
                state=SessionState.BOUNDARY,
                next_action=NextAction.GENERAL_RESPONSE,
                intent=IntentType.OTHER,
                response="您好！我是泰小虎，您的健康顾问。请问有什么可以帮到您的？"
            )
    
    def _generate_profile_question(self, missing_fields: List[str]) -> str:
        """生成画像收集问题"""
        field_questions = {
            'age': '请问您今年多大年纪了？',
            'gender': '请问您是男士还是女士？',
            'chronic_diseases': '请问您平时有什么慢性病吗？比如高血压、糖尿病等。',
            'current_medication': '请问您目前在服用什么药物吗？',
            'health_concerns': '请问您最关心的健康问题是什么？'
        }
        
        if missing_fields:
            # 优先问年龄和性别
            priority_fields = ['age', 'gender', 'chronic_diseases']
            for field in priority_fields:
                if field in missing_fields:
                    return field_questions[field]
            # 问其他字段
            return field_questions[missing_fields[0]]
        
        return ""


# 便捷函数
def create_orchestrator() -> Orchestrator:
    """创建Orchestrator实例"""
    return Orchestrator()


def create_context(user_id: str = "", session_id: str = "") -> ConversationContext:
    """创建对话上下文"""
    return ConversationContext(
        user_id=user_id,
        session_id=session_id or datetime.now().strftime("%Y%m%d%H%M%S")
    )
