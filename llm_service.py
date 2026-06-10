"""
LLM服务层 - 阿里云百炼通义千问集成
支持意图识别、对话生成、RAG知识库检索、健康建议生成
"""

import os
import json
from typing import Dict, List, Optional
import dashscope
from dashscope import Generation

# 配置API Key
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "sk-3d214c27dc5a45b796c778facd7010b4")
dashscope.api_key = DASHSCOPE_API_KEY

# 模型配置
MODEL_NAME = "qwen-plus"  # 性价比高，适合生产环境
# MODEL_NAME = "qwen-turbo"  # 速度更快，成本更低
# MODEL_NAME = "qwen-max"  # 效果最好，成本最高


class LLMService:
    """LLM服务类 - 封装通义千问API调用"""
    
    def __init__(self, model: str = MODEL_NAME):
        self.model = model
        self.api_key = DASHSCOPE_API_KEY
    
    def chat(self, messages: List[Dict], temperature: float = 0.7, max_tokens: int = 2000) -> str:
        """
        通用对话接口
        
        Args:
            messages: 消息列表，格式 [{"role": "user/assistant/system", "content": "..."}]
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成token数
            
        Returns:
            模型回复文本
        """
        try:
            response = Generation.call(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                result_format='message'
            )
            
            if response.status_code == 200:
                return response.output.choices[0].message.content
            else:
                print(f"[LLM Error] {response.code}: {response.message}")
                return None
        except Exception as e:
            print(f"[LLM Exception] {str(e)}")
            return None
    
    def recognize_intent(self, user_input: str, context: List[Dict] = None) -> Dict:
        """
        意图识别 - 判断用户意图
        
        Args:
            user_input: 用户输入
            context: 对话上下文
            
        Returns:
            意图识别结果 {"intent": "health_consult|product_recommend|greeting|...", "confidence": 0.9}
        """
        system_prompt = """你是一个健康导购助手的意图识别模块。请分析用户输入，识别其意图。

可能的意图类型：
1. health_consult - 健康咨询（描述症状、询问健康问题）
2. product_recommend - 产品推荐（询问保健品、药品推荐）
3. greeting - 问候（打招呼、问好）
4. thanks - 感谢（表示感谢）
5. goodbye - 告别（结束对话）
6. other - 其他

请以JSON格式返回：{"intent": "意图类型", "confidence": 0.0-1.0, "reason": "简短原因"}

只返回JSON，不要其他内容。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        result = self.chat(messages, temperature=0.1, max_tokens=200)
        
        if result:
            try:
                # 尝试解析JSON
                # 处理可能的markdown代码块
                if "```json" in result:
                    result = result.split("```json")[1].split("```")[0].strip()
                elif "```" in result:
                    result = result.split("```")[1].split("```")[0].strip()
                
                return json.loads(result)
            except json.JSONDecodeError:
                # 解析失败，返回默认意图
                return {"intent": "health_consult", "confidence": 0.5, "reason": "解析失败"}
        
        return {"intent": "health_consult", "confidence": 0.5, "reason": "API调用失败"}
    
    def generate_health_advice(self, symptom_info: Dict, user_profile: Dict = None) -> str:
        """
        生成健康建议
        
        Args:
            symptom_info: 症状信息 {"main_symptom": "...", "duration": "...", "severity": "...", "accompany": "..."}
            user_profile: 用户画像 {"age": ..., "gender": ..., "chronic_diseases": [...]}
            
        Returns:
            健康建议文本
        """
        system_prompt = """你是泰小虎，一个专业的健康导购助手，面向中老年用户。

你的任务是根据用户的症状信息，提供专业、易懂、贴心的健康建议。

建议要求：
1. 语言亲切、通俗易懂，适合中老年用户理解
2. 建议要具体、可操作
3. 包含生活调理、饮食建议、注意事项
4. 适时提醒就医，但不过度医疗化
5. 控制在200字以内

如果用户有慢性病史，要特别注意药物相互作用和禁忌。"""

        # 构建用户消息
        user_message = f"用户症状信息：\n"
        user_message += f"- 主诉症状：{symptom_info.get('main_symptom', '未知')}\n"
        user_message += f"- 持续时间：{symptom_info.get('duration', '未知')}\n"
        user_message += f"- 严重程度：{symptom_info.get('severity', '未知')}/10\n"
        
        if symptom_info.get('accompany'):
            user_message += f"- 伴随症状：{symptom_info.get('accompany')}\n"
        
        if user_profile:
            user_message += f"\n用户画像：\n"
            if user_profile.get('age'):
                user_message += f"- 年龄：{user_profile['age']}岁\n"
            if user_profile.get('gender'):
                user_message += f"- 性别：{user_profile['gender']}\n"
            if user_profile.get('chronic_diseases'):
                user_message += f"- 慢性病史：{', '.join(user_profile['chronic_diseases'])}\n"
        
        user_message += "\n请给出健康建议："

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        result = self.chat(messages, temperature=0.7, max_tokens=500)
        return result or "建议您注意休息，如症状持续请及时就医。"
    
    def generate_response(self, user_input: str, context: List[Dict], intent: str = None) -> str:
        """
        生成对话回复
        
        Args:
            user_input: 用户输入
            context: 对话上下文
            intent: 已识别的意图
            
        Returns:
            回复文本
        """
        system_prompt = """你是泰小虎，一个专业、亲切的健康导购助手，专门服务中老年用户。

你的特点：
1. 语言亲切、通俗易懂
2. 专业但不晦涩
3. 耐心倾听，细心解答
4. 适时推荐合适的健康产品
5. 关心用户的身体健康

回复要求：
- 控制在100字以内
- 使用简单易懂的语言
- 适当使用表情符号增加亲和力"""

        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加上下文（最近5轮）
        if context:
            for msg in context[-10:]:  # 最近5轮对话
                messages.append(msg)
        
        messages.append({"role": "user", "content": user_input})
        
        result = self.chat(messages, temperature=0.7, max_tokens=300)
        return result or "好的，我明白了。请问还有什么可以帮您的吗？"
    
    def rag_query(self, query: str, knowledge_chunks: List[Dict]) -> str:
        """
        RAG知识库检索增强生成
        
        Args:
            query: 用户问题
            knowledge_chunks: 检索到的知识切片列表 [{"title": "...", "content": "..."}]
            
        Returns:
            基于知识库的回答
        """
        if not knowledge_chunks:
            return None
        
        system_prompt = """你是泰小虎的健康知识助手。请根据提供的知识库内容回答用户问题。

要求：
1. 优先使用知识库中的信息
2. 如果知识库没有相关信息，诚实告知
3. 回答要准确、专业
4. 语言通俗易懂"""

        # 构建知识库上下文
        knowledge_context = "【知识库内容】\n"
        for i, chunk in enumerate(knowledge_chunks[:5], 1):  # 最多使用5个切片
            knowledge_context += f"\n{i}. {chunk.get('title', '未知标题')}\n"
            knowledge_context += f"   {chunk.get('content', '')[:500]}\n"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{knowledge_context}\n\n用户问题：{query}\n\n请基于知识库回答："}
        ]
        
        result = self.chat(messages, temperature=0.5, max_tokens=500)
        return result
    
    def extract_symptoms(self, user_input: str) -> Dict:
        """
        从用户输入中提取症状信息
        
        Args:
            user_input: 用户输入
            
        Returns:
            症状信息字典
        """
        system_prompt = """你是一个医疗信息提取助手。请从用户输入中提取症状相关信息。

请提取以下信息（如果存在）：
- main_symptom: 主诉症状
- duration: 持续时间
- severity: 疼痛/不适程度（1-10）
- accompany: 伴随症状
- body_part: 身体部位

以JSON格式返回：{"main_symptom": "...", "duration": "...", "severity": ..., "accompany": "...", "body_part": "..."}

