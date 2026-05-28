# GitHub 部署指南

将泰小虎智能体部署到 GitHub Pages

## 快速部署

### 1. 创建 GitHub 仓库

```bash
# 在 GitHub 上创建新仓库，命名为 taixiaohu
# 然后本地初始化

cd smart_agent
git init
git add .
git commit -m "Initial commit: 泰小虎智能健康导购助手"
git branch -M main
git remote add origin https://github.com/yourusername/taixiaohu.git
git push -u origin main
```

### 2. 配置 GitHub Pages

1. 进入仓库 Settings → Pages
2. Source 选择 "Deploy from a branch"
3. Branch 选择 "main"，文件夹选择 "/docs"
4. 点击 Save

### 3. 项目结构调整

```
taixiaohu/
├── docs/                    # GitHub Pages 根目录
│   ├── index.html          # 主页面
│   ├── static/             # 静态资源
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   └── api/                # API文档
│
├── src/                    # 源代码
│   ├── agent.py
│   ├── web_interface.py
│   └── adapters/
│
├── tests/                  # 测试
├── config/                 # 配置文件
├── requirements.txt
├── README.md
└── .github/
    └── workflows/          # CI/CD
        └── deploy.yml
```

### 4. 创建 GitHub Actions 工作流

`.github/workflows/deploy.yml`:

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout
      uses: actions/checkout@v3
      
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
        
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        
    - name: Run tests
      run: |
        python -m pytest tests/ -v
        
    - name: Build documentation
      run: |
        python scripts/build_docs.py
        
    - name: Deploy to GitHub Pages
      uses: peaceiris/actions-gh-pages@v3
      if: github.ref == 'refs/heads/main'
      with:
        github_token: ${{ secrets.GITHUB_TOKEN }}
        publish_dir: ./docs
```

### 5. 创建构建脚本

`scripts/build_docs.py`:

```python
#!/usr/bin/env python3
"""
构建文档站点
将模板和静态资源复制到 docs 目录
"""

import shutil
import os
from pathlib import Path

def build_docs():
    """构建文档"""
    # 清理旧文件
    docs_dir = Path("docs")
    if docs_dir.exists():
        shutil.rmtree(docs_dir)
    docs_dir.mkdir()
    
    # 复制静态资源
    static_dir = docs_dir / "static"
    static_dir.mkdir()
    
    # 复制 CSS
    css_dir = static_dir / "css"
    css_dir.mkdir()
    shutil.copy("templates/index.html", docs_dir / "index.html")
    
    # 创建 API 文档
    api_dir = docs_dir / "api"
    api_dir.mkdir()
    
    # 生成 API 文档
    with open(api_dir / "index.html", "w", encoding="utf-8") as f:
        f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>泰小虎 API 文档</title>
    <meta charset="utf-8">
</head>
<body>
    <h1>泰小虎智能健康导购助手 API</h1>
    <p>API 文档正在建设中...</p>
</body>
</html>
""")
    
    print("✅ 文档构建完成")

if __name__ == "__main__":
    build_docs()
```

### 6. 配置后端服务

由于 GitHub Pages 只支持静态页面，需要：

**方案A：使用 Vercel/Render 部署后端**

`vercel.json`:
```json
{
  "version": 2,
  "builds": [
    {
      "src": "web_interface.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "web_interface.py"
    }
  ]
}
```

**方案B：使用 GitHub Pages + 第三方 API**

修改前端直接调用部署好的 API：

```javascript
// 配置 API 地址
const API_BASE = "https://your-backend.vercel.app";

async function sendMessage() {
    const response = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userInput })
    });
    // ...
}
```

## 完整部署流程

### 第一步：准备代码

```bash
# 1. 克隆仓库
git clone https://github.com/yourusername/taixiaohu.git
cd taixiaohu

# 2. 创建项目结构
mkdir -p src adapters templates static/css static/js tests docs

# 3. 移动文件
mv agent.py src/
mv web_interface.py src/
mv adapters/* src/adapters/
mv templates/* templates/
mv test_agent.py tests/

# 4. 创建 requirements.txt
cat > requirements.txt << EOF
flask>=2.0.0
pytest>=7.0.0
EOF

# 5. 更新导入路径
# 修改 src/agent.py 中的导入
# 修改 src/web_interface.py 中的导入
```

### 第二步：配置前端

创建 `templates/index.html`（GitHub Pages 版本）：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>泰小虎 - 智能健康导购助手</title>
    <link rel="stylesheet" href="static/css/style.css">
</head>
<body>
    <div id="app">
        <!-- 应用内容 -->
    </div>
    <script src="static/js/app.js"></script>
</body>
</html>
```

### 第三步：提交代码

```bash
git add .
git commit -m "Prepare for GitHub Pages deployment"
git push origin main
```

### 第四步：验证部署

1. 访问 `https://yourusername.github.io/taixiaohu`
2. 检查页面是否正常加载
3. 测试 API 调用

## 自动化部署

### 配置自动发布

`.github/workflows/release.yml`:

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Create Release
      uses: actions/create-release@v1
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      with:
        tag_name: ${{ github.ref }}
        release_name: Release ${{ github.ref }}
        draft: false
        prerelease: false
```

## 文档同步

将文档推送到 `https://ddyuan-spec.github.io/taixiaohu/docs/`：

```bash
# 1. 在 docs 目录下创建 CNAME 文件（如果需要自定义域名）
echo "taixiaohu.example.com" > docs/CNAME

# 2. 提交
git add docs/
git commit -m "Update documentation"
git push origin main

# 3. 等待 GitHub Actions 部署完成
# 4. 访问 https://yourusername.github.io/taixiaohu
```

## 常见问题

### Q1: GitHub Pages 404 错误

**解决**：
- 检查仓库是否公开
- 确认 Pages 设置正确
- 等待几分钟让部署完成

### Q2: 静态资源加载失败

**解决**：
- 使用相对路径：`static/css/style.css`
- 确保文件在 docs 目录下

### Q3: API 跨域问题

**解决**：
- 后端添加 CORS 支持：

```python
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=["https://yourusername.github.io"])
```

### Q4: 如何更新已部署的内容

**解决**：
```bash
# 修改代码
git add .
git commit -m "Update features"
git push origin main

# GitHub Actions 会自动部署
```

## 相关链接

- [GitHub Pages 文档](https://docs.github.com/en/pages)
- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [Vercel 部署指南](https://vercel.com/docs)

## 联系方式

如有问题，请提交 Issue 或联系维护者。
