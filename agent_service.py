"""
泰小虎智能体 - 核心服务
整合Orchestrator、Product Retriever、Prompt管理器和LLM服务
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from orchestrator import (
    Orchestrator, ConversationContext, IntentType,
    NextAction, create_context, SessionState
)
from product_retriever import ProductRetriever, create_product_retriever
from prompts import PromptManager, get_prompt_manager
from adapters.llm_adapter import LLMAdapter, LLMResponse
from conversation_logger import (
    get_conversation_logger, KnowledgeBaseCall, LLMCall
)
import time


class AgentService:
    """
    泰小虎智能体核心服务
    整合所有模块，提供统一的对话接口
    支持百炼LLM调用
    """
    
    def __init__(self):
        """初始化智能体服务"""
        self.orchestrator = Orchestrator()
        self.product_retriever = create_product_retriever()
        self.prompt_manager = get_prompt_manager()
        self.llm_adapter = LLMAdapter()
        self.conversation_logger = get_conversation_logger()
        
        # 会话存储（生产环境应使用Redis或数据库）
        self.sessions: Dict[str, ConversationContext] = {}
        
        # 当前请求中累积的调用记录（实例变量，每轮请求独立）
        self._current_llm_calls: List[Dict] = []
        self._current_kb_calls: List[Dict] = []
    
    def get_or_create_context(self, session_id: str, user_id: str = "") -> ConversationContext:
        """获取或创建对话上下文"""
        if session_id not in self.sessions:
            context = create_context(user_id, session_id)
            self.sessions[session_id] = context
        return self.sessions[session_id]
    
    def _build_llm_messages(self, module_name: str, user_input: str, context: ConversationContext, 
                           additional_knowledge: str = None) -> List[Dict]:
        """
        构建LLM调用消息
        
        Args:
            module_name: 模块名称（对应Prompt模板）
            user_input: 用户输入
            context: 对话上下文
            additional_knowledge: 额外的知识库内容
            
        Returns:
            消息列表
        """
        messages = []
        
        # System Prompt（角色设定）
        system_prompt = self.prompt_manager.get_prompt('system')
        messages.append({"role": "system", "content": system_prompt})
        
        # 模块Prompt（任务说明）
        module_prompt = self.prompt_manager.get_prompt(module_name)
        if module_prompt:
            messages.append({"role": "system", "content": module_prompt})
        
        # 额外知识库内容（如果有）
        if additional_knowledge:
            knowledge_prompt = f"\n## 知识库信息（优先参考）\n{additional_knowledge}"
            messages.append({"role": "system", "content": knowledge_prompt})
        
        # 对话上下文
        context_info = self._build_context_for_llm(context)
        if context_info:
            messages.append({"role": "system", "content": context_info})
        
        # 近期对话历史（最近3轮）
        history = context.conversation_history[-6:] if context.conversation_history else []
        for msg in history:
            role = "assistant" if msg.get("is_agent") else "user"
            messages.append({"role": role, "content": msg.get("content", "")})
        
        # 用户输入
        messages.append({"role": "user", "content": user_input})
        
        return messages
    
    def _build_context_for_llm(self, context: ConversationContext) -> str:
        """构建LLM上下文信息"""
        parts = ["## 当前会话信息"]
        
        # 用户画像
        if context.profile and context.profile.completeness > 0:
            profile_info = []
            if context.profile.age:
                profile_info.append(f"年龄：{context.profile.age}岁")
            if context.profile.gender:
                profile_info.append(f"性别：{context.profile.gender}")
            if context.profile.chronic_diseases:
                profile_info.append(f"慢性病：{context.profile.chronic_diseases}")
            if context.profile.current_medication:
                profile_info.append(f"当前用药：{context.profile.current_medication}")
            
            if profile_info:
                parts.append("用户画像：" + "，".join(profile_info))
        
        # 当前意图
        if context.current_intent:
            parts.append(f"当前意图：{context.current_intent.value}")
        
        # 症状信息
        if context.short_term_memory and context.short_term_memory.main_symptom:
            parts.append(f"主要症状：{context.short_term_memory.main_symptom}")
            if context.short_term_memory.duration:
                parts.append(f"持续时间：{context.short_term_memory.duration}")
            if context.short_term_memory.severity:
                parts.append(f"严重程度：{context.short_term_memory.severity}/10")
        
        # 已推荐产品
        if context.recommended_products:
            products = [p.product_name for p in context.recommended_products[-3:]]
            parts.append(f"已推荐产品：{', '.join(products)}")
        
        return "\n".join(parts) if len(parts) > 1 else ""
    
    # LLM断开时的固定回复
    LLM_DISCONNECTED_MESSAGE = "LLM已断开请稍后重试"
    
    def _call_llm(self, messages: List[Dict], temperature: float = 0.7, 
                  max_tokens: int = 500, module: str = "unknown", 
                  session_id: str = None) -> str:
        """
        调用LLM生成回复
        
        Returns:
            LLM回复文本，失败返回固定提示
        """
        if not self.llm_adapter.is_enabled:
            self._current_llm_calls.append({
                'module': module, 'prompt_tokens': 0, 'completion_tokens': 0,
                'total_tokens': 0, 'response_time_ms': 0, 'success': False,
                'error_message': 'LLM未启用'
            })
            return self.LLM_DISCONNECTED_MESSAGE
        
        start_time = time.time()
        response = self.llm_adapter.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # 提取usage信息
        usage = response.usage if response.success else {}
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        total_tokens = usage.get('total_tokens', 0)
        
        # 累积LLM调用记录（稍后在log_agent_response中传入）
        self._current_llm_calls.append({
            'module': module,
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': total_tokens,
            'response_time_ms': response_time_ms,
            'success': response.success,
            'error_message': response.error if not response.success else ""
        })
        
        if response.success:
            return response.content
        else:
            print(f"[LLM调用失败] {response.error}")
            return self.LLM_DISCONNECTED_MESSAGE
    
    def _generate_llm_response(self, module_name: str, user_input: str, 
                               context: ConversationContext, 
                               additional_knowledge: str = None,
                               temperature: float = 0.7,
                               max_tokens: int = 500,
                               session_id: str = None) -> Optional[str]:
        """
        使用LLM生成回复
        
        Args:
            module_name: 模块名称
            user_input: 用户输入
            context: 对话上下文
            additional_knowledge: 额外知识
            temperature: 温度
            max_tokens: 最大token数
            session_id: 会话ID
            
        Returns:
            生成的回复，失败返回None
        """
        messages = self._build_llm_messages(module_name, user_input, context, additional_knowledge)
        return self._call_llm(messages, temperature, max_tokens, module=module_name, session_id=session_id)
    
    def process_message(self, user_input: str, session_id: str, user_id: str = "") -> Dict[str, Any]:
        """
        处理用户消息
        
        Args:
            user_input: 用户输入
            session_id: 会话ID
            user_id: 用户ID
            
        Returns:
            Dict: 包含回复、状态、推荐产品等信息
        """
        # 获取或创建上下文
        context = self.get_or_create_context(session_id, user_id)
        
        # 清空本轮调用记录
        self._current_llm_calls = []
        self._current_kb_calls = []
        
        print(f"[DEBUG] process_message self id: {id(self)}, _current_kb_calls id: {id(self._current_kb_calls)}")
        
        # 记录用户消息到对话日志
        self.conversation_logger.log_user_message(session_id, user_input, user_id)
        
        # 记录知识库调用开始时间
        kb_start_time = time.time()
        
        # 1. Orchestrator决策
        decision = self.orchestrator.decide(user_input, context)
        
        # 2. 根据决策执行相应动作
        response_data = {
            "session_id": session_id,
            "state": decision.state.value,
            "intent": decision.intent.value,
            "next_action": decision.next_action.value,
            "is_emergency": decision.is_emergency,
            "should_end": decision.should_end,
            "response": "",
            "recommended_products": [],
            "context_summary": {}
        }
        
        # 紧急症状处理
        if decision.is_emergency:
            response_data["response"] = decision.response
            response_data["emergency_level"] = decision.emergency_level
            # 记录紧急回复到对话日志
            self.conversation_logger.log_agent_response(
                session_id=session_id,
                content=response_data["response"],
                intent=decision.intent.value,
                state=decision.state.value
            )
            return response_data
        
        # 根据next_action生成回复
        if decision.next_action == NextAction.COLLECT_PROFILE:
            response_data["response"] = decision.response
            response_data["missing_fields"] = decision.missing_profile_fields
            
        elif decision.next_action == NextAction.ASK_FOLLOWUP:
            # 症状收集阶段
            if context.current_intent == IntentType.HEALTH_CONSULT:
                response_data["response"] = self._generate_symptom_followup(context)
            else:
                # 使用LLM生成，失败时返回固定提示
                response_data["response"] = self._generate_llm_response(
                    'symptom_collector', user_input, context,
                    temperature=0.7, max_tokens=200, session_id=session_id
                )
                
        elif decision.next_action == NextAction.RECOMMEND_PRODUCT:
            # 产品推荐 - 优先使用LLM
            print(f"[DEBUG] Before _generate_product_recommendation: _current_kb_calls={self._current_kb_calls}")
            recommendation = self._generate_product_recommendation(user_input, context, session_id)
            print(f"[DEBUG] After _generate_product_recommendation: _current_kb_calls={self._current_kb_calls}")
            response_data["response"] = recommendation["response"]
            response_data["recommended_products"] = recommendation.get("recommended_products", [])
            
        elif decision.next_action == NextAction.PROVIDE_KNOWLEDGE:
            # 知识查询或产品咨询
            if context.current_intent == IntentType.PRODUCT_CONSULT:
                response_data["response"] = self._handle_product_consult(user_input, context, session_id)
            else:
                response_data["response"] = self._handle_knowledge_query(user_input, context, session_id)
                
        elif decision.next_action == NextAction.TRANSFER_HUMAN:
            response_data["response"] = decision.response
            
        elif decision.next_action == NextAction.GENERAL_RESPONSE:
            # 通用回复 - 使用LLM，失败时返回固定提示
            response_data["response"] = self._generate_llm_response(
                'boundary_handler', user_input, context,
                temperature=0.8, max_tokens=300, session_id=session_id
            )
        
        else:
            response_data["response"] = decision.response or "您好！我是泰小虎，有什么可以帮您的吗？"
        
        # 记录对话历史
        context.conversation_history.append({
            "content": user_input,
            "is_agent": False,
            "timestamp": datetime.now().isoformat()
        })
        context.conversation_history.append({
            "content": response_data["response"],
            "is_agent": True,
            "timestamp": datetime.now().isoformat()
        })
        context.turn_count += 1
        
        # 记录AI回复到对话日志（包含LLM调用记录和知识库调用记录）
        print(f"[DEBUG] _current_kb_calls before log: {self._current_kb_calls}")
        llm_calls_to_log = []
        for call in self._current_llm_calls:
            llm_calls_to_log.append(LLMCall(
                module=call['module'],
                prompt_tokens=call['prompt_tokens'],
                completion_tokens=call['completion_tokens'],
                total_tokens=call['total_tokens'],
                response_time_ms=call['response_time_ms'],
                success=call['success'],
                error_message=call.get('error_message', '')
            ))
        
        kb_calls_to_log = []
        for call in self._current_kb_calls:
            kb_calls_to_log.append(KnowledgeBaseCall(
                query=call['query'],
                intent=call['intent'],
                results_count=call['results_count'],
                product_ids=call['product_ids'],
                response_time_ms=call['response_time_ms']
            ))
        
        self.conversation_logger.log_agent_response(
            session_id=session_id,
            content=response_data["response"],
            intent=decision.intent.value,
            intent_confidence=getattr(decision, 'intent_confidence', 0.0),
            state=decision.state.value,
            recommended_products=[p.get('product_name', p.get('product_id', '')) 
                                 for p in response_data.get("recommended_products", [])],
            llm_calls=llm_calls_to_log,
            knowledge_base_calls=kb_calls_to_log
        )
        
        # 添加上下文摘要
        response_data["context_summary"] = {
            "turn_count": context.turn_count,
            "profile_completeness": context.profile.completeness,
            "current_intent": context.current_intent.value if context.current_intent else None,
            "main_symptom": context.short_term_memory.main_symptom if context.short_term_memory else None
        }
        
        return response_data
    
    def _generate_symptom_followup(self, context: ConversationContext) -> str:
        """生成症状收集追问"""
        # 根据已收集的信息决定追问内容
        memory = context.short_term_memory
        
        if not memory.main_symptom:
            return "您好！请问哪里不舒服？能详细说说吗？"
        elif not memory.duration:
            return f"理解您{memory.main_symptom}的困扰。这种情况持续多久了？"
        elif not memory.severity:
            return "明白了，那现在症状大概能打几分呢（1-10分，10分最难受）？"
        else:
            return "好的，除了这个还有其他不舒服的地方吗？"
    
    def _generate_product_recommendation(self, query: str, context: ConversationContext, session_id: str = None) -> Dict:
        """生成产品推荐（优先使用LLM + RAG）"""
        import time
        kb_start_time = time.time()
        
        # 构建查询（结合用户画像和症状）
        search_query = query
        
        # 添加症状信息
        if context.short_term_memory and context.short_term_memory.main_symptom:
            search_query += f" {context.short_term_memory.main_symptom}"
        
        # 添加画像信息（年龄、性别、慢性疾病等）
        profile_parts = []
        if context.profile.age:
            profile_parts.append(f"{context.profile.age}岁")
        if context.profile.gender:
            profile_parts.append(context.profile.gender)
        if context.profile.chronic_diseases:
            profile_parts.append(context.profile.chronic_diseases)
        if context.profile.health_concerns:
            profile_parts.append(context.profile.health_concerns)
        
        if profile_parts:
            search_query += " " + " ".join(profile_parts)
        
        # 检索产品
        results = self.product_retriever.retrieve(search_query, top_k=3)
        
        kb_end_time = time.time()
        
        if not results:
            return {
                "response": "根据您的情况，我建议您先详细描述一下症状，这样我能更准确地为您推荐合适的产品。",
                "recommended_products": []
            }
        
        # 记录知识库调用
        kb_call = {
            'query': search_query,
            'intent': 'recommendation',
            'results_count': len(results),
            'product_ids': [r.product_id for r in results],
            'response_time_ms': int((kb_end_time - kb_start_time) * 1000)
        }
        self._current_kb_calls.append(kb_call)
        print(f"[DEBUG] _generate_product_recommendation self id: {id(self)}, _current_kb_calls id: {id(self._current_kb_calls)}")
        print(f"[DEBUG] Added KB call: {kb_call}")
        print(f"[DEBUG] _current_kb_calls now: {self._current_kb_calls}")
        
        # 构建知识库上下文
        knowledge_context = self._build_product_knowledge_context(results)
        
        # 使用LLM生成推荐（带RAG），失败时返回固定提示
        llm_response = self._generate_llm_response(
            'recommendation_engine',
            f"请基于以下产品信息，为用户推荐合适的产品。用户问题：{query}",
            context,
            additional_knowledge=knowledge_context,
            temperature=0.7,
            max_tokens=500,
            session_id=session_id
        )
        
        # 如果LLM返回断开提示，直接返回
        if llm_response == self.LLM_DISCONNECTED_MESSAGE:
            return {
                "response": llm_response,
                "recommended_products": []
            }
        
        # 记录推荐历史，并保存当前讨论的产品
        for result in results:
            product = self.product_retriever.get_product_by_id(result.product_id)
            if product:
                from orchestrator import ProductRecommendation
                context.recommended_products.append(ProductRecommendation(
                    product_name=product['product_name'],
                    reason=f"匹配查询: {search_query}",
                    contraindications_checked=True
                ))
                # 保存当前讨论的产品（第一个推荐的产品）
                if not context.current_discussed_product:
                    context.current_discussed_product = product['product_name']
        
        return {
            "response": llm_response,
            "recommended_products": [
                {
                    "product_id": r.product_id,
                    "product_name": self.product_retriever.get_product_by_id(r.product_id)['product_name'] if self.product_retriever.get_product_by_id(r.product_id) else r.product_id,
                    "score": r.score
                }
                for r in results
            ]
        }
    
    def _build_product_knowledge_context(self, results: List) -> str:
        """构建产品知识库上下文"""
        if not results:
            return ""
        
        context_parts = ["## 可推荐产品列表\n"]
        
        for i, result in enumerate(results, 1):
            product = self.product_retriever.get_product_by_id(result.product_id)
            if product:
                context_parts.append(f"\n### {i}. {product['product_name']}")
                context_parts.append(f"主要功效：{product['main_efficacy']}")
                context_parts.append(f"适用人群：{product['target_audience']}")
                
                # 核心成分
                ingredients = product.get('core_ingredients', [])
                if ingredients:
                    names = [f"{ing['name']}（{ing['function']}）" for ing in ingredients[:3]]
                    context_parts.append(f"核心成分：{'、'.join(names)}")
                
                # 用法用量
                dosage = product.get('dosage', {})
                if dosage:
                    context_parts.append(f"用法用量：{dosage.get('adult', '详见说明')}")
                
                # 禁忌
                contraindications = product.get('contraindications', [])
                if contraindications:
                    context_parts.append(f"禁忌：{'、'.join(contraindications[:2])}")
        
        return '\n'.join(context_parts)
    
    def _generate_product_recommendation_fallback(self, query: str, context: ConversationContext,
                                                   results: List, search_query: str) -> Dict:
        """生成产品推荐（规则方式 - Fallback）"""
        response_parts = ["根据您的情况，我为您推荐以下产品：\n"]
        products = []
        
        for i, result in enumerate(results, 1):
            product = self.product_retriever.get_product_by_id(result.product_id)
            if product:
                # 检查禁忌
                contraindication_warning = self._check_contraindications(product, context)
                
                response_parts.append(f"\n{i}. 【{product['product_name']}】")
                response_parts.append(f"   功效：{product['main_efficacy']}")
                
                # 添加核心成分
                ingredients = product.get('core_ingredients', [])
                if ingredients:
                    ingredient_names = [ing['name'] for ing in ingredients[:3]]
                    response_parts.append(f"   核心成分：{'、'.join(ingredient_names)}")
                
                # 添加用法
                dosage = product.get('dosage', {})
                if dosage:
                    response_parts.append(f"   用法：{dosage.get('adult', '详见说明')}")
                
                # 添加禁忌提醒
                if contraindication_warning:
                    response_parts.append(f"   ⚠️ {contraindication_warning}")
                
                products.append({
                    "product_id": product['product_id'],
                    "product_name": product['product_name'],
                    "main_efficacy": product['main_efficacy'],
                    "score": result.score
                })
                
                # 记录推荐历史
                from orchestrator import ProductRecommendation
                context.recommended_products.append(ProductRecommendation(
                    product_name=product['product_name'],
                    reason=f"匹配查询: {search_query}",
                    contraindications_checked=bool(contraindication_warning)
                ))
        
        response_parts.append("\n温馨提示：以上产品仅供参考，不能代替医生的诊断和治疗。如有需要，请咨询专业医生。")
        
        return {
            "response": '\n'.join(response_parts),
            "products": products
        }
    
    def _check_contraindications(self, product: Dict, context: ConversationContext) -> str:
        """检查禁忌症"""
        warnings = []
        
        # 检查慢性病禁忌
        if context.profile.chronic_diseases:
            chronic_diseases = product.get('contraindication_diseases', [])
            for disease in chronic_diseases:
                if disease in context.profile.chronic_diseases:
                    warnings.append(f"有{disease}请注意")
        
        # 检查年龄禁忌
        age = context.profile.age
        target_age = product.get('target_age_range', {})
        if age and target_age:
            if age < target_age.get('min', 0) or age > target_age.get('max', 150):
                warnings.append("年龄可能不适合")
        
        # 检查一般禁忌
        contraindications = product.get('contraindications', [])
        if contraindications:
            warnings.append(f"禁忌：{'、'.join(contraindications[:2])}")
        
        return '；'.join(warnings) if warnings else ""
    
    def _handle_product_consult(self, query: str, context: ConversationContext, session_id: str = None) -> str:
        """处理产品咨询（优先使用LLM + RAG）"""
        # 尝试识别产品名称（从当前查询或上下文中）
        target_product = None
        
        # 首先尝试从当前查询中识别产品
        for p in self.product_retriever.products:
            if p['product_name'] in query or any(alias in query for alias in p.get('product_name_alias', [])):
                target_product = p
                # 记住当前讨论的产品
                context.current_discussed_product = p['product_name']
                break
        
        # 如果没有识别到，检查是否有指代词（这个产品/那产品/它/刚才的产品）
        if not target_product:
            refer_keywords = ['这个产品', '那产品', '此产品', '它', '刚才的产品', '推荐的产品', '那个产品']
            has_refer = any(kw in query for kw in refer_keywords)
            if has_refer and context.current_discussed_product:
                for p in self.product_retriever.products:
                    if p['product_name'] == context.current_discussed_product:
                        target_product = p
                        break
        
        # 如果没有识别到，但上下文中有记住的产品，使用上下文中的产品
        if not target_product and context.current_discussed_product:
            for p in self.product_retriever.products:
                if p['product_name'] == context.current_discussed_product:
                    target_product = p
                    break
        
        if target_product:
            # 构建产品知识库上下文
            knowledge_context = self._build_single_product_context(target_product)
            
            # 使用LLM生成回答，失败时返回固定提示
            return self._generate_llm_response(
                'product_consult',
                f"用户咨询产品：{target_product['product_name']}\n用户问题：{query}",
                context,
                additional_knowledge=knowledge_context,
                temperature=0.7,
                max_tokens=400,
                session_id=session_id
            )
        else:
            # 没有识别到具体产品，检索相关产品
            results = self.product_retriever.retrieve(query, top_k=3)
            if results:
                # 记住第一个检索到的产品
                context.current_discussed_product = self.product_retriever.get_product_by_id(results[0].product_id)['product_name']
                knowledge_context = self._build_product_knowledge_context(results)
                return self._generate_llm_response(
                    'product_consult',
                    f"用户询问：{query}",
                    context,
                    additional_knowledge=knowledge_context,
                    temperature=0.7,
                    max_tokens=400,
                    session_id=session_id
                )
            
            return "抱歉，我没有找到相关的产品信息。您可以告诉我您想了解什么健康问题，我来帮您推荐合适的产品~"
    
    def _build_single_product_context(self, product: Dict) -> str:
        """构建单个产品的知识库上下文"""
        context_parts = [f"## 产品信息：{product['product_name']}\n"]
        context_parts.append(f"主要功效：{product['main_efficacy']}")
        context_parts.append(f"适用人群：{product['target_audience']}")
        
        # 核心成分
        ingredients = product.get('core_ingredients', [])
        if ingredients:
            context_parts.append("\n核心成分：")
            for ing in ingredients:
                context_parts.append(f"- {ing['name']}：{ing['function']}")
        
        # 用法用量
        usage = product.get('usage', '')
        dosage = product.get('dosage', {})
        if usage:
            context_parts.append(f"\n用法：{usage}")
        if dosage:
            context_parts.append(f"用量：{dosage.get('adult', '详见说明')}")
        
        # 禁忌
        contraindications = product.get('contraindications', [])
        if contraindications:
            context_parts.append(f"\n禁忌：{'、'.join(contraindications)}")
        
        # FAQ
        faqs = product.get('faq', [])
        if faqs:
            context_parts.append("\n常见问答：")
            for faq in faqs[:3]:
                context_parts.append(f"Q: {faq['question']}")
                context_parts.append(f"A: {faq['answer']}")
        
        return '\n'.join(context_parts)
    
    def _build_product_info_response(self, product: Dict) -> str:
        """构建产品信息回复（Fallback）"""
        response_parts = [f"关于【{product['product_name']}】：\n"]
        response_parts.append(f"【主要功效】{product['main_efficacy']}")
        response_parts.append(f"【适用人群】{product['target_audience']}")
        
        # 核心成分
        ingredients = product.get('core_ingredients', [])
        if ingredients:
            response_parts.append("\n【核心成分】")
            for ing in ingredients[:4]:
                response_parts.append(f"• {ing['name']}：{ing['function']}")
        
        # 用法用量
        usage = product.get('usage', '')
        dosage = product.get('dosage', {})
        if usage:
            response_parts.append(f"\n【用法】{usage}")
        if dosage:
            response_parts.append(f"【用量】{dosage.get('adult', '详见说明')}")
        
        # 禁忌
        contraindications = product.get('contraindications', [])
        if contraindications:
            response_parts.append(f"\n【禁忌】{'、'.join(contraindications)}")
        
        # FAQ提示
        response_parts.append(f"\n您还可以问我关于{product['product_name']}的常见问题，比如：")
        response_parts.append("• 适合什么人吃？")
        response_parts.append("• 有什么副作用？")
        response_parts.append("• 多久见效？")
        
        return '\n'.join(response_parts)
    
    def _handle_knowledge_query(self, query: str, context: ConversationContext, session_id: str = None) -> str:
        """处理健康知识查询（优先使用LLM + RAG）"""
        # 从产品知识库中检索相关内容
        results = self.product_retriever.retrieve(query, top_k=3, intent="knowledge")
        
        # 构建知识库上下文
        knowledge_context = ""
        if results:
            knowledge_parts = ["## 相关健康知识\n"]
            for i, result in enumerate(results, 1):
                product = self.product_retriever.get_product_by_id(result.product_id)
                if product:
                    # 提取相关的FAQ或功效信息
                    faqs = product.get('faq', [])
                    if faqs:
                        knowledge_parts.append(f"\n### {product['product_name']}相关知识：")
                        for faq in faqs[:2]:
                            if any(keyword in faq['question'] or keyword in faq['answer'] 
                                   for keyword in [query[:4], query[-4:]] if len(query) > 4):
                                knowledge_parts.append(f"问：{faq['question']}")
                                knowledge_parts.append(f"答：{faq['answer']}")
            
            # 添加通用健康知识
            knowledge_parts.extend([
                "\n## 通用健康知识",
                "• 规律作息有助于改善睡眠质量",
                "• 适量运动有益身心健康",
                "• 均衡饮食是健康的基石",
                "• 保持乐观心态对健康很重要"
            ])
            
            knowledge_context = '\n'.join(knowledge_parts)
        
        # 使用LLM生成回答，失败时返回固定提示
        return self._generate_llm_response(
            'knowledge_qa',
            f"用户问题：{query}",
            context,
            additional_knowledge=knowledge_context,
            temperature=0.7,
            max_tokens=400,
            session_id=session_id
        )
    
    def _generate_welcome_response(self) -> str:
        """生成欢迎回复"""
        return """您好！我是泰小虎，您的健康顾问~

我可以帮您：
🩺 解答健康问题，了解身体状况
💊 推荐合适的保健品
📚 普及健康养生知识

请问有什么可以帮到您的吗？"""
    
    def get_product_faq(self, product_name: str, question: str = None) -> str:
        """获取产品FAQ"""
        return self.product_retriever.get_product_faq(product_name, question)
    
    def list_products(self) -> list:
        """列出所有产品"""
        return self.product_retriever.list_all_products()
    
    def clear_session(self, session_id: str):
        """清除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def get_llm_status(self) -> Dict[str, Any]:
        """获取LLM状态"""
        config = self.llm_adapter.get_safe_config()
        return {
            "enabled": self.llm_adapter.is_enabled,
            "model": config.get("model", ""),
            "provider": config.get("provider", ""),
            "has_api_key": bool(config.get("api_key", "")) and "****" not in config.get("api_key", "")
        }
    
    def test_llm_connection(self) -> Dict[str, Any]:
        """测试LLM连接"""
        return self.llm_adapter.test_connection()


# 便捷函数
_agent_service = None


def get_agent_service() -> AgentService:
    """获取全局Agent服务"""
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service
