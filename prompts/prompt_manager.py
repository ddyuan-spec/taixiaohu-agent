"""
泰小虎智能体 - Prompt管理器
负责管理和渲染各模块Prompt
"""

from typing import Dict, Any, Optional
from string import Template
import json

from .system_prompts import (
    SYSTEM_PROMPT,
    ORCHESTRATOR_PROMPT,
    SAFETY_GUARD_PROMPT,
    INTENT_ROUTER_PROMPT,
    PROFILE_EXTRACTOR_PROMPT,
    SYMPTOM_COLLECTOR_PROMPT,
    RECOMMENDATION_ENGINE_PROMPT,
    PRODUCT_CONSULT_PROMPT,
    KNOWLEDGE_QA_PROMPT,
    BOUNDARY_HANDLER_PROMPT,
    CUSTOMER_SERVICE_PROMPT,
    DISCLAIMER_PROMPT,
    PROFILE_COLLECT_PROMPT,
    WELCOME_PROMPT
)


class PromptManager:
    """Prompt管理器"""
    
    def __init__(self):
        self.prompts = {
            'system': SYSTEM_PROMPT,
            'orchestrator': ORCHESTRATOR_PROMPT,
            'safety_guard': SAFETY_GUARD_PROMPT,
            'intent_router': INTENT_ROUTER_PROMPT,
            'profile_extractor': PROFILE_EXTRACTOR_PROMPT,
            'symptom_collector': SYMPTOM_COLLECTOR_PROMPT,
            'recommendation_engine': RECOMMENDATION_ENGINE_PROMPT,
            'product_consult': PRODUCT_CONSULT_PROMPT,
            'knowledge_qa': KNOWLEDGE_QA_PROMPT,
            'boundary_handler': BOUNDARY_HANDLER_PROMPT,
            'customer_service': CUSTOMER_SERVICE_PROMPT,
            'disclaimer': DISCLAIMER_PROMPT,
            'profile_collect': PROFILE_COLLECT_PROMPT,
            'welcome': WELCOME_PROMPT
        }
    
    def get_prompt(self, prompt_name: str) -> str:
        """获取指定Prompt"""
        return self.prompts.get(prompt_name, "")
    
    def render_prompt(self, prompt_name: str, variables: Dict[str, Any]) -> str:
        """
        渲染Prompt，替换变量
        
        Args:
            prompt_name: Prompt名称
            variables: 变量字典
            
        Returns:
            渲染后的Prompt
        """
        prompt_template = self.get_prompt(prompt_name)
        if not prompt_template:
            return ""
        
        try:
            template = Template(prompt_template)
            return template.safe_substitute(variables)
        except Exception as e:
            print(f"渲染Prompt失败: {e}")
            return prompt_template
    
    def render_with_context(self, prompt_name: str, context: Any) -> str:
        """
        使用对话上下文渲染Prompt
        
        Args:
            prompt_name: Prompt名称
            context: ConversationContext对象
            
        Returns:
            渲染后的Prompt
        """
        # 将上下文转换为字典
        variables = self._context_to_dict(context)
        return self.render_prompt(prompt_name, variables)
    
    def _context_to_dict(self, context: Any) -> Dict[str, Any]:
        """将上下文对象转换为字典"""
        variables = {}
        
        # 基础信息
        if hasattr(context, 'user_id'):
            variables['user_id'] = context.user_id
        if hasattr(context, 'session_id'):
            variables['session_id'] = context.session_id
        
        # 画像信息
        if hasattr(context, 'profile') and context.profile:
            profile = context.profile
            variables['age'] = profile.age
            variables['gender'] = profile.gender
            variables['chronic_diseases'] = profile.chronic_diseases
            variables['current_medication'] = profile.current_medication
            variables['allergy_history'] = profile.allergy_history
            variables['health_concerns'] = profile.health_concerns
            variables['profile_completeness'] = profile.completeness
        
        # 意图信息
        if hasattr(context, 'current_intent') and context.current_intent:
            variables['current_intent'] = context.current_intent.value
        if hasattr(context, 'previous_intent') and context.previous_intent:
            variables['previous_intent'] = context.previous_intent.value
        
        # 短期记忆
        if hasattr(context, 'short_term_memory') and context.short_term_memory:
            memory = context.short_term_memory
            variables['main_symptom'] = memory.main_symptom
            variables['duration'] = memory.duration
            variables['severity'] = memory.severity
            variables['accompany_symptoms'] = ', '.join(memory.accompany_symptoms)
        
        # 症状数据
        if hasattr(context, 'symptom_data'):
            variables['symptom_data'] = json.dumps(context.symptom_data, ensure_ascii=False)
        
        # 推荐历史
        if hasattr(context, 'recommended_products'):
            variables['recommended_count'] = len(context.recommended_products)
            variables['recommended_list'] = ', '.join([p.product_name for p in context.recommended_products])
        
        # 对话信息
        if hasattr(context, 'turn_count'):
            variables['turn_count'] = context.turn_count
        
        return variables
    
    def add_prompt(self, name: str, prompt: str):
        """添加自定义Prompt"""
        self.prompts[name] = prompt
    
    def update_prompt(self, name: str, prompt: str):
        """更新Prompt"""
        if name in self.prompts:
            self.prompts[name] = prompt
    
    def list_prompts(self) -> list:
        """列出所有Prompt名称"""
        return list(self.prompts.keys())
    
    def get_system_prompt_with_context(self, context: Any) -> str:
        """获取带上下文的System Prompt"""
        variables = self._context_to_dict(context)
        return self.render_prompt('system', variables)
    
    def build_full_prompt(self, module_name: str, user_input: str, context: Any) -> str:
        """
        构建完整的Prompt（System + Module + Context）
        
        Args:
            module_name: 模块名称
            user_input: 用户输入
            context: 对话上下文
            
        Returns:
            完整的Prompt
        """
        parts = []
        
        # System Prompt
        system_prompt = self.get_system_prompt_with_context(context)
        if system_prompt:
            parts.append(system_prompt)
        
        # Module Prompt
        module_prompt = self.get_prompt(module_name)
        if module_prompt:
            parts.append(module_prompt)
        
        # Context信息
        context_info = self._build_context_info(context)
        if context_info:
            parts.append(context_info)
        
        # 用户输入
        parts.append(f"\n## 用户输入\n{user_input}")
        
        return "\n\n---\n\n".join(parts)
    
    def _build_context_info(self, context: Any) -> str:
        """构建上下文信息字符串"""
        info_parts = ["## 对话上下文"]
        
        # 画像信息
        if hasattr(context, 'profile') and context.profile:
            profile = context.profile
            if profile.completeness > 0:
                info_parts.append(f"用户画像：年龄{profile.age}岁，性别{profile.gender}")
                if profile.chronic_diseases:
                    info_parts.append(f"慢性病：{profile.chronic_diseases}")
        
        # 当前意图
        if hasattr(context, 'current_intent') and context.current_intent:
            info_parts.append(f"当前意图：{context.current_intent.value}")
        
        # 症状信息
        if hasattr(context, 'short_term_memory') and context.short_term_memory:
            memory = context.short_term_memory
            if memory.main_symptom:
                info_parts.append(f"主要症状：{memory.main_symptom}")
            if memory.duration:
                info_parts.append(f"持续时间：{memory.duration}")
        
        # 推荐历史
        if hasattr(context, 'recommended_products') and context.recommended_products:
            products = [p.product_name for p in context.recommended_products]
            info_parts.append(f"已推荐产品：{', '.join(products)}")
        
        return "\n".join(info_parts) if len(info_parts) > 1 else ""


# 全局Prompt管理器实例
_prompt_manager = None


def get_prompt_manager() -> PromptManager:
    """获取全局Prompt管理器"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager
