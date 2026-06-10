"""
泰小虎智能体 - 产品知识库检索模块 (RAG)
基于关键词匹配和语义相似度的混合检索
"""

import json
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass
class RetrievalResult:
    """检索结果"""
    product_id: str
    product_name: str
    content: str
    score: float
    match_type: str  # "exact", "keyword", "semantic"
    matched_keywords: List[str]


class ProductRetriever:
    """产品知识库检索器"""
    
    def __init__(self, knowledge_base_path: str = None):
        """
        初始化检索器
        
        Args:
            knowledge_base_path: 产品知识库JSON文件路径
        """
        self.products = []
        self.knowledge_base_path = knowledge_base_path or "data/products_knowledge.json"
        self._load_knowledge_base()
    
    def _load_knowledge_base(self):
        """加载产品知识库"""
        try:
            with open(self.knowledge_base_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.products = data.get('products', [])
            print(f"✓ 产品知识库加载成功: {len(self.products)} 个产品")
        except Exception as e:
            print(f"✗ 加载产品知识库失败: {e}")
            self.products = []
    
    def retrieve(self, query: str, top_k: int = 3, intent: str = None) -> List[RetrievalResult]:
        """
        检索产品信息
        
        Args:
            query: 用户查询
            top_k: 返回结果数量
            intent: 当前意图（用于调整检索策略）
            
        Returns:
            List[RetrievalResult]: 检索结果列表
        """
        if not self.products:
            return []
        
        results = []
        query_lower = query.lower()
        
        # 1. 精确匹配（产品名称）
        for product in self.products:
            score, match_type, keywords = self._calculate_match_score(query_lower, product)
            if score > 0:
                results.append(RetrievalResult(
                    product_id=product['product_id'],
                    product_name=product['product_name'],
                    content=self._extract_relevant_content(product, query_lower),
                    score=score,
                    match_type=match_type,
                    matched_keywords=keywords
                ))
        
        # 2. 排序并返回top_k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    def _calculate_match_score(self, query: str, product: Dict) -> tuple:
        """
        计算匹配分数
        
        Returns:
            (score, match_type, matched_keywords)
        """
        score = 0.0
        match_type = "none"
        matched_keywords = []
        
        # 精确匹配产品名称（最高权重）
        product_names = [product['product_name'].lower()] + \
                       [alias.lower() for alias in product.get('product_name_alias', [])]
        
        for name in product_names:
            if name in query:
                score += 10.0
                match_type = "exact"
                matched_keywords.append(name)
                break
        
        # 关键词匹配
        efficacy_keywords = [kw.lower() for kw in product.get('efficacy_keywords', [])]
        for kw in efficacy_keywords:
            if kw in query:
                score += 3.0
                matched_keywords.append(kw)
                if match_type == "none":
                    match_type = "keyword"
        
        # 搜索关键词匹配
        search_keywords = [kw.lower() for kw in product.get('search_keywords', [])]
        for kw in search_keywords:
            if kw in query:
                score += 2.5
                matched_keywords.append(kw)
                if match_type == "none":
                    match_type = "keyword"
        
        # 标签匹配
        tags = [tag.lower() for tag in product.get('tags', [])]
        for tag in tags:
            if tag in query:
                score += 2.0
                matched_keywords.append(tag)
                if match_type == "none":
                    match_type = "keyword"
        
        # 适用症状匹配
        target_symptoms = [s.lower() for s in product.get('target_symptoms', [])]
        for symptom in target_symptoms:
            if symptom in query:
                score += 2.5
                matched_keywords.append(symptom)
                if match_type == "none":
                    match_type = "keyword"
        
        # 语义相似度（简单实现）
        main_efficacy = product.get('main_efficacy', '').lower()
        similarity = SequenceMatcher(None, query, main_efficacy).ratio()
        if similarity > 0.3:
            score += similarity * 2
            if match_type == "none":
                match_type = "semantic"
        
        return score, match_type, matched_keywords
    
    def _extract_relevant_content(self, product: Dict, query: str) -> str:
        """提取与查询相关的产品内容"""
        content_parts = []
        
        # 产品名称
        content_parts.append(f"【产品名称】{product['product_name']}")
        
        # 主要功效
        content_parts.append(f"【主要功效】{product.get('main_efficacy', '')}")
        
        # 核心成分
        ingredients = product.get('core_ingredients', [])
        if ingredients:
            ingredient_names = [f"{ing['name']}({ing['function']})" for ing in ingredients[:3]]
            content_parts.append(f"【核心成分】{'、'.join(ingredient_names)}")
        
        # 适用人群
        content_parts.append(f"【适用人群】{product.get('target_audience', '')}")
        
        # 用法用量
        usage = product.get('usage', '')
        dosage = product.get('dosage', {})
        adult_dose = dosage.get('adult', '')
        if usage and adult_dose:
            content_parts.append(f"【用法用量】{usage}，{adult_dose}")
        
        # 禁忌
        contraindications = product.get('contraindications', [])
        if contraindications:
            content_parts.append(f"【禁忌】{'、'.join(contraindications)}")
        
        # 注意事项
        precautions = product.get('precautions', [])
        if precautions:
            content_parts.append(f"【注意事项】{'；'.join(precautions[:2])}")
        
        return '\n'.join(content_parts)
    
    def get_product_by_name(self, name: str) -> Optional[Dict]:
        """根据产品名称获取产品详情"""
        name_lower = name.lower()
        for product in self.products:
            # 匹配主名称
            if name_lower in product['product_name'].lower():
                return product
            # 匹配别名
            for alias in product.get('product_name_alias', []):
                if name_lower in alias.lower():
                    return product
        return None
    
    def get_product_by_id(self, product_id: str) -> Optional[Dict]:
        """根据产品ID获取产品详情"""
        for product in self.products:
            if product['product_id'] == product_id:
                return product
        return None
    
    def search_by_symptom(self, symptom: str) -> List[RetrievalResult]:
        """根据症状搜索产品"""
        results = []
        symptom_lower = symptom.lower()
        
        for product in self.products:
            score = 0.0
            matched = False
            
            # 匹配适用症状
            target_symptoms = [s.lower() for s in product.get('target_symptoms', [])]
            if symptom_lower in target_symptoms:
                score += 5.0
                matched = True
            
            # 匹配功效关键词
            efficacy_keywords = [kw.lower() for kw in product.get('efficacy_keywords', [])]
            if symptom_lower in efficacy_keywords:
                score += 4.0
                matched = True
            
            if matched:
                results.append(RetrievalResult(
                    product_id=product['product_id'],
                    product_name=product['product_name'],
                    content=self._extract_relevant_content(product, symptom_lower),
                    score=score,
                    match_type="symptom_match",
                    matched_keywords=[symptom]
                ))
        
        results.sort(key=lambda x: x.score, reverse=True)
        return results
    
    def generate_recommendation_response(self, query: str, context: Any = None) -> str:
        """
        生成产品推荐回复
        
        Args:
            query: 用户查询
            context: 对话上下文
            
        Returns:
            str: 推荐回复
        """
        results = self.retrieve(query, top_k=3)
        
        if not results:
            return "抱歉，根据您的描述，我暂时没有找到完全匹配的产品。您可以告诉我更多关于您的健康状况，我会尽力为您推荐合适的产品。"
        
        # 生成推荐回复
        response_parts = ["根据您的情况，我为您推荐以下产品：\n"]
        
        for i, result in enumerate(results, 1):
            product = self.get_product_by_id(result.product_id)
            if product:
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
                contraindications = product.get('contraindications', [])
                if contraindications:
                    response_parts.append(f"   ⚠️ 禁忌：{'、'.join(contraindications)}")
        
        response_parts.append("\n温馨提示：以上产品仅供参考，不能代替医生的诊断和治疗。如有需要，请咨询专业医生。")
        
        return '\n'.join(response_parts)
    
    def get_product_faq(self, product_name: str, question: str = None) -> str:
        """
        获取产品FAQ
        
        Args:
            product_name: 产品名称
            question: 具体问题（可选）
            
        Returns:
            str: FAQ回复
        """
        product = self.get_product_by_name(product_name)
        if not product:
            return f"抱歉，我没有找到关于'{product_name}'的信息。"
        
        faq_list = product.get('faq', [])
        if not faq_list:
            return f"关于{product['product_name']}，您可以问我：\n• 适合什么人吃？\n• 有什么功效？\n• 怎么服用？"
        
        # 如果有具体问题，尝试匹配
        if question:
            question_lower = question.lower()
            for faq in faq_list:
                if any(kw in question_lower for kw in faq['question'].lower().split()):
                    return f"关于{product['product_name']}：\n\nQ: {faq['question']}\nA: {faq['answer']}"
        
        # 返回所有FAQ
        response = f"关于{product['product_name']}的常见问题：\n"
        for i, faq in enumerate(faq_list[:5], 1):
            response += f"\n{i}. {faq['question']}\n   {faq['answer'][:100]}..."
        
        return response
    
    def list_all_products(self) -> List[Dict]:
        """列出所有产品"""
        return [
            {
                'product_id': p['product_id'],
                'product_name': p['product_name'],
                'main_efficacy': p['main_efficacy'],
                'category': p['category']
            }
            for p in self.products
        ]


# 便捷函数
def create_product_retriever(knowledge_base_path: str = None) -> ProductRetriever:
    """创建产品检索器"""
    return ProductRetriever(knowledge_base_path)


# 测试代码
if __name__ == "__main__":
    retriever = create_product_retriever()
    
    # 测试检索
    test_queries = [
        "泰吉眠适合什么人",
        "失眠怎么办",
        "便秘吃什么好",
        "提高记忆力",
        "美容护肤"
    ]
    
    print("=" * 60)
    print("产品知识库检索测试")
    print("=" * 60)
    
    for query in test_queries:
        print(f"\n查询: {query}")
        results = retriever.retrieve(query, top_k=2)
        if results:
            for r in results:
                print(f"  → {r.product_name} (得分: {r.score:.2f}, 匹配: {r.match_type})")
        else:
            print("  → 未找到匹配产品")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
