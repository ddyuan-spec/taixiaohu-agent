"""
泰小虎智能健康导购助手 - Web 界面服务
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from agent import TaiXiaoHuAgent
from agent_service import get_agent_service
import uuid
import os
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'taixiaohu_secret_key_2024'  # 用于session加密

# 全局智能体实例（每个用户独立会话的场景下可改为字典管理）
agent = TaiXiaoHuAgent()

# 新的智能体服务
agent_service = get_agent_service()


def get_session_id():
    """获取或创建会话ID"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']


@app.route('/')
def index():
    """主页"""
    return render_template('index.html',
                           agent_name=agent.name,
                           welcome_msg=agent.get_welcome_message(),
                           intent_options=agent.get_intent_options())


@app.route('/api/chat', methods=['POST'])
def chat():
    """处理聊天请求（使用AgentService，支持后台LLM配置）"""
    try:
        data = request.json
        user_message = data.get('message', '')
        session_id = data.get('session_id', 'default_session')
        user_id = data.get('user_id', '')

        if not user_message:
            return jsonify({'success': False, 'error': '消息不能为空'}), 400

        # 使用AgentService处理消息（支持后台LLM配置）
        from agent_service import get_agent_service
        agent_service = get_agent_service()
        result = agent_service.process_message(user_message, session_id, user_id)

        return jsonify({
            'success': True,
            'response': result['response'],
            'state': result['state'],
            'intent': result['intent'],
            'next_action': result.get('next_action', ''),
            'recommended_products': result.get('recommended_products', [])
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/intent', methods=['POST'])
def set_intent():
    """设置意图"""
    try:
        data = request.json
        intent = data.get('intent')
        message = data.get('message', '')

        result = agent.process_message(message, intent=intent)

        return jsonify({
            'success': True,
            'response': result['response'],
            'state': result['state'],
            'intent': result['intent']
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/profile/start', methods=['POST'])
def start_profile():
    """开始画像收集"""
    try:
        agent.start_profile_collect()
        first_question = "您好！我想更好地为您服务。如果您方便的话，可以告诉我您的年龄和性别吗？您的信息我会严格保密哦~"
        return jsonify({
            'success': True,
            'response': first_question,
            'state': 'profile_collect'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/history', methods=['GET'])
def get_history():
    """获取对话历史"""
    try:
        history = agent.get_conversation_history()
        return jsonify({'success': True, 'history': history})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/clear', methods=['POST'])
def clear_session():
    """清空会话"""
    try:
        agent.clear_session()
        # 同时清除新服务的会话
        session_id = get_session_id()
        agent_service.clear_session(session_id)
        # 清除flask session
        session.clear()
        return jsonify({
            'success': True,
            'message': '会话已重置',
            'welcome': agent.get_welcome_message()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# 新的智能体API（使用AgentService）
# ============================================================

@app.route('/api/v2/chat', methods=['POST'])
def chat_v2():
    """新的聊天API - 使用AgentService"""
    try:
        data = request.json
        user_message = data.get('message', '')
        # 优先使用传入的session_id，否则使用flask session
        session_id = data.get('session_id') or get_session_id()
        user_id = data.get('user_id', '')
        
        if not user_message:
            return jsonify({'success': False, 'error': '消息不能为空'}), 400
        
        # 使用新的AgentService处理消息
        result = agent_service.process_message(user_message, session_id, user_id)
        
        return jsonify({
            'success': True,
            'response': result['response'],
            'state': result['state'],
            'intent': result['intent'],
            'is_emergency': result['is_emergency'],
            'emergency_level': result.get('emergency_level'),
            'recommended_products': result.get('recommended_products', []),
            'context_summary': result.get('context_summary', {}),
            'session_id': session_id
        })
        
    except Exception as e:
        import traceback
        print(f"Error in chat_v2: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/v2/products', methods=['GET'])
def list_products_v2():
    """获取产品列表"""
    try:
        products = agent_service.list_products()
        return jsonify({
            'success': True,
            'products': products
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/v2/products/faq', methods=['POST'])
def product_faq_v2():
    """获取产品FAQ"""
    try:
        data = request.json
        product_name = data.get('product_name', '')
        question = data.get('question', '')
        
        if not product_name:
            return jsonify({'success': False, 'error': '产品名称不能为空'}), 400
        
        response = agent_service.get_product_faq(product_name, question)
        return jsonify({
            'success': True,
            'response': response
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/v2/llm/status', methods=['GET'])
def llm_status_v2():
    """获取LLM状态"""
    try:
        status = agent_service.get_llm_status()
        return jsonify({
            'success': True,
            **status
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/v2/llm/test', methods=['POST'])
def llm_test_v2():
    """测试LLM连接"""
    try:
        result = agent_service.test_llm_connection()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# 对话记录管理API
# ============================================================
@app.route('/api/v2/conversations', methods=['GET'])
def list_conversations():
    """获取对话记录列表"""
    try:
        from conversation_logger import get_conversation_logger
        logger = get_conversation_logger()
        
        # 强制重新加载数据（确保Railway上数据最新）
        logger._load_existing_sessions()
        
        limit = request.args.get('limit', 100, type=int)
        sessions = logger.get_all_sessions(limit=limit)
        
        result_sessions = []
        for s in sessions:
            # 统计知识库调用次数
            kb_calls = 0
            for msg in s.messages:
                if isinstance(msg, dict):
                    kb_calls += len(msg.get('knowledge_base_calls', []))
                else:
                    kb_calls += len(msg.knowledge_base_calls) if hasattr(msg, 'knowledge_base_calls') else 0
            
            result_sessions.append({
                'session_id': s.session_id,
                'user_id': s.user_id,
                'started_at': s.started_at,
                'ended_at': s.ended_at,
                'total_messages': s.total_messages,
                'kb_calls': kb_calls,
                'is_active': s.is_active,
                'user_profile': s.user_profile
            })
        
        return jsonify({
            'success': True,
            'sessions': result_sessions
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/v2/conversations/<session_id>', methods=['GET'])
def get_conversation_detail(session_id):
    """获取对话详情"""
    try:
        from conversation_logger import get_conversation_logger
        logger = get_conversation_logger()
        logger._load_existing_sessions()
        
        session = logger.get_session(session_id)
        if not session:
            return jsonify({'success': False, 'error': '会话不存在'}), 404
        
        return jsonify({
            'success': True,
            'session': session.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/v2/conversations/<session_id>', methods=['DELETE'])
def delete_conversation(session_id):
    """删除对话记录"""
    try:
        from conversation_logger import get_conversation_logger, CONVERSATION_LOG_DIR
        import os
        
        logger = get_conversation_logger()
        
        # 从内存中删除
        if session_id in logger.sessions:
            del logger.sessions[session_id]
        
        # 从文件中删除
        filepath = os.path.join(CONVERSATION_LOG_DIR, f"{session_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
        
        return jsonify({'success': True, 'message': '对话记录已删除'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/v2/kb/stats', methods=['GET'])
def get_kb_stats():
    """获取知识库调用统计"""
    try:
        from conversation_logger import get_conversation_logger
        logger = get_conversation_logger()
        
        stats = logger.get_knowledge_base_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/v2/kb/chunks', methods=['GET'])
def get_kb_chunks():
    """获取知识切片列表"""
    try:
        from admin_service import knowledge_service
        chunks = knowledge_service.get_all_chunks()
        
        # 获取统计
        stats = knowledge_service.get_stats()
        
        return jsonify({
            'success': True,
            'chunks': chunks,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/v2/kb/call-records', methods=['GET'])
def get_kb_call_records():
    """获取知识库调用记录（最近调用）"""
    try:
        from conversation_logger import get_conversation_logger
        from product_retriever import create_product_retriever
        
        # 加载产品知识库
        retriever = create_product_retriever()
        logger = get_conversation_logger()
        
        # 从磁盘刷新会话数据
        logger._load_existing_sessions()
        
        # 获取所有调用记录并按时间排序
        all_calls = []
        for session in logger.sessions.values():
            for msg in session.messages:
                # 处理dict或dataclass
                if isinstance(msg, dict):
                    kb_calls = msg.get('knowledge_base_calls', [])
                else:
                    kb_calls = msg.knowledge_base_calls if hasattr(msg, 'knowledge_base_calls') and isinstance(msg.knowledge_base_calls, list) else []
                for call in kb_calls:
                    # 处理dict或dataclass
                    if isinstance(call, dict):
                        call_dict = call
                    else:
                        call_dict = {
                            'query': call.query,
                            'intent': call.intent,
                            'results_count': call.results_count,
                            'product_ids': call.product_ids,
                            'response_time_ms': call.response_time_ms,
                            'timestamp': call.timestamp
                        }
                    
                    # 查找对应的产品名称
                    product_names = []
                    for pid in call_dict.get('product_ids', []):
                        product = retriever.get_product_by_id(pid)
                        if product:
                            product_names.append(product.get('product_name', pid))
                        else:
                            product_names.append(pid)
                    
                    all_calls.append({
                        'session_id': session.session_id,
                        'product_ids': call_dict.get('product_ids', []),
                        'product_names': product_names,
                        'query': call_dict.get('query', ''),
                        'intent': call_dict.get('intent', ''),
                        'results_count': call_dict.get('results_count', 0),
                        'response_time_ms': call_dict.get('response_time_ms', 0),
                        'timestamp': call_dict.get('timestamp', '')
                    })
        
        # 按时间倒序
        all_calls.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        limit = request.args.get('limit', 50, type=int)
        
        return jsonify({
            'success': True,
            'records': all_calls[:limit]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/v2/llm/records', methods=['GET'])
def get_llm_records():
    """获取LLM调用记录"""
    try:
        from conversation_logger import get_conversation_logger
        logger = get_conversation_logger()
        logger._load_existing_sessions()
        
        # 收集所有LLM调用
        all_calls = []
        for session in logger.sessions.values():
            for msg in session.messages:
                # 处理dict或dataclass
                if isinstance(msg, dict):
                    llm_calls = msg.get('llm_calls', [])
                else:
                    llm_calls = msg.llm_calls if hasattr(msg, 'llm_calls') and isinstance(msg.llm_calls, list) else []
                for call in llm_calls:
                    # 处理dict或dataclass
                    if isinstance(call, dict):
                        call_dict = call
                    else:
                        call_dict = {
                            'module': call.module,
                            'prompt_tokens': call.prompt_tokens,
                            'completion_tokens': call.completion_tokens,
                            'total_tokens': call.total_tokens,
                            'response_time_ms': call.response_time_ms,
                            'success': call.success,
                            'error_message': call.error_message,
                            'timestamp': call.timestamp
                        }
                    call_dict['session_id'] = session.session_id
                    all_calls.append(call_dict)
        
        # 按时间倒序
        all_calls.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        limit = request.args.get('limit', 50, type=int)
        
        # 统计
        total_calls = len(all_calls)
        total_tokens = sum(c.get('total_tokens', 0) for c in all_calls)
        avg_time = sum(c.get('response_time_ms', 0) for c in all_calls) / total_calls if total_calls > 0 else 0
        success_count = sum(1 for c in all_calls if c.get('success', False))
        
        return jsonify({
            'success': True,
            'records': all_calls[:limit],
            'stats': {
                'total_calls': total_calls,
                'total_tokens': total_tokens,
                'avg_response_time_ms': round(avg_time, 2),
                'success_rate': round(success_count / total_calls * 100, 2) if total_calls > 0 else 0
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取统计信息"""
    try:
        stats = agent.get_stats()
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# 后台管理系统路由
# ============================================================

@app.route('/admin')
def admin_dashboard():
    """后台首页仪表盘"""
    from admin_service import knowledge_service, profile_service, session_service
    from conversation_logger import get_conversation_logger

    knowledge_stats = knowledge_service.get_stats()
    profile_stats = profile_service.get_stats()
    recent_sessions = session_service.get_recent_sessions(10)

    # 计算完整度分布百分比
    total = max(profile_stats.get('total_profiles', 0), 1)
    dist = profile_stats.get('distribution', {})
    profile_stats['dist_pct'] = {
        'low': round(dist.get('low', 0) * 100 / total),
        'medium': round(dist.get('medium', 0) * 100 / total),
        'high': round(dist.get('high', 0) * 100 / total),
    }

    # 获取LLM统计
    logger = get_conversation_logger()
    logger._load_existing_sessions()
    llm_stats = {
        'total_calls': 0,
        'total_tokens': 0,
        'avg_response_time_ms': 0,
        'success_rate': 0
    }
    try:
        llm_all_calls = []
        for session in logger.sessions.values():
            for msg in session.messages:
                if isinstance(msg, dict):
                    calls = msg.get('llm_calls', [])
                else:
                    calls = msg.llm_calls if hasattr(msg, 'llm_calls') and isinstance(msg.llm_calls, list) else []
                for call in calls:
                    if isinstance(call, dict):
                        llm_all_calls.append(call)
        if llm_all_calls:
            llm_stats['total_calls'] = len(llm_all_calls)
            llm_stats['total_tokens'] = sum(c.get('total_tokens', 0) for c in llm_all_calls)
            avg_time = sum(c.get('response_time_ms', 0) for c in llm_all_calls) / len(llm_all_calls)
            llm_stats['avg_response_time_ms'] = round(avg_time, 0)
            success_count = sum(1 for c in llm_all_calls if c.get('success', False))
            llm_stats['success_rate'] = round(success_count / len(llm_all_calls) * 100, 1)
    except Exception as e:
        print(f"[LLM统计错误] {e}")

    return render_template('admin.html',
                           knowledge_stats=knowledge_stats,
                           profile_stats=profile_stats,
                           recent_sessions=recent_sessions,
                           llm_stats=llm_stats)


@app.route('/admin/knowledge')
def admin_knowledge():
    """知识库管理页面 - 重定向到知识上传"""
    from flask import redirect
    return redirect('/admin/knowledge/upload')


@app.route('/admin/knowledge/upload')
def admin_knowledge_upload_page():
    """知识上传页面"""
    return render_template('admin_knowledge_upload.html')


@app.route('/admin/knowledge/chunks')
def admin_knowledge_chunks_page():
    """知识切片列表页面"""
    from admin_service import knowledge_service
    chunks = knowledge_service.get_all_chunks()
    stats = knowledge_service.get_stats()
    return render_template('admin_knowledge_chunks.html',
                           chunks=chunks,
                           stats=stats)


@app.route('/admin/knowledge/call-records')
def admin_knowledge_call_records_page():
    """知识库调用记录页面"""
    return render_template('admin_kb_calls.html')


@app.route('/admin/knowledge/upload', methods=['POST'])
def admin_knowledge_upload():
    """上传知识库文件"""
    from admin_service import knowledge_service

    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '请选择文件'}), 400

        file = request.files['file']
        if not file.filename:
            return jsonify({'success': False, 'error': '文件名为空'}), 400

        # 检查文件类型
        allowed_ext = {'txt', 'md', 'csv', 'json'}
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if ext not in allowed_ext:
            return jsonify({'success': False, 'error': f'不支持的文件类型，仅支持: {", ".join(allowed_ext)}'}), 400

        # 读取文件内容
        content = file.read().decode('utf-8')

        # 切片并保存
        new_chunks = knowledge_service.upload_and_slice(content, file.filename)

        return jsonify({
            'success': True,
            'message': f'文件上传成功，生成 {len(new_chunks)} 个切片',
            'chunk_count': len(new_chunks)
        })

    except UnicodeDecodeError:
        return jsonify({'success': False, 'error': '文件编码错误，请使用 UTF-8 编码'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/knowledge/add', methods=['POST'])
def admin_knowledge_add():
    """手动添加知识切片"""
    from admin_service import knowledge_service

    try:
        data = request.json
        title = data.get('title', '').strip()
        content = data.get('content', '').strip()

        if not title or not content:
            return jsonify({'success': False, 'error': '标题和内容不能为空'}), 400

        chunk = knowledge_service.add_chunk(title, content)

        return jsonify({
            'success': True,
            'message': '切片添加成功',
            'chunk': chunk
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/knowledge/delete', methods=['POST'])
def admin_knowledge_delete():
    """删除知识切片"""
    try:
        data = request.json
        chunk_id = data.get('id')
        if not chunk_id:
            return jsonify({'success': False, 'error': '缺少切片ID'}), 400
        success = knowledge_service.delete_chunk(chunk_id)
        if success:
            return jsonify({'success': True, 'message': '切片已删除'})
        else:
            return jsonify({'success': False, 'error': '切片不存在'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/knowledge/pull', methods=['POST'])
def admin_knowledge_pull():
    """从 GitHub 手动拉取知识库"""
    from admin_service import knowledge_service
    try:
        result = knowledge_service.load_from_github()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': f'拉取失败: {str(e)}'}), 500


@app.route('/admin/profiles')
def admin_profiles():
    """用户画像管理页面"""
    from admin_service import profile_service

    profiles = profile_service.get_all_profiles()
    stats = profile_service.get_stats()

    return render_template('admin_profiles.html',
                           profiles=profiles,
                           stats=stats)


@app.route('/api/admin/profiles', methods=['POST'])
def api_create_profile():
    """手动创建用户画像"""
    try:
        from admin_service import profile_service
        data = request.json or {}
        user_id = data.get('user_id', '').strip()
        if not user_id:
            return jsonify({'success': False, 'error': '用户ID不能为空'}), 400
        # 检查是否已存在
        existing = profile_service.get_profile_by_id(user_id)
        if existing:
            return jsonify({'success': False, 'error': '该用户ID已存在'}), 409
        # 构建画像数据
        profile_data = {
            'user_id': user_id,
            'name': data.get('name', ''),
            'age': data.get('age', ''),
            'gender': data.get('gender', ''),
            'chronic_diseases': data.get('chronic_diseases', ''),
            'allergy_history': data.get('allergy_history', ''),
            'current_medication': data.get('current_medication', ''),
            'health_concerns': data.get('health_concerns', ''),
            'completeness': 0.3,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        # 计算完整度
        filled = sum(1 for v in [profile_data['name'], profile_data['age'], profile_data['gender'],
                                   profile_data['chronic_diseases'], profile_data['allergy_history'],
                                   profile_data['current_medication'], profile_data['health_concerns']] if v)
        profile_data['completeness'] = round(filled / 6, 2)
        profile_service.create_profile(profile_data)
        return jsonify({'success': True, 'profile': profile_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/profiles/<user_id>', methods=['GET'])
def api_get_profile(user_id):
    """获取指定用户画像（JSON格式）"""
    try:
        from admin_service import profile_service
        profile = profile_service.get_profile_by_id(user_id)
        if not profile:
            return jsonify({'success': False, 'error': '用户画像不存在'}), 404
        return jsonify({'success': True, 'profile': profile})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/profiles/<user_id>', methods=['PUT'])
def api_update_profile(user_id):
    """更新指定用户画像"""
    try:
        from admin_service import profile_service
        data = request.json or {}
        updated = profile_service.update_profile(user_id, data)
        if not updated:
            return jsonify({'success': False, 'error': '用户画像不存在或更新失败'}), 404
        return jsonify({'success': True, 'profile': updated})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/profiles/<user_id>')
def admin_profile_detail(user_id):
    """用户画像详情页面"""
    from admin_service import profile_service

    profile = profile_service.get_profile_by_id(user_id)
    if not profile:
        return redirect(url_for('admin_profiles'))

    history = profile_service.get_profile_history(user_id)
    sessions = profile_service.get_profile_sessions(user_id)

    return render_template('admin_profiles.html',
                           profiles=profile_service.get_all_profiles(),
                           stats=profile_service.get_stats(),
                           detail_profile=profile,
                           detail_history=history,
                           detail_sessions=sessions)


@app.route('/admin/api/save_session', methods=['POST'])
def admin_save_session():
    """手动保存当前会话的画像和消息"""
    try:
        agent.save_current_profile()
        return jsonify({'success': True, 'message': '画像和会话已保存'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# LLM 模型配置路由
# ============================================================
@app.route('/admin/llm')
def admin_llm():
    """LLM 模型配置页面"""
    import sys
    import os
    # 添加父目录到路径
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from adapters.llm_adapter import llm_adapter, PRESET_MODELS
    config = llm_adapter.get_safe_config()
    return render_template('admin_llm.html',
                           config=config,
                           preset_models=PRESET_MODELS)


@app.route('/admin/llm/config', methods=['POST'])
def admin_llm_config():
    """保存 LLM 配置"""
    import sys
    import os
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from adapters.llm_adapter import llm_adapter, save_llm_config
    try:
        data = request.json
        save_llm_config(data)
        llm_adapter.reload_config()
        return jsonify({'success': True, 'message': '配置已保存'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/admin/llm/test', methods=['POST'])
def admin_llm_test():
    """测试 LLM 连接"""
    import sys
    import os
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from adapters.llm_adapter import llm_adapter
    try:
        llm_adapter.reload_config()
        result = llm_adapter.test_connection()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# 提示词配置路由 (新版 - 16模块管理)
# ============================================================
PROMPTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'prompts.json')

def _load_prompts():
    """加载提示词配置"""
    if os.path.exists(PROMPTS_FILE):
        try:
            with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_prompts(prompts):
    """保存提示词配置"""
    os.makedirs(os.path.dirname(PROMPTS_FILE), exist_ok=True)
    with open(PROMPTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(prompts, f, ensure_ascii=False, indent=2)


@app.route('/admin/prompt')
def admin_prompt():
    """提示词配置页面"""
    return render_template('admin_prompt.html')


@app.route('/api/admin/prompts', methods=['GET'])
def api_list_prompts():
    """获取所有提示词配置"""
    try:
        prompts = _load_prompts()
        return jsonify({'success': True, 'prompts': prompts})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/prompts/<prompt_id>', methods=['GET'])
def api_get_prompt(prompt_id):
    """获取单个提示词配置"""
    try:
        prompts = _load_prompts()
        prompt = prompts.get(prompt_id)
        if not prompt:
            return jsonify({'success': False, 'error': '提示词不存在'}), 404
        return jsonify({'success': True, 'prompt': prompt})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/prompts/<prompt_id>', methods=['PUT'])
def api_update_prompt(prompt_id):
    """更新提示词配置"""
    try:
        prompts = _load_prompts()
        data = request.json or {}
        prompts[prompt_id] = data
        _save_prompts(prompts)
        return jsonify({'success': True, 'prompt': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/prompts/import', methods=['POST'])
def api_import_prompts():
    """批量导入提示词"""
    try:
        data = request.json or {}
        imported = data.get('prompts', {})
        if not imported:
            return jsonify({'success': False, 'error': '导入数据为空'}), 400
        _save_prompts(imported)
        return jsonify({'success': True, 'message': f'成功导入 {len(imported)} 个模块'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/prompt/save', methods=['POST'])
def admin_prompt_save_legacy():
    """保存提示词配置（兼容旧版）"""
    try:
        data = request.json
        prompt_name = data.get('name')
        prompt_content = data.get('content')

        if not prompt_name or prompt_content is None:
            return jsonify({'success': False, 'error': '提示词名称和内容不能为空'}), 400

        from llm_service import get_llm_service
        llm_service = get_llm_service()
        if llm_service:
            llm_service.update_prompt(prompt_name, prompt_content)

        return jsonify({'success': True, 'message': '提示词已保存'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/conversations')
def admin_conversations():
    """对话记录管理页面"""
    return render_template('admin_conversations.html')


# ============================================================
# 新增功能 API 路由
# ============================================================

# ---------- Badcase 管理 API ----------
@app.route('/api/admin/badcases', methods=['GET'])
def list_badcases():
    """获取Badcase列表"""
    try:
        from data_service import get_badcase_service
        service = get_badcase_service()
        status = request.args.get('status')
        category = request.args.get('category')
        limit = request.args.get('limit', 100, type=int)
        return jsonify({'success': True, 'badcases': service.list_badcases(status, category, limit)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/badcases', methods=['POST'])
def create_badcase():
    """创建Badcase"""
    try:
        from data_service import get_badcase_service
        service = get_badcase_service()
        data = request.json
        badcase = service.create_badcase(
            session_id=data.get('session_id', ''),
            category=data.get('category', 'other'),
            description=data.get('description', ''),
            severity=data.get('severity', 'medium'),
            assigned_to=data.get('assigned_to', ''),
            conversation_snippet=data.get('conversation_snippet', '')
        )
        return jsonify({'success': True, 'badcase': badcase})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/badcases/<badcase_id>', methods=['PUT'])
def update_badcase(badcase_id):
    """更新Badcase"""
    try:
        from data_service import get_badcase_service
        service = get_badcase_service()
        data = request.json
        badcase = service.update_badcase(badcase_id, data)
        if badcase:
            return jsonify({'success': True, 'badcase': badcase})
        return jsonify({'success': False, 'error': 'Badcase不存在'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/badcases/stats', methods=['GET'])
def get_badcase_stats():
    """获取Badcase统计"""
    try:
        from data_service import get_badcase_service
        service = get_badcase_service()
        return jsonify({'success': True, 'stats': service.get_stats()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------- 模型调用记录 API ----------
@app.route('/api/admin/model-calls', methods=['GET'])
def list_model_calls():
    """获取模型调用记录"""
    try:
        from data_service import get_model_call_service
        service = get_model_call_service()
        model_name = request.args.get('model_name')
        module_type = request.args.get('module_type')
        status = request.args.get('status')
        limit = request.args.get('limit', 100, type=int)
        return jsonify({'success': True, 'calls': service.list_calls(model_name, module_type, status, limit)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/model-calls/stats', methods=['GET'])
def get_model_call_stats():
    """获取模型调用统计"""
    try:
        from data_service import get_model_call_service
        service = get_model_call_service()
        days = request.args.get('days', 7, type=int)
        return jsonify({'success': True, 'stats': service.get_stats(days)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/model-calls/<call_id>', methods=['GET'])
def get_model_call(call_id):
    """获取单条模型调用记录"""
    try:
        from data_service import get_model_call_service
        service = get_model_call_service()
        call = service.get_call(call_id)
        if call:
            return jsonify({'success': True, 'call': call})
        return jsonify({'success': False, 'error': '调用记录不存在'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------- 调用链路追踪 API ----------
@app.route('/api/admin/traces', methods=['GET'])
def list_traces():
    """获取链路追踪列表"""
    try:
        from data_service import get_trace_service
        service = get_trace_service()
        session_id = request.args.get('session_id')
        limit = request.args.get('limit', 50, type=int)
        return jsonify({'success': True, 'traces': service.list_traces(session_id, limit)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/traces/<trace_id>', methods=['GET'])
def get_trace_detail(trace_id):
    """获取链路详情"""
    try:
        from data_service import get_trace_service
        service = get_trace_service()
        trace = service.get_trace(trace_id)
        if trace:
            return jsonify({'success': True, 'trace': trace})
        return jsonify({'success': False, 'error': '链路不存在'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/traces/by-session/<session_id>', methods=['GET'])
def get_traces_by_session(session_id):
    """根据会话ID获取链路追踪列表"""
    try:
        from data_service import get_trace_service
        service = get_trace_service()
        traces = service.list_traces(session_id=session_id)
        return jsonify({'success': True, 'traces': traces})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------- 积分体系 API ----------
@app.route('/api/points/balance', methods=['GET'])
def get_points_balance():
    """获取积分余额"""
    try:
        from data_service import get_points_service
        service = get_points_service()
        session_id = request.args.get('session_id', 'default')
        return jsonify(service.get_balance(session_id))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/points/transactions', methods=['GET'])
def get_points_transactions():
    """获取积分流水"""
    try:
        from data_service import get_points_service
        service = get_points_service()
        session_id = request.args.get('session_id', 'default')
        limit = request.args.get('limit', 50, type=int)
        return jsonify({'success': True, 'transactions': service.get_transactions(session_id, limit)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/points/earn', methods=['POST'])
def earn_points():
    """积分获取（内部调用）"""
    try:
        from data_service import get_points_service
        service = get_points_service()
        data = request.json
        return jsonify(service.earn_points(
            data.get('session_id', 'default'),
            data.get('source', 'manual'),
            data.get('points', 0),
            data.get('description', '')
        ))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------- 打卡 API ----------
@app.route('/api/points/checkin', methods=['POST'])
def do_checkin():
    """每日打卡"""
    try:
        from data_service import get_checkin_service
        service = get_checkin_service()
        data = request.json
        return jsonify(service.checkin(data.get('session_id', 'default')))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/points/checkin/status', methods=['GET'])
def get_checkin_status():
    """获取打卡状态"""
    try:
        from data_service import get_checkin_service
        service = get_checkin_service()
        session_id = request.args.get('session_id', 'default')
        return jsonify(service.get_status(session_id))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------- 分享 API ----------
@app.route('/api/points/share', methods=['POST'])
def create_share():
    """创建分享"""
    try:
        from data_service import get_share_service
        service = get_share_service()
        data = request.json
        return jsonify(service.create_share(data.get('session_id', 'default')))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/points/share/verify', methods=['POST'])
def verify_share():
    """验证分享码"""
    try:
        from data_service import get_share_service
        service = get_share_service()
        data = request.json
        return jsonify(service.verify_share(
            data.get('share_code', ''),
            data.get('visitor_session_id', 'default')
        ))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------- 积分等级 API ----------
@app.route('/api/points/level', methods=['GET'])
def get_user_level():
    """获取用户等级"""
    try:
        from data_service import get_level_service
        service = get_level_service()
        session_id = request.args.get('session_id', 'default')
        return jsonify(service.get_user_level(session_id))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/points/levels', methods=['GET'])
def get_all_levels():
    """获取所有等级配置"""
    try:
        from data_service import get_level_service
        service = get_level_service()
        return jsonify({'success': True, 'levels': service.get_all_levels()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------- 积分商城 API ----------
@app.route('/api/shop/products', methods=['GET'])
def list_shop_products():
    """获取商城商品列表"""
    try:
        from data_service import get_shop_service
        service = get_shop_service()
        product_type = request.args.get('type')
        return jsonify({'success': True, 'products': service.list_products(product_type)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/shop/exchange', methods=['POST'])
def exchange_product():
    """兑换商品"""
    try:
        from data_service import get_shop_service
        service = get_shop_service()
        data = request.json
        return jsonify(service.exchange(
            data.get('session_id', 'default'),
            data.get('product_id', '')
        ))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/shop/exchange-records', methods=['GET'])
def get_exchange_records():
    """获取兑换记录"""
    try:
        from data_service import get_shop_service
        service = get_shop_service()
        session_id = request.args.get('session_id', 'default')
        return jsonify({'success': True, 'records': service.get_exchange_records(session_id)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------- 积分配置后台 API ----------
@app.route('/api/admin/points-config', methods=['GET'])
def get_points_config():
    """获取积分配置"""
    try:
        from data_service import get_points_service
        service = get_points_service()
        return jsonify({'success': True, 'config': service.get_config()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/points-config', methods=['PUT'])
def update_points_config():
    """更新积分配置"""
    try:
        from data_service import get_points_service
        service = get_points_service()
        data = request.json
        return jsonify({'success': True, 'config': service.update_config(data)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------- 对话记录筛选增强 API ----------
@app.route('/api/admin/conversations/filter', methods=['GET'])
def filter_conversations():
    """筛选对话记录"""
    try:
        from conversation_logger import get_conversation_logger
        logger = get_conversation_logger()
        logger._load_existing_sessions()
        
        keyword = request.args.get('keyword', '').lower()
        intent = request.args.get('intent')
        has_kb = request.args.get('has_kb')
        min_turns = request.args.get('min_turns', type=int)
        max_turns = request.args.get('max_turns', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        sort_by = request.args.get('sort_by', 'started_at')
        order = request.args.get('order', 'desc')
        limit = request.args.get('limit', 100, type=int)
        
        sessions = []
        for s in logger.sessions.values():
            # 关键词筛选
            if keyword:
                found = False
                for msg in s.messages:
                    content = msg.get('content', '') if isinstance(msg, dict) else getattr(msg, 'content', '')
                    if keyword in content.lower():
                        found = True
                        break
                if not found:
                    continue
            
            # 意图筛选
            if intent:
                msg_intents = []
                for msg in s.messages:
                    msg_intent = msg.get('intent', '') if isinstance(msg, dict) else getattr(msg, 'intent', '')
                    if msg_intent:
                        msg_intents.append(msg_intent)
                if intent not in msg_intents:
                    continue
            
            # 知识库调用筛选
            if has_kb is not None:
                has_kb_calls = False
                for msg in s.messages:
                    kb_calls = msg.get('knowledge_base_calls', []) if isinstance(msg, dict) else getattr(msg, 'knowledge_base_calls', [])
                    if kb_calls:
                        has_kb_calls = True
                        break
                if has_kb == 'true' and not has_kb_calls:
                    continue
                if has_kb == 'false' and has_kb_calls:
                    continue
            
            # 轮数筛选
            msg_count = len(s.messages)
            if min_turns and msg_count < min_turns:
                continue
            if max_turns and msg_count > max_turns:
                continue
            
            # 时间筛选
            if start_date and s.started_at < start_date:
                continue
            if end_date and s.started_at > end_date:
                continue
            
            sessions.append({
                'session_id': s.session_id,
                'user_id': s.user_id,
                'started_at': s.started_at,
                'ended_at': s.ended_at,
                'total_messages': len(s.messages),
                'is_active': s.is_active
            })
        
        # 排序
        reverse = order == 'desc'
        sessions.sort(key=lambda x: x.get(sort_by, ''), reverse=reverse)
        
        return jsonify({'success': True, 'sessions': sessions[:limit], 'total': len(sessions)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------- 数据导出 API ----------
@app.route('/api/admin/export/conversations', methods=['POST'])
def export_conversations():
    """导出对话记录"""
    try:
        import csv
        import io
        from conversation_logger import get_conversation_logger
        
        logger = get_conversation_logger()
        logger._load_existing_sessions()
        
        data = request.json or {}
        session_ids = data.get('session_ids', [])
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['session_id', 'timestamp', 'message_type', 'content', 'intent', 'recommended_products'])
        
        for s in logger.sessions.values():
            if session_ids and s.session_id not in session_ids:
                continue
            for msg in s.messages:
                if isinstance(msg, dict):
                    writer.writerow([
                        s.session_id,
                        msg.get('timestamp', ''),
                        msg.get('message_type', ''),
                        msg.get('content', '')[:200],
                        msg.get('intent', ''),
                        ','.join(msg.get('recommended_products', []))
                    ])
        
        output.seek(0)
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=conversations.csv'}
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------- 新增后台管理页面 ----------
@app.route('/admin/badcases')
def admin_badcases():
    """Badcase管理页面"""
    return render_template('admin_badcases.html')


@app.route('/admin/model-calls')
def admin_model_calls():
    """模型调用记录页面"""
    return render_template('admin_model_calls.html')


@app.route('/admin/traces')
def admin_traces():
    """调用链路追踪页面"""
    return render_template('admin_traces.html')


@app.route('/admin/points')
def admin_points():
    """积分管理页面"""
    return render_template('admin_points.html')


@app.route('/admin/points/config')
def admin_points_config():
    """积分配置页面"""
    return render_template('admin_points_config.html')


@app.route('/admin/shop')
def admin_shop():
    """积分商城管理页面"""
    return render_template('admin_shop.html')


@app.route('/admin/data-export')
def admin_data_export():
    """数据导出页面"""
    return render_template('admin_data_export.html')


# ============================================================
# 启动时预加载数据
# ============================================================
def preload_data():
    """启动时预加载所有数据"""
    print("[Startup] 正在预加载数据...")
    try:
        from conversation_logger import get_conversation_logger, CONVERSATION_LOG_DIR
        import os
        print(f"[Startup] 数据目录: {CONVERSATION_LOG_DIR}")
        print(f"[Startup] 目录是否存在: {os.path.exists(CONVERSATION_LOG_DIR)}")
        if os.path.exists(CONVERSATION_LOG_DIR):
            files = os.listdir(CONVERSATION_LOG_DIR)
            print(f"[Startup] 目录内容: {files}")
        logger = get_conversation_logger()
        logger._load_existing_sessions()
        print(f"[Startup] 已加载 {len(logger.sessions)} 个对话会话")
    except Exception as e:
        print(f"[Startup] 预加载数据失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    with app.app_context():
        preload_data()
    
    print("=" * 50)
    print("泰小虎智能健康导购助手")
    print("=" * 50)
    print(f"请在浏览器中访问: http://localhost:{port}")
    print(f"后台管理: http://localhost:{port}/admin")
    print("按 Ctrl+C 停止服务\n")

    app.run(debug=debug, host='0.0.0.0', port=port)
else:
    # Gunicorn / Railway 部署模式
    with app.app_context():
        preload_data()
