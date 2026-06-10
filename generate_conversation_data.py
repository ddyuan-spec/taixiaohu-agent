"""
生成10条覆盖各种场景的多轮对话测试数据
并同步更新链路追踪、模型调用、Badcase、用户画像等关联数据
"""
import json
import os
import sys

# 添加 app 目录到路径
APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                       'smart_agent', 'docs', 'app')
sys.path.insert(0, APP_DIR)

from datetime import datetime, timedelta
import uuid

DATA_DIR = os.path.join(APP_DIR, "data")
CONVERSATION_LOG_DIR = os.path.join(DATA_DIR, "conversation_logs")
os.makedirs(CONVERSATION_LOG_DIR, exist_ok=True)

def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ============================================================
# 10条多轮对话场景定义
# ============================================================

SCENARIOS = [
    {
        "session_id": "sess_demo_001",
        "user_id": "user_demo_001",
        "title": "保健品推荐-多轮咨询",
        "turns": [
            {
                "user": "你好，我想给我妈买点保健品，她今年65岁了",
                "agent": "您好！为65岁的长辈选择保健品，建议先了解她的健康状况。请问您母亲目前有什么慢性病或正在服用的药物吗？",
                "intent": "health_consult",
                "intent_confidence": 0.95,
                "kb_calls": [{"query": "老年人保健品推荐", "results_count": 5, "product_ids": ["prod_001", "prod_002"],
                    "sources": [
                        {"file_name": "老年人营养指南.pdf", "chunk_id": "chunk_001", "chunk_content": "老年人日常保健应关注心血管健康和骨骼健康，推荐补充深海鱼油、辅酶Q10和维生素D+钙...", "relevance": 0.92},
                        {"file_name": "保健品产品手册.pdf", "chunk_id": "chunk_005", "chunk_content": "深海鱼油富含Omega-3脂肪酸，有助于调节血脂，建议选择低钠配方产品...", "relevance": 0.88}
                    ]
                }],
                "llm_calls": [{"module": "intent_recognition", "prompt_tokens": 120, "completion_tokens": 45, "total_tokens": 165, "response_time_ms": 800, "success": True}],
                "recommended_products": [],
                "trace_nodes": [
                    {"node_type": "intent_recognition", "duration_ms": 800, "status": "success", "input": {"user_message": "你好，我想给我妈买点保健品，她今年65岁了"}, "output": {"intent": "health_consult", "confidence": 0.95}},
                    {"node_type": "knowledge_query", "duration_ms": 300, "status": "success", "input": {"query": "老年人保健品推荐"}, "output": {"results_count": 5, "top_relevance": 0.92}},
                    {"node_type": "dialogue_response", "duration_ms": 1200, "status": "success", "input": {"context": "用户为65岁母亲咨询保健品"}, "output": {"response": "询问健康状况"}}
                ]
            },
            {
                "user": "她有高血压，平时在吃降压药",
                "agent": "了解了。高血压患者在选择保健品时需要特别注意。我推荐以下几款适合高血压人群的保健品：\n\n1. **深海鱼油** - 有助于调节血脂，选择低钠配方\n2. **辅酶Q10** - 对心血管健康有益\n3. **维生素D+钙** - 老年人普遍缺乏\n\n请问您母亲有没有其他过敏史或特殊饮食要求？",
                "intent": "product_recommend",
                "intent_confidence": 0.93,
                "kb_calls": [{"query": "高血压 保健品 推荐", "results_count": 3, "product_ids": ["prod_003", "prod_004", "prod_005"],
                    "sources": [
                        {"file_name": "高血压人群保健指南.pdf", "chunk_id": "chunk_010", "chunk_content": "高血压患者选择保健品需特别注意钠含量，推荐辅酶Q10和低钠深海鱼油...", "relevance": 0.91},
                        {"file_name": "产品禁忌说明.pdf", "chunk_id": "chunk_015", "chunk_content": "高血压患者应避免高钠保健品，服用降压药期间可安全使用辅酶Q10...", "relevance": 0.85}
                    ]
                }],
                "llm_calls": [
                    {"module": "intent_recognition", "prompt_tokens": 150, "completion_tokens": 50, "total_tokens": 200, "response_time_ms": 700, "success": True},
                    {"module": "product_recommendation", "prompt_tokens": 800, "completion_tokens": 200, "total_tokens": 1000, "response_time_ms": 1500, "success": True}
                ],
                "recommended_products": ["prod_003", "prod_004", "prod_005"],
                "trace_nodes": [
                    {"node_type": "intent_recognition", "duration_ms": 700, "status": "success", "input": {"user_message": "她有高血压，平时在吃降压药"}, "output": {"intent": "product_recommend", "confidence": 0.93}},
                    {"node_type": "knowledge_query", "duration_ms": 250, "status": "success", "input": {"query": "高血压 保健品 推荐"}, "output": {"results_count": 3, "top_relevance": 0.89}},
                    {"node_type": "product_recommend", "duration_ms": 1500, "status": "success", "input": {"products": ["prod_003", "prod_004", "prod_005"]}, "output": {"recommended": ["prod_003", "prod_004", "prod_005"]}},
                    {"node_type": "dialogue_response", "duration_ms": 1100, "status": "success", "input": {"context": "推荐高血压适用保健品"}, "output": {"response": "推荐3款产品"}}
                ]
            },
            {
                "user": "她没有过敏史，这些大概多少钱？",
                "agent": "好的，以下是推荐产品的价格信息：\n\n1. **深海鱼油（60粒装）** - ￥128\n2. **辅酶Q10（30粒装）** - ￥198\n3. **维生素D+钙（90片装）** - ￥89\n\n三件套组合价￥358（省￥57）。需要我帮您生成订单吗？",
                "intent": "price_inquiry",
                "intent_confidence": 0.91,
                "kb_calls": [{"query": "产品价格 鱼油 辅酶Q10 钙片", "results_count": 3, "product_ids": ["prod_003", "prod_004", "prod_005"],
                    "sources": [
                        {"file_name": "产品价目表2024.pdf", "chunk_id": "chunk_020", "chunk_content": "深海鱼油60粒装￥128，辅酶Q10 30粒装￥198，维生素D+钙90片装￥89...", "relevance": 0.95},
                        {"file_name": "促销政策.pdf", "chunk_id": "chunk_025", "chunk_content": "三件套组合价￥358，比单买节省￥57，活动有效期至2024年底...", "relevance": 0.90}
                    ]
                }],
                "llm_calls": [{"module": "dialogue_response", "prompt_tokens": 600, "completion_tokens": 150, "total_tokens": 750, "response_time_ms": 900, "success": True}],
                "recommended_products": ["prod_003", "prod_004", "prod_005"],
                "trace_nodes": [
                    {"node_type": "intent_recognition", "duration_ms": 600, "status": "success", "input": {"user_message": "她没有过敏史，这些大概多少钱？"}, "output": {"intent": "price_inquiry", "confidence": 0.91}},
                    {"node_type": "knowledge_query", "duration_ms": 200, "status": "success", "input": {"query": "产品价格"}, "output": {"results_count": 3, "top_relevance": 0.95}},
                    {"node_type": "dialogue_response", "duration_ms": 900, "status": "success", "input": {"context": "询问产品价格"}, "output": {"response": "报价信息"}}
                ]
            }
        ],
        "profile": {"age": 65, "gender": "女", "chronic_disease": "高血压", "allergies": "无", "medications": "降压药", "health_concerns": "心血管健康、骨骼健康"},
        "has_badcase": False
    },
    {
        "session_id": "sess_demo_002",
        "user_id": "user_demo_002",
        "title": "儿童营养-Badcase场景",
        "turns": [
            {
                "user": "我家孩子3岁了，最近不爱吃饭，有什么办法吗？",
                "agent": "3岁孩子不爱吃饭是常见问题。建议：\n1. 营造愉快的用餐氛围\n2. 控制零食摄入\n3. 增加食物多样性\n\n另外，可以适当补充儿童复合维生素。",
                "intent": "health_consult",
                "intent_confidence": 0.88,
                "kb_calls": [{"query": "儿童不爱吃饭 解决办法", "results_count": 4, "product_ids": ["prod_010"],
                    "sources": [
                        {"file_name": "儿童营养指南.pdf", "chunk_id": "chunk_030", "chunk_content": "3岁儿童不爱吃饭可通过营造用餐氛围、控制零食、增加食物多样性来改善...", "relevance": 0.87},
                        {"file_name": "儿童维生素产品说明.pdf", "chunk_id": "chunk_032", "chunk_content": "儿童复合维生素适用于3岁以上儿童，每日1片，可补充日常饮食不足...", "relevance": 0.82}
                    ]
                }],
                "llm_calls": [{"module": "intent_recognition", "prompt_tokens": 130, "completion_tokens": 60, "total_tokens": 190, "response_time_ms": 750, "success": True}],
                "recommended_products": ["prod_010"],
                "trace_nodes": [
                    {"node_type": "intent_recognition", "duration_ms": 750, "status": "success", "input": {"user_message": "我家孩子3岁了，最近不爱吃饭，有什么办法吗？"}, "output": {"intent": "health_consult", "confidence": 0.88}},
                    {"node_type": "knowledge_query", "duration_ms": 280, "status": "success", "input": {"query": "儿童不爱吃饭"}, "output": {"results_count": 4, "top_relevance": 0.85}},
                    {"node_type": "dialogue_response", "duration_ms": 1000, "status": "success", "input": {"context": "3岁儿童不爱吃饭"}, "output": {"response": "建议+维生素推荐"}}
                ]
            },
            {
                "user": "那维生素会不会有副作用？",
                "agent": "儿童维生素一般很安全，按照推荐剂量服用即可。",
                "intent": "safety_inquiry",
                "intent_confidence": 0.85,
                "kb_calls": [{"query": "儿童维生素 副作用", "results_count": 2, "product_ids": [],
                    "sources": [
                        {"file_name": "儿童维生素安全手册.pdf", "chunk_id": "chunk_035", "chunk_content": "3岁儿童服用维生素需严格按推荐剂量，过量可能导致维生素A/D中毒...", "relevance": 0.85},
                        {"file_name": "产品说明书.pdf", "chunk_id": "chunk_036", "chunk_content": "儿童复合维生素推荐剂量：3-6岁每日半片，6岁以上每日1片...", "relevance": 0.80}
                    ]
                }],
                "llm_calls": [{"module": "dialogue_response", "prompt_tokens": 400, "completion_tokens": 80, "total_tokens": 480, "response_time_ms": 600, "success": True}],
                "recommended_products": [],
                "trace_nodes": [
                    {"node_type": "intent_recognition", "duration_ms": 600, "status": "success", "input": {"user_message": "那维生素会不会有副作用？"}, "output": {"intent": "safety_inquiry", "confidence": 0.85}},
                    {"node_type": "knowledge_query", "duration_ms": 200, "status": "success", "input": {"query": "儿童维生素 副作用"}, "output": {"results_count": 2, "top_relevance": 0.78}},
                    {"node_type": "safety_check", "duration_ms": 5000, "status": "error", "input": {"condition": "3岁儿童", "product": "复合维生素"}, "output": {"error": "安全检查超时"}, "error_message": "安全检查服务响应超时"},
                    {"node_type": "dialogue_response", "duration_ms": 600, "status": "success", "input": {"context": "询问维生素安全性"}, "output": {"response": "简单回答安全性"}}
                ]
            }
        ],
        "profile": {"age": 32, "gender": "女", "chronic_disease": "", "allergies": "", "medications": "", "health_concerns": "儿童营养"},
        "has_badcase": True,
        "badcase": {
            "category": "inappropriate_response",
            "description": "3岁儿童服用维生素需要更谨慎的剂量指导，系统回答过于笼统，未提及过量风险",
            "severity": "high",
            "conversation_snippet": "用户：那维生素会不会有副作用？\n系统：儿童维生素一般很安全，按照推荐剂量服用即可。\n问题：未针对3岁儿童给出具体剂量建议和风险提示"
        }
    },
    {
        "session_id": "sess_demo_003",
        "user_id": "user_demo_003",
        "title": "减肥咨询-知识库引用",
        "turns": [
            {
                "user": "我想减肥，有什么推荐的保健品吗？",
                "agent": "减肥是一个系统工程，保健品只能作为辅助。根据《中国居民膳食指南》，健康减重建议每周减少0.5-1kg。\n\n推荐的辅助产品：\n1. **膳食纤维** - 增加饱腹感\n2. **左旋肉碱** - 促进脂肪代谢\n3. **益生菌** - 调节肠道菌群\n\n但最重要的是控制饮食和增加运动。",
                "intent": "product_recommend",
                "intent_confidence": 0.94,
                "kb_calls": [{"query": "减肥 保健品 膳食纤维 左旋肉碱", "results_count": 6, "product_ids": ["prod_020", "prod_021", "prod_022"],
                    "sources": [
                        {"file_name": "减肥营养指南.pdf", "chunk_id": "chunk_040", "chunk_content": "《中国居民膳食指南》建议健康减重每周减少0.5-1kg，推荐膳食纤维增加饱腹感...", "relevance": 0.91},
                        {"file_name": "运动营养手册.pdf", "chunk_id": "chunk_042", "chunk_content": "左旋肉碱可促进脂肪代谢，配合有氧运动效果更佳，建议每日500-2000mg...", "relevance": 0.87}
                    ]
                }],
                "llm_calls": [
                    {"module": "intent_recognition", "prompt_tokens": 110, "completion_tokens": 40, "total_tokens": 150, "response_time_ms": 650, "success": True},
                    {"module": "product_recommendation", "prompt_tokens": 700, "completion_tokens": 180, "total_tokens": 880, "response_time_ms": 1400, "success": True}
                ],
                "recommended_products": ["prod_020", "prod_021", "prod_022"],
                "trace_nodes": [
                    {"node_type": "intent_recognition", "duration_ms": 650, "status": "success", "input": {"user_message": "我想减肥，有什么推荐的保健品吗？"}, "output": {"intent": "product_recommend", "confidence": 0.94}},
                    {"node_type": "knowledge_query", "duration_ms": 320, "status": "success", "input": {"query": "减肥 保健品"}, "output": {"results_count": 6, "top_relevance": 0.91, "sources": [{"file": "减肥营养指南.pdf", "chunk_id": "chunk_001", "relevance": 0.91}, {"file": "运动营养手册.pdf", "chunk_id": "chunk_002", "relevance": 0.87}]}},
                    {"node_type": "product_recommend", "duration_ms": 1400, "status": "success", "input": {"products": ["prod_020", "prod_021", "prod_022"]}, "output": {"recommended": ["prod_020", "prod_021", "prod_022"]}},
                    {"node_type": "dialogue_response", "duration_ms": 1050, "status": "success", "input": {"context": "减肥保健品推荐"}, "output": {"response": "推荐3款产品+膳食指南引用"}}
                ]
            },
            {
                "user": "这些和节食一起吃效果更好吗？",
                "agent": "不建议过度节食。根据营养学研究，过度节食会导致基础代谢率下降，反而容易反弹。建议：\n\n1. 每日热量摄入不低于1200大卡\n2. 蛋白质摄入要充足（每公斤体重1-1.2g）\n3. 配合有氧运动（每周150分钟）\n\n保健品在合理饮食基础上才能发挥最佳效果。",
                "intent": "knowledge_query",
                "intent_confidence": 0.89,
                "kb_calls": [{"query": "节食 基础代谢 反弹", "results_count": 4, "product_ids": [],
                    "sources": [
                        {"file_name": "减肥营养指南.pdf", "chunk_id": "chunk_044", "chunk_content": "过度节食会导致基础代谢率下降，反而容易反弹，建议每日热量摄入不低于1200大卡...", "relevance": 0.88},
                        {"file_name": "运动营养学.pdf", "chunk_id": "chunk_046", "chunk_content": "蛋白质摄入要充足，每公斤体重1-1.2g，配合有氧运动每周150分钟...", "relevance": 0.84}
                    ]
                }],
                "llm_calls": [{"module": "dialogue_response", "prompt_tokens": 550, "completion_tokens": 160, "total_tokens": 710, "response_time_ms": 950, "success": True}],
                "recommended_products": [],
                "trace_nodes": [
                    {"node_type": "intent_recognition", "duration_ms": 620, "status": "success", "input": {"user_message": "这些和节食一起吃效果更好吗？"}, "output": {"intent": "knowledge_query", "confidence": 0.89}},
                    {"node_type": "knowledge_query", "duration_ms": 280, "status": "success", "input": {"query": "节食 基础代谢"}, "output": {"results_count": 4, "top_relevance": 0.88, "sources": [{"file": "减肥营养指南.pdf", "chunk_id": "chunk_003", "relevance": 0.88}]}},
                    {"node_type": "dialogue_response", "duration_ms": 950, "status": "success", "input": {"context": "节食与保健品搭配"}, "output": {"response": "不建议过度节食"}}
                ]
            }
        ],
        "profile": {"age": 28, "gender": "女", "chronic_disease": "", "allergies": "", "medications": "", "health_concerns": "体重管理"},
        "has_badcase": False
    },
    {
        "session_id": "sess_demo_004",
        "user_id": "user_demo_004",
        "title": "画像采集-新用户",
        "turns": [
            {
                "user": "你好",
                "agent": "您好！我是泰小虎，您的健康顾问。为了更好地为您服务，能否告诉我您的年龄和性别？",
                "intent": "greeting",
                "intent_confidence": 0.97,
                "kb_calls": [],
                "llm_calls": [{"module": "intent_recognition", "prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80, "response_time_ms": 400, "success": True}],
                "recommended_products": [],
                "trace_nodes": [
                    {"node_type": "intent_recognition", "duration_ms": 400, "status": "success", "input": {"user_message": "你好"}, "output": {"intent": "greeting", "confidence": 0.97}},
                    {"node_type": "profile_collection", "duration_ms": 300, "status": "success", "input": {"step": "init"}, "output": {"asked_fields": ["age", "gender"]}},
                    {"node_type": "dialogue_response", "duration_ms": 500, "status": "success", "input": {"context": "新用户问候"}, "output": {"response": "问候+请求画像信息"}}
                ]
            },
            {
                "user": "我28岁，男",
                "agent": "收到！28岁男性。请问您有什么慢性病或正在服用的药物吗？（如高血压、糖尿病等）",
                "intent": "profile_collection",
                "intent_confidence": 0.96,
                "kb_calls": [],
                "llm_calls": [{"module": "dialogue_response", "prompt_tokens": 100, "completion_tokens": 40, "total_tokens": 140, "response_time_ms": 450, "success": True}],
                "recommended_products": [],
                "trace_nodes": [
                    {"node_type": "intent_recognition", "duration_ms": 380, "status": "success", "input": {"user_message": "我28岁，男"}, "output": {"intent": "profile_collection", "confidence": 0.96}},
                    {"node_type": "profile_collection", "duration_ms": 200, "status": "success", "input": {"step": "age_gender", "data": {"age": 28, "gender": "男"}}, "output": {"asked_fields": ["chronic_disease"]}},
                    {"node_type": "dialogue_response", "duration_ms": 450, "status": "success", "input": {"context": "收集画像-年龄性别"}, "output": {"response": "询问慢性病"}}
                ]
            },
            {
                "user": "没有慢性病，就是经常熬夜",
                "agent": "了解了。熬夜会影响免疫力和肝脏代谢。针对您的情况，我建议关注以下方面：\n\n1. **护肝类** - 奶蓟草提取物\n2. **维生素B族** - 缓解疲劳\n3. **褪黑素** - 改善睡眠质量\n\n同时建议尽量调整作息，保证每天7-8小时睡眠。",
                "intent": "product_recommend",
                "intent_confidence": 0.90,
                "kb_calls": [{"query": "熬夜 护肝 维生素B 褪黑素", "results_count": 5, "product_ids": ["prod_030", "prod_031", "prod_032"],
                    "sources": [
                        {"file_name": "熬夜恢复指南.pdf", "chunk_id": "chunk_050", "chunk_content": "熬夜会影响免疫力和肝脏代谢，推荐奶蓟草提取物护肝、维生素B族缓解疲劳...", "relevance": 0.90},
                        {"file_name": "睡眠改善手册.pdf", "chunk_id": "chunk_052", "chunk_content": "褪黑素可改善睡眠质量，建议睡前30分钟服用1-3mg，同时调整作息...", "relevance": 0.86}
                    ]
                }],
                "llm_calls": [
                    {"module": "intent_recognition", "prompt_tokens": 120, "completion_tokens": 50, "total_tokens": 170, "response_time_ms": 600, "success": True},
                    {"module": "product_recommendation", "prompt_tokens": 500, "completion_tokens": 150, "total_tokens": 650, "response_time_ms": 1200, "success": True}
                ],
                "recommended_products": ["prod_030", "prod_031", "prod_032"],
                "trace_nodes": [
                    {"node_type": "intent_recognition", "duration_ms": 600, "status": "success", "input": {"user_message": "没有慢性病，就是经常熬夜"}, "output": {"intent": "product_recommend", "confidence": 0.90}},
                    {"node_type": "profile_collection", "duration_ms": 150, "status": "success", "input": {"step": "health_status", "data": {"chronic_disease": "无", "lifestyle": "经常熬夜"}}, "output": {"completed": True}},
                    {"node_type": "knowledge_query", "duration_ms": 250, "status": "success", "input": {"query": "熬夜 保健品"}, "output": {"results_count": 5, "top_relevance": 0.90}},
                    {"node_type": "product_recommend", "duration_ms": 1200, "status": "success", "input": {"products": ["prod_030", "prod_031", "prod_032"]}, "output": {"recommended": ["prod_030", "prod_031", "prod_032"]}},
                    {"node_type": "dialogue_response", "duration_ms": 900, "status": "success", "input": {"context": "熬夜人群保健品推荐"}, "output": {"response": "推荐护肝+维B+褪黑素"}}
                ]
            }
        ],
        "profile": {"age": 28, "gender": "男", "chronic_disease": "无", "allergies": "", "medications": "", "health_concerns": "熬夜恢复、肝脏健康"},
        "has_badcase": False
    },
    {
        "session_id": "sess_demo_005",
        "user_id": "user_demo_005",
        "title": "关节养护-中老年用户",
        "turns": [
            {
                "user": "我膝盖不太好，上下楼梯会疼，有什么保健品能吃吗？",
                "agent": "膝盖疼痛在中老年人群中很常见，通常与关节软骨磨损有关。建议关注以下成分：\n\n1. **氨糖软骨素** - 修复软骨组织\n2. **胶原蛋白** - 维持关节弹性\n3. **MSM（有机硫）** - 缓解炎症\n\n请问您今年多大年纪？疼痛持续多久了？",
                "intent": "health_consult",
                "intent_confidence": 0.92,
                "kb_calls": [{"query": "膝盖疼痛 关节 保健品", "results_count": 5, "product_ids": ["prod_040", "prod_041"],
                    "sources": [
                        {"file_name": "关节养护指南.pdf", "chunk_id": "chunk_060", "chunk_content": "膝盖疼痛通常与关节软骨磨损有关，推荐氨糖软骨素修复软骨、胶原蛋白维持弹性...", "relevance": 0.93},
                        {"file_name": "中老年保健手册.pdf", "chunk_id": "chunk_062", "chunk_content": "MSM有机硫可缓解关节炎症，配合氨糖使用效果更佳，建议连续服用3个月...", "relevance": 0.89}
                    ]
                }],
                "llm_calls": [{"module": "dialogue_response", "prompt_tokens": 500, "completion_tokens": 130, "total_tokens": 630, "response_time_ms": 850, "success": True}],
                "recommended_products": ["prod_040", "prod_041"],
                "trace_nodes": [
                    {"node_type": "intent_recognition", "duration_ms": 700, "status": "success", "input": {"user_message": "我膝盖不太好，上下楼梯会疼，有什么保健品能吃吗？"}, "output": {"intent": "health_consult", "confidence": 0.92}},
                    {"node_type": "knowledge_query", "duration_ms": 300, "status": "success", "input": {"query": "膝盖疼痛 关节保健品"}, "output": {"results_count": 5, "top_relevance": 0.93}},
                    {"node_type": "dialogue_response", "duration_ms": 850, "status": "success", "input": {"context": "膝盖疼痛咨询"}, "output": {"response": "推荐氨糖软骨素等"}}
                ]
            },
            {
                "user": "我55岁了，疼了大概半年",
                "agent": "55岁出现膝盖疼痛半年，建议先去医院做个X光检查，排除骨关节炎。在保健品方面，以下产品比较适合您：\n\n1. **氨糖软骨素复合片** - ￥168/60片\n2. **钙+维生素D3** - ￥89/90片\n\n建议连续服用3个月以上观察效果。同时注意减少爬楼梯和深蹲动作。",
                "intent": "product_recommend",
                "intent_confidence": 0.91,
                "kb_calls": [{"query": "55岁 膝盖疼痛 氨糖软骨素", "results_count": 3, "product_ids": ["prod_040", "prod_042"],
                    "sources": [
                        {"file_name": "关节养护指南.pdf", "chunk_id": "chunk_064", "chunk_content": "55岁出现膝盖疼痛建议先就医排除骨关节炎，氨糖软骨素复合片￥168/60片...", "relevance": 0.90},
                        {"file_name": "钙片产品说明.pdf", "chunk_id": "chunk_066", "chunk_content": "钙+维生素D3 ￥89/90片，建议中老年每日补充，配合氨糖效果更佳...", "relevance": 0.87}
                    ]
                }],
                "llm_calls": [
                    {"module": "intent_recognition", "prompt_tokens": 140, "completion_tokens": 55, "total_tokens": 195, "response_time_ms": 680, "success": True},
                    {"module": "product_recommendation", "prompt_tokens": 600, "completion_tokens": 160, "total_tokens": 760, "response_time_ms": 1300, "success": True}
                ],
                "recommended_products": ["prod_040", "prod_042"],
                "trace_nodes": [
                    {"node_type": "intent_recognition", "duration_ms": 680, "status": "success", "input": {"user_message": "我55岁了，疼了大概半年"}, "output": {"intent": "product_recommend", "confidence": 0.91}},
                    {"node_type": "knowledge_query", "duration_ms": 280, "status": "success", "input": {"query": "中老年 关节养护"}, "output": {"results_count": 3, "top_relevance": 0.90}},
                    {"node_type": "product_recommend", "duration_ms": 1300, "status": "success", "input": {"products": ["prod_040", "prod_042"]}, "output": {"recommended": ["prod_040", "prod_042"]}},
                    {"node_type": "dialogue_response", "duration_ms": 1000, "status": "success", "input": {"context": "55岁膝盖疼痛半年"}, "output": {"response": "建议就医+产品推荐"}}
                ]
            }
        ],
        "profile": {"age": 55, "gender": "男", "chronic_disease": "", "allergies": "", "medications": "", "health_concerns": "关节健康"},
        "has_badcase": False
    },
    {
        "session_id": "sess_demo_006",
        "user_id": "user_demo_006",
        "title": "孕期营养-敏感场景",
        "turns": [
            {
                "user": "我怀孕了，现在4个月，需要补充什么营养吗？",
                "agent": "恭喜您！孕4个月是胎儿快速发育期，营养需求增加。重点补充：\n\n1. **叶酸** - 预防神经管缺陷（400-800μg/天）\n2. **DHA** - 促进胎儿大脑发育\n3. **钙+维生素D** - 骨骼发育\n4. **铁剂** - 预防孕期贫血\n\n建议选择孕妇专用复合维生素。",
                "intent": "health_consult",
                "intent_confidence": 0.95,
                "kb_calls": [{"query": "孕期营养 叶酸 DHA 钙 铁", "results_count": 6, "product_ids": ["prod_050"],
                    "sources": [
                        {"file_name": "孕期营养指南.pdf", "chunk_id": "chunk_070", "chunk_content": "孕4个月是胎儿快速发育期，重点补充叶酸400-800μg/天预防神经管缺陷...", "relevance": 0.94},
                        {"file_name": "DHA产品说明.pdf", "chunk_id": "chunk_072", "chunk_content": "DHA促进胎儿大脑发育，建议选择藻油DHA更纯净，每日200-300mg...", "relevance": 0.91}
                    ]
                }],
                "llm_calls": [{"module": "dialogue_response", "prompt_tokens": 550, "completion_tokens": 140, "total_tokens": 690, "response_time_ms": 900, "success": True}],
                "recommended_products": ["prod_050"],
                "trace_nodes": [
                    {"node_type": "intent_recognition", "duration_ms": 720, "status": "success", "input": {"user_message": "我怀孕了，现在4个月，需要补充什么营养吗？"}, "output": {"intent": "health_consult", "confidence": 0.95}},
                    {"node_type": "knowledge_query", "duration_ms": 350, "status": "success", "input": {"query": "孕期营养 4个月"}, "output": {"results_count": 6, "top_relevance": 0.94}},
                    {"node_type": "dialogue_response", "duration_ms": 900, "status": "success", "input": {"context": "孕4个月营养咨询"}, "output": {"response": "叶酸+DHA+钙+铁推荐"}}
                ]
            },
            {
                "user": "这些对胎儿不会有影响吧？",
                "agent": "孕期补充这些营养素是安全的，但需要注意：\n\n1. **叶酸** - 孕期必需，安全剂量内无害\n2. **DHA** - 选择藻油DHA更纯净\n3. **钙** - 不超过2000mg/天\n4. **铁** - 遵医嘱，过量可能便秘\n\n建议在产科医生指导下服用，定期产检。",
                "intent": "safety_inquiry",
                "intent_confidence": 0.93,
                "kb_calls": [{"query": "孕期 营养素 安全性", "results_count": 4, "product_ids": [],
                    "sources": [
                        {"file_name": "孕期安全手册.pdf", "chunk_id": "chunk_074", "chunk_content": "孕期补充营养素安全，叶酸安全剂量内无害，钙不超过2000mg/天，铁需遵医嘱...", "relevance": 0.92},
                        {"file_name": "产检指南.pdf", "chunk_id": "chunk_076", "chunk_content": "建议在产科医生指导下服用营养素，定期产检监测胎儿发育情况...", "relevance": 0.88}
                    ]
                }],
                "llm_calls": [{"module": "dialogue_response", "prompt_tokens": 480, "completion_tokens": 120, "total_tokens": 600, "response_time_ms": 780, "success": True}],
                "recommended_products": [],
                "trace_nodes": [
                    {"node_type": "intent_recognition", "duration_ms": 650, "status": "success", "input": {"user_message": "这些对胎儿不会有影响吧？"}, "output": {"intent": "safety_inquiry", "confidence": 0.93}},
                    {"node_type": "safety_check", "duration_ms": 800, "status": "success", "input": {"condition": "孕期4个月", "products": ["叶酸", "DHA", "钙", "铁"]}, "output": {"safe": True, "warnings": ["钙不超过2000mg/天", "铁遵医嘱"]}},
                    {"node_type": "dialogue_response", "duration_ms": 780, "status": "success", "input": {"context": "孕期安全性咨询"}, "output": {"response": "安全性说明+剂量建议"}}
                ]
            }
        ],
        "profile": {"age": 30, "gender": "女", "chronic_disease": "", "allergies": "", "medications": "", "health_concerns": "孕期营养"},
        "has_badcase": False
    },
    {
        "session_id": "sess_demo_007",
        "user_id": "user_demo_007",
        "title": "糖尿病饮食-Badcase场景2",
        "turns": [
            {
                "user": "我有糖尿病，平时血糖控制得不太好，有什么保健品能辅助降糖吗？",
                "agent": "糖尿病患者选择保健品需要非常谨慎。以下产品可能有一定辅助作用：\n\n1. **铬元素** - 可能改善胰岛素敏感性\n2. **苦瓜提取物** - 传统降糖食材\n3. **膳食纤维** - 延缓糖分吸收\n\n但请注意：保健品不能替代降糖药物！",
                "intent": "product_recommend",
                "intent_confidence": 0.87,
                "kb_calls": [{"query": "糖尿病 保健品 降糖", "results_count": 4, "product_ids": ["prod_060", "prod_061"],
                    "sources": [
                        {"file_name": "糖尿病保健指南.pdf", "chunk_id": "chunk_080", "chunk_content": "铬元素可能改善胰岛素敏感性，苦瓜提取物是传统降糖食材，膳食纤维延缓糖分吸收...", "relevance": 0.82},
                        {"file_name": "医疗免责声明.pdf", "chunk_id": "chunk_082", "chunk_content": "保健品不能替代降糖药物，糖尿病患者任何用药调整必须咨询医生...", "relevance": 0.90}
                    ]
                }],
                "llm_calls": [{"module": "dialogue_response", "prompt_tokens": 600, "completion_tokens": 150, "total_tokens": 750, "response_time_ms": 950, "success": True}],
                "recommended_products": ["prod_060", "prod_061"],
                "trace_nodes": [
                    {"node_type": "intent_recognition", "duration_ms": 750, "status": "success", "input": {"user_message": "我有糖尿病，平时血糖控制得不太好，有什么保健品能辅助降糖吗？"}, "output": {"intent": "product_recommend", "confidence": 0.87}},
                    {"node_type": "knowledge_query", "duration_ms": 300, "status": "success", "input": {"query": "糖尿病 保健品 降糖"}, "output": {"results_count": 4, "top_relevance": 0.82}},
                    {"node_type": "dialogue_response", "duration_ms": 950, "status": "success", "input": {"context": "糖尿病保健品咨询"}, "output": {"response": "推荐铬元素+苦瓜提取物"}}
                ]
            },
            {
                "user": "那我可以停掉二甲双胍只吃这些吗？",
                "agent": "不建议这样做。保健品只能作为辅助，不能替代处方药物。",
                "intent": "medical_advice",
                "intent_confidence": 0.90,
                "kb_calls": [],
                "llm_calls": [{"module": "dialogue_response", "prompt_tokens": 350, "completion_tokens": 60, "total_tokens": 410, "response_time_ms": 500, "success": True}],
                "recommended_products": [],
                "trace_nodes": [
                    {"node_type": "intent_recognition", "duration_ms": 580, "status": "success", "input": {"user_message": "那我可以停掉二甲双胍只吃这些吗？"}, "output": {"intent": "medical_advice", "confidence": 0.90}},
                    {"node_type": "safety_check", "duration_ms": 600, "status": "success", "input": {"condition": "糖尿病", "intent": "停药"}, "output": {"safe": False, "warning": "用户意图停药，需强烈劝阻"}},
                    {"node_type": "dialogue_response", "duration_ms": 500, "status": "success", "input": {"context": "询问停药"}, "output": {"response": "劝阻停药"}}
                ]
            }
        ],
        "profile": {"age": 52, "gender": "男", "chronic_disease": "2型糖尿病", "allergies": "", "medications": "二甲双胍", "health_concerns": "血糖控制"},
        "has_badcase": True,
        "badcase": {
            "category": "knowledge_gap",
            "description": "系统未充分强调糖尿病患者不能停用处方药的重要性，回答过于简短，缺乏医学免责声明",
            "severity": "critical",
            "conversation_snippet": "用户：那我可以停掉二甲双胍只吃这些吗？\n系统：不建议这样做。保健品只能作为辅助，不能替代处方药物。\n问题：回答过于简短，未提供替代方案建议，缺乏就医指导"
        }
    },
    {
        "session_id": "sess_demo_008",
        "user_id": "user_demo_008",
        "title": "运动后恢复-健身人群",
        "turns": [
            {
                "user": "我每周健身4次，想买点蛋白粉和恢复类的保健品",
                "agent": "健身人群的营养补充很关键！根据您的训练频率，推荐以下产品：\n\n1. **乳清蛋白粉** - 训练后30分钟内补充，促进肌肉修复\n2. **支链氨基酸(BCAA)** - 训练中饮用，减少肌肉分解\n3. **肌酸** - 提升爆发力和训练容量\n4. **镁+锌** - 促进恢复和睡眠质量\n\n请问您的训练目标是什么？增肌还是减脂？",
                "intent": "product_recommend",
                "intent_confidence": 0.94,
                "kb_calls": [{"query": "健身 蛋白粉 BCAA 肌酸", "results_count": 7, "product_ids": ["prod_070", "prod_071", "prod_072", "prod_073"],
                    "sources": [
                        {"file_name": "运动营养指南.pdf", "chunk_id": "chunk_090", "chunk_content": "乳清蛋白粉训练后30分钟内补充30g促进肌肉修复，BCAA训练中饮用减少肌肉分解...", "relevance": 0.93},
                        {"file_name": "肌酸使用手册.pdf", "chunk_id": "chunk_092", "chunk_content": "肌酸可提升爆发力和训练容量，建议每日5g，配合充足水分摄入...", "relevance": 0.90}
                    ]
                }],
                "llm_calls": [
                    {"module": "intent_recognition", "prompt_tokens": 130, "completion_tokens": 50, "total_tokens": 180, "response_time_ms": 620, "success": True},
                    {"module": "product_recommendation", "prompt_tokens": 650, "completion_tokens": 170, "total_tokens": 820, "response_time_ms": 1450, "success": True}
                ],
                "recommended_products": ["prod_070", "prod_071", "prod_072", "prod_073"],
                "trace_nodes": [
                    {"node_type": "intent_recognition", "duration_ms": 620, "status": "success", "input": {"user_message": "我每周健身4次，想买点蛋白粉和恢复类的保健品"}, "output": {"intent": "product_recommend", "confidence": 0.94}},
                    {"node_type": "knowledge_query", "duration_ms": 280, "status": "success", "input": {"query": "健身 蛋白粉 BCAA 肌酸"}, "output": {"results_count": 7, "top_relevance": 0.93}},
                    {"node_type": "product_recommend", "duration_ms": 1450, "status": "success", "input": {"products": ["prod_070", "prod_071", "prod_072", "prod_073"]}, "output": {"recommended": ["prod_070", "prod_071", "prod_072", "prod_073"]}},
                    {"node_type": "dialogue_response", "duration_ms": 1100, "status": "success", "input": {"context": "健身人群产品推荐"}, "output": {"response": "推荐蛋白粉+BCAA+肌酸+镁锌"}}
                ]
            },
            {
                "user": "主要是增肌，这些怎么吃比较好？",
                "agent": "增肌期的补充方案建议：\n\n**训练日：**\n- 训练前30分钟：肌酸5g + BCAA 10g\n- 训练后30分钟内：乳清蛋白粉30g\n- 睡前：酪蛋白或镁+锌\n\n**休息日：**\n- 早餐：乳清蛋白粉20g\n- 睡前：镁+锌\n\n同时确保每日蛋白质摄入达到1.6-2.2g/kg体重。",
                "intent": "usage_guidance",
                "intent_confidence": 0.92,
                "kb_calls": [{"query": "增肌 蛋白粉 服用方法", "results_count": 3, "product_ids": ["prod_070"],
                    "sources": [
                        {"file_name": "增肌营养方案.pdf", "chunk_id": "chunk_094", "chunk_content": "增肌期每日蛋白质摄入1.6-2.2g/kg体重，训练日训练后30分钟内补充乳清蛋白30g...", "relevance": 0.91},
                        {"file_name": "补剂搭配指南.pdf", "chunk_id": "chunk_096", "chunk_content": "肌酸5g+BCAA 10g训练前，乳清蛋白30g训练后，睡前镁+锌促进恢复...", "relevance": 0.88}
                    ]
                }],
                "llm_calls": [{"module": "dialogue_response", "prompt_tokens": 580, "completion_tokens": 180, "total_tokens": 760, "response_time_ms": 1000, "success": True}],
                "recommended_products": ["prod_070"],
                "trace_nodes": [
                    {"node_type": "intent_recognition", "duration_ms": 650, "status": "success", "input": {"user_message": "主要是增肌，这些怎么吃比较好？"}, "output": {"intent": "usage_guidance", "confidence": 0.92}},
                    {"node_type": "knowledge_query", "duration_ms": 220, "status": "success", "input": {"query": "增肌 服用方法"}, "output": {"results_count": 3, "top_relevance": 0.91}},
                    {"node_type": "dialogue_response", "duration_ms": 1000, "status": "success", "input": {"context": "增肌服用指导"}, "output": {"response": "详细的服用时间和剂量"}}
                ]
            }
        ],
        "profile": {"age": 26, "gender": "男", "chronic_disease": "", "allergies": "", "medications": "", "health_concerns": "增肌、运动恢复"},
        "has_badcase": False
    },
    {
        "session_id": "sess_demo_009",
        "user_id": "user_demo_009",
        "title": "免疫力提升-换季防护",
        "turns": [
            {
                "user": "最近换季老是感冒，有什么能提高免疫力的？",
                "agent": "换季容易感冒确实与免疫力下降有关。以下营养素有助于增强免疫系统：\n\n1. **维生素C** - 增强白细胞活性\n2. **维生素D** - 调节免疫反应\n3. **锌** - 促进免疫细胞生成\n4. **益生菌** - 70%免疫细胞在肠道\n5. **蜂胶/蜂皇浆** - 天然抗菌成分\n\n建议组合补充，同时保持充足睡眠和适度运动。",
                "intent": "product_recommend",
                "intent_confidence": 0.93,
                "kb_calls": [{"query": "免疫力 维生素C 维生素D 锌 益生菌", "results_count": 6, "product_ids": ["prod_080", "prod_081", "prod_082"],
                    "sources": [
                        {"file_name": "免疫力提升指南.pdf", "chunk_id": "chunk_100", "chunk_content": "维生素C增强白细胞活性，维生素D调节免疫反应，锌促进免疫细胞生成...", "relevance": 0.90},
                        {"file_name": "肠道健康手册.pdf", "chunk_id": "chunk_102", "chunk_content": "70%免疫细胞在肠道，益生菌4-8周调节肠道菌群，蜂胶1-2周有初步感受...", "relevance": 0.87}
                    ]
                }],
                "llm_calls": [
                    {"module": "intent_recognition", "prompt_tokens": 120, "completion_tokens": 45, "total_tokens": 165, "response_time_ms": 580, "success": True},
                    {"module": "product_recommendation", "prompt_tokens": 600, "completion_tokens": 160, "total_tokens": 760, "response_time_ms": 1350, "success": True}
                ],
                "recommended_products": ["prod_080", "prod_081", "prod_082"],
                "trace_nodes": [
                    {"node_type": "intent_recognition", "duration_ms": 580, "status": "success", "input": {"user_message": "最近换季老是感冒，有什么能提高免疫力的？"}, "output": {"intent": "product_recommend", "confidence": 0.93}},
                    {"node_type": "knowledge_query", "duration_ms": 300, "status": "success", "input": {"query": "免疫力 换季感冒"}, "output": {"results_count": 6, "top_relevance": 0.90}},
                    {"node_type": "product_recommend", "duration_ms": 1350, "status": "success", "input": {"products": ["prod_080", "prod_081", "prod_082"]}, "output": {"recommended": ["prod_080", "prod_081", "prod_082"]}},
                    {"node_type": "dialogue_response", "duration_ms": 1050, "status": "success", "input": {"context": "免疫力提升推荐"}, "output": {"response": "维C+维D+锌+益生菌+蜂胶"}}
                ]
            },
            {
                "user": "这些要吃多久才能见效？",
                "agent": "免疫力提升是一个渐进过程，通常需要：\n\n- **维生素C/D、锌** - 2-4周开始感受到效果\n- **益生菌** - 4-8周调节肠道菌群\n- **蜂胶** - 1-2周可能有初步感受\n\n建议至少连续补充3个月，配合健康生活方式。如果感冒频率没有改善，建议就医检查是否有其他免疫问题。",
                "intent": "usage_guidance",
                "intent_confidence": 0.89,
                "kb_calls": [{"query": "免疫力 见效时间", "results_count": 3, "product_ids": [],
                    "sources": [
                        {"file_name": "免疫力提升指南.pdf", "chunk_id": "chunk_104", "chunk_content": "维生素C/D、锌2-4周见效，益生菌4-8周调节肠道菌群，蜂胶1-2周有初步感受...", "relevance": 0.85},
                        {"file_name": "营养补充周期.pdf", "chunk_id": "chunk_106", "chunk_content": "建议至少连续补充3个月，配合健康生活方式，如无效建议就医检查...", "relevance": 0.82}
                    ]
                }],
                "llm_calls": [{"module": "dialogue_response", "prompt_tokens": 450, "completion_tokens": 130, "total_tokens": 580, "response_time_ms": 800, "success": True}],
                "recommended_products": [],
                "trace_nodes": [
                    {"node_type": "intent_recognition", "duration_ms": 600, "status": "success", "input": {"user_message": "这些要吃多久才能见效？"}, "output": {"intent": "usage_guidance", "confidence": 0.89}},
                    {"node_type": "knowledge_query", "duration_ms": 200, "status": "success", "input": {"query": "免疫力 见效时间"}, "output": {"results_count": 3, "top_relevance": 0.85}},
                    {"node_type": "dialogue_response", "duration_ms": 800, "status": "success", "input": {"context": "询问见效时间"}, "output": {"response": "各产品见效时间说明"}}
                ]
            }
        ],
        "profile": {"age": 35, "gender": "女", "chronic_disease": "", "allergies": "", "medications": "", "health_concerns": "免疫力提升"},
        "has_badcase": False
    },
    {
        "session_id": "sess_demo_010",
        "user_id": "user_demo_010",
        "title": "综合咨询-复杂场景",
        "turns": [
            {
                "user": "我爸70岁了，有高血压和糖尿病，最近记忆力下降，有什么能吃的？",
                "agent": "70岁长辈同时有高血压和糖尿病，选择保健品需要特别谨慎。针对记忆力下降，以下成分可能有帮助：\n\n1. **DHA/EPA** - 支持脑部健康（选择低钠配方）\n2. **磷脂酰丝氨酸(PS)** - 改善认知功能\n3. **维生素B12** - 老年人常缺乏，影响神经功能\n\n但必须先咨询主治医生，确保与现有药物没有冲突！",
                "intent": "health_consult",
                "intent_confidence": 0.90,
                "kb_calls": [{"query": "老年人 高血压 糖尿病 记忆力 DHA", "results_count": 5, "product_ids": ["prod_090"],
                    "sources": [
                        {"file_name": "老年脑健康指南.pdf", "chunk_id": "chunk_110", "chunk_content": "DHA/EPA支持脑部健康，70岁老人选择低钠配方，磷脂酰丝氨酸改善认知...", "relevance": 0.86},
                        {"file_name": "慢病用药注意.pdf", "chunk_id": "chunk_112", "chunk_content": "高血压糖尿病患者服用保健品前必须咨询医生，注意药物相互作用...", "relevance": 0.91}
                    ]
                }],
                "llm_calls": [{"module": "dialogue_response", "prompt_tokens": 700, "completion_tokens": 170, "total_tokens": 870, "response_time_ms": 1100, "success": True}],
                "recommended_products": ["prod_090"],
                "trace_nodes": [
                    {"node_type": "intent_recognition", "duration_ms": 780, "status": "success", "input": {"user_message": "我爸70岁了，有高血压和糖尿病，最近记忆力下降，有什么能吃的？"}, "output": {"intent": "health_consult", "confidence": 0.90}},
                    {"node_type": "knowledge_query", "duration_ms": 350, "status": "success", "input": {"query": "老年人 高血压 糖尿病 记忆力"}, "output": {"results_count": 5, "top_relevance": 0.86}},
                    {"node_type": "safety_check", "duration_ms": 900, "status": "success", "input": {"condition": "高血压+糖尿病", "age": 70}, "output": {"safe": True, "warnings": ["需医生确认", "注意药物相互作用"]}},
                    {"node_type": "dialogue_response", "duration_ms": 1100, "status": "success", "input": {"context": "70岁多病老人记忆力下降"}, "output": {"response": "DHA+PS+B12推荐+就医提醒"}}
                ]
            },
            {
                "user": "他平时在吃阿司匹林和格列美脲，会有冲突吗？",
                "agent": "您提到的药物与保健品的相互作用需要专业评估：\n\n- **阿司匹林** + 鱼油/DHA - 可能增加出血风险，需医生确认剂量\n- **格列美脲** + 大部分保健品 - 一般无明显冲突\n\n**强烈建议**：在服用任何保健品前，请携带产品成分表咨询您父亲的主治医生或药师。系统无法替代专业医疗建议。",
                "intent": "safety_inquiry",
                "intent_confidence": 0.94,
                "kb_calls": [{"query": "阿司匹林 格列美脲 保健品 相互作用", "results_count": 4, "product_ids": [],
                    "sources": [
                        {"file_name": "药物相互作用手册.pdf", "chunk_id": "chunk_114", "chunk_content": "阿司匹林+鱼油可能增加出血风险，需医生确认剂量，格列美脲与大部分保健品无明显冲突...", "relevance": 0.84},
                        {"file_name": "慢病用药注意.pdf", "chunk_id": "chunk_116", "chunk_content": "服用保健品前请携带产品成分表咨询主治医生或药师，系统无法替代专业医疗建议...", "relevance": 0.88}
                    ]
                }],
                "llm_calls": [{"module": "dialogue_response", "prompt_tokens": 600, "completion_tokens": 150, "total_tokens": 750, "response_time_ms": 950, "success": True}],
                "recommended_products": [],
                "trace_nodes": [
                    {"node_type": "intent_recognition", "duration_ms": 720, "status": "success", "input": {"user_message": "他平时在吃阿司匹林和格列美脲，会有冲突吗？"}, "output": {"intent": "safety_inquiry", "confidence": 0.94}},
                    {"node_type": "knowledge_query", "duration_ms": 320, "status": "success", "input": {"query": "阿司匹林 格列美脲 相互作用"}, "output": {"results_count": 4, "top_relevance": 0.84}},
                    {"node_type": "safety_check", "duration_ms": 850, "status": "success", "input": {"medications": ["阿司匹林", "格列美脲"], "supplements": ["DHA", "PS", "B12"]}, "output": {"safe": "conditional", "warnings": ["阿司匹林+鱼油可能增加出血风险"]}},
                    {"node_type": "dialogue_response", "duration_ms": 950, "status": "success", "input": {"context": "药物相互作用咨询"}, "output": {"response": "相互作用说明+就医建议"}}
                ]
            },
            {
                "user": "好的，我会先问医生。谢谢",
                "agent": "不客气！您的做法非常正确。对于有多种慢性病且正在服药的长辈，先咨询医生是最安全的选择。\n\n如果医生确认可以服用，建议从单一产品开始，观察1-2周后再考虑添加其他产品。\n\n祝您父亲健康！如有其他问题随时咨询。",
                "intent": "greeting",
                "intent_confidence": 0.88,
                "kb_calls": [],
                "llm_calls": [{"module": "dialogue_response", "prompt_tokens": 300, "completion_tokens": 90, "total_tokens": 390, "response_time_ms": 600, "success": True}],
                "recommended_products": [],
                "trace_nodes": [
                    {"node_type": "intent_recognition", "duration_ms": 450, "status": "success", "input": {"user_message": "好的，我会先问医生。谢谢"}, "output": {"intent": "greeting", "confidence": 0.88}},
                    {"node_type": "dialogue_response", "duration_ms": 600, "status": "success", "input": {"context": "用户感谢结束对话"}, "output": {"response": "安全建议+祝福"}}
                ]
            }
        ],
        "profile": {"age": 45, "gender": "女", "chronic_disease": "", "allergies": "", "medications": "", "health_concerns": "父亲健康管理"},
        "has_badcase": False
    }
]

# ============================================================
# 生成对话记录JSON文件
# ============================================================

def generate_conversation_data():
    sessions = []
    traces = []
    model_calls = []
    badcases = []
    profiles = {}
    
    now = datetime.now()
    
    for i, scenario in enumerate(SCENARIOS):
        session_id = scenario["session_id"]
        user_id = scenario["user_id"]
        
        # 生成会话时间（分布在最近7天内）
        session_time = now - timedelta(days=i, hours=i*2)
        
        # 构建消息列表
        messages = []
        msg_time = session_time
        
        for turn_idx, turn in enumerate(scenario["turns"]):
            # 用户消息
            user_msg = {
                "message_id": f"{session_id}_user_{turn_idx}",
                "message_type": "user",
                "content": turn["user"],
                "timestamp": msg_time.isoformat()
            }
            messages.append(user_msg)
            msg_time += timedelta(minutes=1)
            
            # 助手消息
            agent_msg = {
                "message_id": f"{session_id}_agent_{turn_idx}",
                "message_type": "agent",
                "content": turn["agent"],
                "intent": turn["intent"],
                "intent_confidence": turn["intent_confidence"],
                "recommended_products": turn.get("recommended_products", []),
                "knowledge_base_calls": [
                    {
                        "query": kb["query"],
                        "intent": turn["intent"],
                        "results_count": kb["results_count"],
                        "product_ids": kb.get("product_ids", []),
                        "response_time_ms": 200 + turn_idx * 50,
                        "sources": kb.get("sources", []),
                        "timestamp": msg_time.isoformat()
                    } for kb in turn.get("kb_calls", [])
                ],
                "llm_calls": [
                    {
                        "module": llm["module"],
                        "prompt_tokens": llm["prompt_tokens"],
                        "completion_tokens": llm["completion_tokens"],
                        "total_tokens": llm["total_tokens"],
                        "response_time_ms": llm["response_time_ms"],
                        "success": llm["success"],
                        "error_message": "",
                        "timestamp": msg_time.isoformat()
                    } for llm in turn.get("llm_calls", [])
                ],
                "timestamp": msg_time.isoformat()
            }
            messages.append(agent_msg)
            msg_time += timedelta(minutes=2)
            
            # 生成模型调用记录
            for llm in turn.get("llm_calls", []):
                model_calls.append({
                    "call_id": f"call_{session_id}_{turn_idx}_{llm['module']}",
                    "session_id": session_id,
                    "conversation_id": f"conv_{session_id}",
                    "model_name": "qwen-plus",
                    "prompt_tokens": llm["prompt_tokens"],
                    "completion_tokens": llm["completion_tokens"],
                    "total_tokens": llm["total_tokens"],
                    "response_time_ms": llm["response_time_ms"],
                    "module_type": llm["module"],
                    "status": "success" if llm["success"] else "error",
                    "error_message": "",
                    "cost_usd": round(llm["total_tokens"] * 0.00002, 4),
                    "created_at": msg_time.isoformat()
                })
            
            # 生成链路追踪
            trace_nodes = []
            for node_idx, node in enumerate(turn.get("trace_nodes", [])):
                trace_nodes.append({
                    "node_id": f"txh_{session_id}_{turn_idx}_node_{node_idx}",
                    "node_type": node["node_type"],
                    "input_data": node.get("input", {}),
                    "output_data": node.get("output", {}),
                    "duration_ms": node["duration_ms"],
                    "status": node["status"],
                    "error_message": node.get("error_message", ""),
                    "created_at": msg_time.isoformat()
                })
            
            if trace_nodes:
                traces.append({
                    "trace_id": f"txh_{session_id}_{turn_idx}",
                    "session_id": session_id,
                    "user_message": turn["user"],
                    "status": "completed",
                    "total_duration_ms": sum(n["duration_ms"] for n in trace_nodes),
                    "nodes": trace_nodes,
                    "created_at": msg_time.isoformat(),
                    "completed_at": msg_time.isoformat()
                })
        
        # 构建会话
        session = {
            "session_id": session_id,
            "user_id": user_id,
            "started_at": session_time.isoformat(),
            "ended_at": msg_time.isoformat(),
            "messages": messages,
            "user_profile": scenario.get("profile", {}),
            "total_messages": len(messages),
            "is_active": False
        }
        sessions.append(session)
        
        # 保存会话JSON文件
        save_json(os.path.join(CONVERSATION_LOG_DIR, f"{session_id}.json"), session)
        
        # 生成用户画像
        profiles[user_id] = {
            "user_id": user_id,
            **scenario.get("profile", {}),
            "completeness": 0.85 if scenario.get("profile", {}).get("age") else 0.3,
            "created_at": session_time.isoformat(),
            "updated_at": msg_time.isoformat()
        }
        
        # 生成Badcase
        if scenario.get("has_badcase"):
            badcase = scenario["badcase"]
            badcases.append({
                "id": f"bc_{session_id}",
                "session_id": session_id,
                "category": badcase["category"],
                "description": badcase["description"],
                "severity": badcase["severity"],
                "status": "open",
                "assigned_to": "产品团队",
                "conversation_snippet": badcase["conversation_snippet"],
                "created_at": msg_time.isoformat(),
                "updated_at": msg_time.isoformat(),
                "resolution": "",
                "resolution_time": None
            })
    
    # 保存汇总数据
    save_json(os.path.join(DATA_DIR, "sessions.json"), sessions)
    save_json(os.path.join(DATA_DIR, "traces.json"), traces)
    save_json(os.path.join(DATA_DIR, "model_calls.json"), model_calls)
    save_json(os.path.join(DATA_DIR, "badcases.json"), badcases)
    save_json(os.path.join(DATA_DIR, "profiles.json"), profiles)
    
    print(f"生成完成！")
    print(f"  对话会话: {len(sessions)} 条")
    print(f"  链路追踪: {len(traces)} 条")
    print(f"  模型调用: {len(model_calls)} 条")
    print(f"  Badcase: {len(badcases)} 条")
    print(f"  用户画像: {len(profiles)} 条")
    
    # 打印场景概览
    print("\n场景覆盖:")
    for s in SCENARIOS:
        bc_mark = " [有Badcase]" if s.get("has_badcase") else ""
        print(f"  - {s['title']} ({len(s['turns'])}轮){bc_mark}")

if __name__ == "__main__":
    generate_conversation_data()
