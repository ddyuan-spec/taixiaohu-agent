"""
泰小虎智能健康导购助手 - Web 界面服务
"""

from flask import Flask, render_template, request, jsonify
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


if __name__ == '__main__':
    print("=" * 50)
    print("🐯 泰小虎智能健康导购助手")
    print("=" * 50)
    print("📱 请在浏览器中访问: http://localhost:5000")
    print("⚠️  按 Ctrl+C 停止服务\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
