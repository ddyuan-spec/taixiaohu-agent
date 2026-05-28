"""
一键更新脚本 - 为 taixiaohu-agent 添加 LLM 模型配置功能
使用方法：将此脚本和新增文件放到项目根目录对应位置，运行 python update_llm.py
"""

import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def copy_file(src, dst):
    """复制文件"""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    print(f"  [OK] {dst}")

def main():
    print("=" * 60)
    print("泰小虎智能体 - LLM 模型配置功能更新")
    print("=" * 60)

    # 1. 复制 LLM 适配器
    print("\n[1/6] 安装 LLM 适配器...")
    copy_file(
        os.path.join(BASE_DIR, "adapters", "llm_adapter.py"),
        os.path.join(BASE_DIR, "adapters", "llm_adapter.py")
    )

    # 2. 复制管理页面模板
    print("\n[2/6] 安装模型配置页面...")
    copy_file(
        os.path.join(BASE_DIR, "templates", "admin_llm.html"),
        os.path.join(BASE_DIR, "templates", "admin_llm.html")
    )

    # 3. 更新 web_interface.py - 添加 LLM 路由
    print("\n[3/6] 更新 web_interface.py ...")
    update_web_interface()

    # 4. 更新 agent.py - 接入真实 LLM
    print("\n[4/6] 更新 agent.py ...")
    update_agent()

    # 5. 更新 requirements.txt
    print("\n[5/6] 更新 requirements.txt ...")
    update_requirements()

    # 6. 更新其他后台模板的侧边栏（添加模型配置入口）
    print("\n[6/6] 更新后台模板侧边栏...")
    update_admin_templates()

    print("\n" + "=" * 60)
    print("更新完成！")
    print("请重启服务后访问: http://localhost:5000/admin/llm")
    print("=" * 60)


def update_web_interface():
    """在 web_interface.py 中添加 LLM 配置路由"""
    filepath = os.path.join(BASE_DIR, "web_interface.py")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 要插入的 LLM 路由代码
    llm_routes = '''

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
'''

    if 'admin/llm' not in content:
        # 在 __main__ 之前插入
        marker = "if __name__ == '__main__':"
        if marker in content:
            content = content.replace(marker, llm_routes + "\n" + marker)
        else:
            content += llm_routes

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print("  [OK] 已添加 LLM 路由")
    else:
        print("  [SKIP] LLM 路由已存在")


def update_agent():
    """修改 agent.py，接入真实 LLM"""
    filepath = os.path.join(BASE_DIR, "agent.py")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 在文件顶部 import 区域添加 LLM 导入
    llm_import = '''
# LLM 适配器（可选）
try:
    from adapters.llm_adapter import llm_adapter
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
'''

    if 'from adapters.llm_adapter' not in content:
        # 在最后一个 import 之后添加
        lines = content.split('\n')
        last_import_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                last_import_idx = i
        lines.insert(last_import_idx + 1, llm_import)
        content = '\n'.join(lines)

    # 添加 LLM 调用方法
    llm_method = '''
    def _call_llm(self, user_message: str, system_prompt: str = None) -> Optional[str]:
        """
        调用真实 LLM 获取回复
        返回 None 表示 LLM 不可用或调用失败
        """
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

        # 添加最近的对话历史（最多 10 轮）
        recent = self.messages[-20:] if len(self.messages) > 20 else self.messages
        for msg in recent:
            messages.append({"role": msg.role, "content": msg.content})

        # 添加当前用户消息
        messages.append({"role": "user", "content": user_message})

        result = llm_adapter.chat(messages)
        if result.success:
            return result.content
        else:
            print(f"[LLM Error] {result.error}")
            if llm_adapter.config.get("fallback_to_mock", True):
                return None  # 回退到模拟回复
            return f"抱歉，我现在遇到了一些技术问题：{result.error}"
'''

    if '_call_llm' not in content:
        # 在 process_message 方法之前插入
        marker = 'def process_message('
        if marker in content:
            content = content.replace(marker, llm_method + '\n    ' + marker)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print("  [OK] 已添加 LLM 调用支持")


def update_requirements():
    """更新 requirements.txt"""
    filepath = os.path.join(BASE_DIR, "requirements.txt")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if 'requests' not in content:
        content += '\nrequests>=2.28.0\n'
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print("  [OK] 已添加 requests 依赖")
    else:
        print("  [SKIP] requests 依赖已存在")


def update_admin_templates():
    """更新现有后台模板的侧边栏，添加模型配置入口"""
    templates_dir = os.path.join(BASE_DIR, "templates")
    sidebar_link = '''                    <a href="/admin/llm" class="nav-link">
                        <i class="bi bi-cpu"></i> 模型配置
                    </a>'''

    for filename in ['admin.html', 'admin_knowledge.html', 'admin_profiles.html']:
        filepath = os.path.join(templates_dir, filename)
        if not os.path.exists(filepath):
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        if '/admin/llm' in content:
            print(f"  [SKIP] {filename} 已包含模型配置入口")
            continue

        # 在"返回前台"链接之前插入
        marker = '<a href="/" class="nav-link">'
        if marker in content:
            content = content.replace(marker, sidebar_link + '\n                    ' + marker)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  [OK] {filename} 已添加模型配置入口")


if __name__ == '__main__':
    main()
