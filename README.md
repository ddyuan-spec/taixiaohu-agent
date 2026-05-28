# 🤖 智能体应用

基于 **Vibe Coding** 理念构建的智能体应用，支持自然语言对话、工具调用、记忆功能和多模态处理。

## ✨ 功能特性

- 💬 **自然语言对话** - 理解并回应用户的问题
- 🛠️ **工具调用** - 使用可用工具完成特定任务（时间、天气、计算、搜索）
- 🧠 **记忆功能** - 记住对话历史和用户偏好
- 🖼️ **多模态处理** - 支持文本和图片输入
- 🌐 **Web 界面** - 美观的现代化聊天界面
- 📱 **响应式设计** - 支持桌面和移动设备

## 🚀 快速开始

### 方式一：命令行运行

```bash
# 进入项目目录
cd smart_agent

# 运行智能体
python agent.py
```

### 方式二：Web 界面运行

```bash
# 安装依赖
pip install flask

# 运行 Web 服务
python web_interface.py
```

然后在浏览器中访问：`http://localhost:5000`

## 📖 使用说明

### 命令行交互

启动后，你可以：
- 直接输入消息与智能体对话
- 输入 `时间` 查询当前时间
- 输入 `天气` 查询天气信息
- 输入 `计算 1+1` 执行数学计算
- 输入 `状态` 查看智能体统计信息
- 输入 `清空` 清空对话记忆
- 输入 `退出` 结束对话

### Web 界面

- 💬 在输入框中输入消息，按 Enter 发送
- 📷 点击相机图标可以上传图片
- 🗑️ 点击垃圾桶图标清空对话
- 📊 点击图表图标查看统计信息

## 🏗️ 项目结构

```
smart_agent/
├── agent.py           # 智能体核心代码
├── web_interface.py   # Web 界面服务
├── templates/
│   └── index.html     # Web 界面模板
└── README.md          # 项目说明
```

## 🔧 扩展开发

### 添加新工具

```python
from agent import Tool

# 定义工具函数
def my_custom_tool(param1: str):
    return f"处理结果: {param1}"

# 创建工具
tool = Tool(
    name="我的工具",
    description="工具描述",
    parameters={"param1": "参数说明"},
    function=my_custom_tool
)

# 注册工具
agent.register_tool(tool)
```

### 接入大模型 API

在 `agent.py` 中，你可以将 `_generate_conversation_response` 方法替换为真实的大模型 API 调用：

```python
def _generate_conversation_response(self, user_input: str, image_data: Optional[str] = None) -> str:
    # 调用 OpenAI、Claude 或其他大模型 API
    # 使用 self.memory.get_context() 获取对话上下文
    # 返回模型生成的回复
    pass
```

## 🛠️ 技术栈

- **后端**: Python 3.8+
- **Web 框架**: Flask
- **前端**: HTML5 + CSS3 + JavaScript
- **架构**: 模块化设计，易于扩展

## 📝 示例对话

```
你: 你好
🤖 小智: 你好！我是小智，很高兴为您服务。

你: 现在几点了？
🤖 小智: 我已经为您处理了请求。[时间] 2024年01月15日 14:30:25

你: 帮我计算 123 * 456
🤖 小智: 我已经为您处理了请求。[计算] 123 * 456 = 56088

你: 北京天气怎么样？
🤖 小智: 我已经为您处理了请求。[天气] 北京今天晴朗，气温22°C
```

## 🎯 未来规划

- [ ] 接入真实的大模型 API（OpenAI、Claude 等）
- [ ] 支持更多工具（文件处理、数据分析等）
- [ ] 添加用户认证和对话持久化
- [ ] 支持语音输入和输出
- [ ] 多智能体协作功能

## 📄 许可证

MIT License

---

🌟 如果这个项目对你有帮助，欢迎 Star 和分享！