如果某项信息不存在，对应值为null。只返回JSON。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        result = self.chat(messages, temperature=0.1, max_tokens=300)
        
        if result:
            try:
                if "```json" in result:
                    result = result.split("```json")[1].split("```")[0].strip()
                elif "```" in result:
                    result = result.split("```")[1].split("```")[0].strip()
                
                return json.loads(result)
            except json.JSONDecodeError:
                pass
        
        return {}


# 全局LLM服务实例
llm_service = LLMService()

# 提示词配置存储
DEFAULT_PROMPTS = {
    "intent_recognition": """你是一个健康导购助手的意图识别模块。请分析用户输入，识别其意图。

可能的意图类型：
1. health_consult - 健康咨询（描述症状、询问健康问题）
2. product_recommend - 产品推荐（询问保健品、药品推荐）
3. greeting - 问候（打招呼、问好）
4. thanks - 感谢（表示感谢）
5. goodbye - 告别（结束对话）
6. other - 其他

请以JSON格式返回：{"intent": "意图类型", "confidence": 0.0-1.0, "reason": "简短原因"}

只返回JSON，不要其他内容。""",

    "health_advice": """你是泰小虎，一个专业的健康导购助手，面向中老年用户。

你的任务是根据用户的症状信息，提供专业、易懂、贴心的健康建议。

建议要求：
1. 语言亲切、通俗易懂，适合中老年用户理解
2. 建议要具体、可操作
3. 包含生活调理、饮食建议、注意事项
4. 适时提醒就医，但不过度医疗化
5. 控制在200字以内

如果用户有慢性病史，要特别注意药物相互作用和禁忌。""",

    "dialogue_response": """你是泰小虎，一个专业、亲切的健康导购助手，专门服务中老年用户。

你的特点：
1. 语言亲切、通俗易懂
2. 专业但不晦涩
3. 耐心倾听，细心解答
4. 适时推荐合适的健康产品
5. 关心用户的身体健康

回复要求：
- 控制在100字以内
- 使用简单易懂的语言
- 适当使用表情符号增加亲和力""",

    "symptom_extraction": """你是一个医疗信息提取助手。请从用户输入中提取症状相关信息。

请提取以下信息（如果存在）：
- main_symptom: 主诉症状
- duration: 持续时间
- severity: 疼痛/不适程度（1-10）
- accompany: 伴随症状
- body_part: 身体部位

以JSON格式返回：{"main_symptom": "...", "duration": "...", "severity": ..., "accompany": "...", "body_part": "..."}

如果某项信息不存在，对应值为null。只返回JSON。""",

    "product_recommendation": """你是泰小虎的产品推荐专家。请根据用户的症状、画像和检索到的产品信息，生成个性化的产品推荐。

推荐原则：
1. 优先推荐与用户症状匹配的产品
2. 考虑用户的年龄、性别、慢性病史
3. 说明推荐理由，让用户理解为什么推荐
4. 提醒注意事项和禁忌
5. 语言亲切，像朋友推荐一样

请生成不超过200字的推荐文案。""",

    "knowledge_qa": """你是泰小虎的健康知识助手。请根据提供的知识库内容回答用户问题。

要求：
1. 优先使用知识库中的信息
2. 如果知识库没有相关信息，诚实告知
3. 回答要准确、专业
4. 语言通俗易懂"""
}


class LLMServiceWithPrompts(LLMService):
    """扩展LLM服务，支持提示词管理"""
    
    def __init__(self, model: str = MODEL_NAME):
        super().__init__(model)
        self.prompts = DEFAULT_PROMPTS.copy()
    
    def get_all_prompts(self) -> Dict[str, str]:
        """获取所有提示词"""
        return self.prompts
    
    def get_prompt(self, name: str) -> str:
        """获取指定提示词"""
        return self.prompts.get(name, "")
    
    def update_prompt(self, name: str, content: str):
        """更新提示词"""
        self.prompts[name] = content


# 全局LLM服务实例（使用带提示词管理的版本）
llm_service = LLMServiceWithPrompts()


def get_llm_service() -> LLMServiceWithPrompts:
    """获取LLM服务实例"""
    return llm_service
