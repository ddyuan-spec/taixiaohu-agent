"""
泰小虎智能健康导购助手 - Web 界面服务
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
from agent import TaiXiaoHuAgent

app = Flask(__name__)

# 全局智能体实例（每个用户独立会话的场景下可改为字典管理）
agent = TaiXiaoHuAgent()


@app.route('/')
def index():
    """主页"""
    return render_template('index.html',
                           agent_name=agent.name,
                           welcome_msg=agent.get_welcome_message(),
                           intent_options=agent.get_intent_options())


@app.route('/api/chat', methods=['POST'])
def chat():
    """处理聊天请求"""
    try:
        data = request.json
        user_message = data.get('message', '')
        intent = data.get('intent')  # 客户端传入的意图

        if not user_message and not intent:
            return jsonify({'success': False, 'error': '消息不能为空'}), 400

        result = agent.process_message(user_message, intent=intent)

        return jsonify({
            'success': True,
            'response': result['response'],
            'state': result['state'],
            'intent': result['intent'],
            'profile_completeness': result.get('profile_completeness', 0)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
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
        return jsonify({
            'success': True,
            'message': '会话已重置',
            'welcome': agent.get_welcome_message()
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

    knowledge_stats = knowledge_service.get_stats()
    profile_stats = profile_service.get_stats()
    recent_sessions = session_service.get_recent_sessions(10)

    # 计算完整度分布百分比
    total = max(profile_stats.get('total_profiles', 0), 1)
    dist = profile_stats.get('completeness_distribution', {})
    profile_stats['dist_pct'] = {
        'low': round(dist.get('low', 0) * 100 / total),
        'medium': round(dist.get('medium', 0) * 100 / total),
        'high': round(dist.get('high', 0) * 100 / total),
    }

    return render_template('admin.html',
                           knowledge_stats=knowledge_stats,
                           profile_stats=profile_stats,
                           recent_sessions=recent_sessions)


@app.route('/admin/knowledge')
def admin_knowledge():
    """知识库管理页面"""
    from admin_service import knowledge_service

    chunks = knowledge_service.get_all_chunks()
    stats = knowledge_service.get_stats()

    return render_template('admin_knowledge.html',
                           chunks=chunks,
                           stats=stats)


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
    from admin_service import knowledge_service

    try:
        data = request.json
        chunk_id = data.get('id', '')

        if not chunk_id:
            return jsonify({'success': False, 'error': '切片ID不能为空'}), 400

        success = knowledge_service.delete_chunk(chunk_id)
        if success:
            return jsonify({'success': True, 'message': '切片已删除'})
        else:
            return jsonify({'success': False, 'error': '切片不存在'}), 404

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/profiles')
def admin_profiles():
    """用户画像管理页面"""
    from admin_service import profile_service

    profiles = profile_service.get_all_profiles()
    stats = profile_service.get_stats()

    return render_template('admin_profiles.html',
                           profiles=profiles,
                           stats=stats)


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
    from adapters.llm_adapter import llm_adapter, PRESET_MODELS
    config = llm_adapter.get_safe_config()
    return render_template('admin_llm.html',
                           config=config,
                           preset_models=PRESET_MODELS)


@app.route('/admin/llm/config', methods=['POST'])
def admin_llm_config():
    """保存 LLM 配置"""
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
    from adapters.llm_adapter import llm_adapter
    try:
        llm_adapter.reload_config()
        result = llm_adapter.test_connection()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    print("=" * 50)
    print("泰小虎智能健康导购助手")
    print("=" * 50)
    print("请在浏览器中访问: http://localhost:5000")
    print("后台管理: http://localhost:5000/admin")
    print("按 Ctrl+C 停止服务\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
