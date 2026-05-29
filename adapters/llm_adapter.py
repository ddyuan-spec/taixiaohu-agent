"""
LLM 调用适配器 V2
支持阿里云百炼（DashScope）、OpenAI 兼容接口
新增：环境变量支持 + GitHub配置恢复
"""
import json
import os
import requests as http_requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

# ============================================================
# 配置管理
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(BASE_DIR) == 'adapters':
    BASE_DIR = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(BASE_DIR, "data")
LLM_CONFIG_FILE = os.path.join(DATA_DIR, "llm_config.json")

# GitHub 预置配置URL
GITHUB_LLM_CONFIG_URL = "https://raw.githubusercontent.com/ddyuan-spec/taixiaohu-agent/main/data/llm_config.json"

# 默认 LLM 配置
DEFAULT_LLM_CONFIG = {
    "provider": "aliyun",
    "model": "qwen-plus",
    "api_key": "",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "temperature": 0.7,
    "max_tokens": 2000,
    "enabled": False,
    "fallback_to_mock": True
}

# 预设模型列表
PRESET_MODELS = {
    "aliyun": {
        "name": "阿里云百炼（通义千问）",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": [
            {"id": "qwen-turbo", "name": "Qwen Turbo（快速）", "desc": "速度快、成本低"},
            {"id": "qwen-plus", "name": "Qwen Plus（推荐）", "desc": "均衡性能与成本"},
            {"id": "qwen-max", "name": "Qwen Max（最强）", "desc": "能力最强、成本较高"},
            {"id": "qwen-long", "name": "Qwen Long（长文本）", "desc": "支持超长上下文"},
        ]
    },
    "openai_compatible": {
        "name": "OpenAI 兼容接口",
        "base_url": "",
        "models": [
            {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "desc": "OpenAI 快速模型"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "desc": "OpenAI 轻量模型"},
            {"id": "deepseek-chat", "name": "DeepSeek Chat", "desc": "DeepSeek 对话模型"},
        ]
    }
}

def _ensure_data_dir():
    """确保数据目录存在"""
    os.makedirs(DATA_DIR, exist_ok=True)

def _try_load_from_env(config: Dict) -> Dict:
    """
    从环境变量加载API Key（优先级最高）
    支持的环境变量：
      - DASHSCOPE_API_KEY（阿里云百炼）
      - OPENAI_API_KEY（OpenAI）
      - LLM_API_KEY（通用）
      - LLM_BASE_URL（自定义API地址）
      - LLM_MODEL（自定义模型名）
    """
    # API Key：环境变量优先
    env_key = (
        os.environ.get("DASHSCOPE_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("LLM_API_KEY")
    )
    if env_key and not config.get("api_key"):
        config["api_key"] = env_key
        print(f"[LLM] 从环境变量加载API Key: {env_key[:8]}****")

    # Base URL
    env_url = os.environ.get("LLM_BASE_URL")
    if env_url:
        config["base_url"] = env_url

    # Model
    env_model = os.environ.get("LLM_MODEL")
    if env_model:
        config["model"] = env_model

    return config

def _try_load_from_github(config: Dict) -> Dict:
    """
    从GitHub加载预置配置（如果本地配置为空）
    只恢复除api_key以外的配置，api_key需要用户手动填写
    """
    if config.get("api_key"):
        return config  # 已有API Key，不需要恢复

    try:
        print("[LLM] 本地配置为空，尝试从GitHub加载预置配置...")
        resp = http_requests.get(GITHUB_LLM_CONFIG_URL, timeout=10)
        if resp.status_code == 200:
            github_config = resp.json()
            if isinstance(github_config, dict):
                # 恢复除api_key以外的配置
                for key, val in github_config.items():
                    if key != "api_key" and key in DEFAULT_LLM_CONFIG:
                        config[key] = val
                print(f"[LLM] ✅ 从GitHub加载配置成功 (provider={config.get('provider')}, model={config.get('model')})")
    except Exception as e:
        print(f"[LLM] 从GitHub加载配置失败: {e}")

    return config

def load_llm_config() -> Dict:
    """加载 LLM 配置（优先级：环境变量 > 本地文件 > GitHub预置 > 默认值）"""
    _ensure_data_dir()
    config = DEFAULT_LLM_CONFIG.copy()

    # 1. 从本地文件加载
    if os.path.exists(LLM_CONFIG_FILE):
        try:
            with open(LLM_CONFIG_FILE, "r", encoding="utf-8") as f:
                file_config = json.load(f)
                for key, val in DEFAULT_LLM_CONFIG.items():
                    if key in file_config:
                        config[key] = file_config[key]
        except (json.JSONDecodeError, IOError):
            pass

    # 2. 从GitHub加载预置配置（如果本地为空）
    config = _try_load_from_github(config)

    # 3. 从环境变量加载（最高优先级）
    config = _try_load_from_env(config)

    return config

def save_llm_config(config: Dict):
    """保存 LLM 配置"""
    _ensure_data_dir()
    with open(LLM_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def pull_llm_config_from_github() -> Dict:
    """
    手动从GitHub拉取LLM配置
    返回: {"success": bool, "message": str, "config": dict}
    """
    try:
        resp = http_requests.get(GITHUB_LLM_CONFIG_URL, timeout=15)
        if resp.status_code == 200:
            github_config = resp.json()
            if isinstance(github_config, dict):
                # 保留当前的api_key（如果有的话）
                current_config = load_llm_config()
                current_key = current_config.get("api_key", "")

                for key, val in github_config.items():
                    if key in DEFAULT_LLM_CONFIG:
                        github_config[key] = val

                # 如果GitHub上有api_key且当前没有，使用GitHub的
                if not current_key and github_config.get("api_key"):
                    github_config["api_key"] = github_config["api_key"]
                elif current_key:
                    github_config["api_key"] = current_key

                save_llm_config(github_config)
                return {
                    "success": True,
                    "message": f"配置恢复成功 (provider={github_config.get('provider')}, model={github_config.get('model')})",
                    "config": github_config
                }
            else:
                return {"success": False, "message": "GitHub配置格式错误"}
        else:
            return {"success": False, "message": f"GitHub请求失败: HTTP {resp.status_code}"}
    except Exception as e:
        return {"success": False, "message": f"拉取失败: {str(e)}"}

# ============================================================
# LLM 适配器
# ============================================================
@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str
    success: bool = True
    error: str = ""
    usage: Dict = field(default_factory=dict)
    model: str = ""

class LLMAdapter:
    """LLM 调用适配器"""
    def __init__(self):
        self.config = load_llm_config()

    def reload_config(self):
        """重新加载配置"""
        self.config = load_llm_config()

    @property
    def is_enabled(self) -> bool:
        """是否启用真实 LLM"""
        return self.config.get("enabled", False) and bool(self.config.get("api_key", ""))

    def chat(self, messages: List[Dict], temperature: float = None,
             max_tokens: int = None) -> LLMResponse:
        """调用 LLM 进行对话"""
        if not self.is_enabled:
            return LLMResponse(
                content="",
                success=False,
                error="LLM 未启用或未配置 API Key"
            )

        config = self.config
        api_key = config.get("api_key", "")
        base_url = config.get("base_url", "").rstrip("/")
        model = config.get("model", "qwen-plus")
        temp = temperature if temperature is not None else config.get("temperature", 0.7)
        tokens = max_tokens if max_tokens is not None else config.get("max_tokens", 2000)

        if not api_key:
            return LLMResponse(content="", success=False, error="API Key 未配置")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temp,
            "max_tokens": tokens
        }

        try:
            response = http_requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                usage = result.get("usage", {})
                return LLMResponse(content=content, success=True, usage=usage, model=model)
            else:
                error_msg = f"API 错误 ({response.status_code})"
                try:
                    error_detail = response.json()
                    error_msg += f": {error_detail.get('error', {}).get('message', response.text[:200])}"
                except Exception:
                    error_msg += f": {response.text[:200]}"
                return LLMResponse(content="", success=False, error=error_msg)
        except http_requests.Timeout:
            return LLMResponse(content="", success=False, error="请求超时，请稍后重试")
        except http_requests.ConnectionError:
            return LLMResponse(content="", success=False, error="无法连接到 LLM 服务，请检查网络或 API 地址")
        except Exception as e:
            return LLMResponse(content="", success=False, error=f"LLM 调用异常: {str(e)}")

    def test_connection(self) -> Dict:
        """测试 LLM 连接"""
        if not self.config.get("api_key", ""):
            return {"success": False, "message": "请先配置 API Key"}
        messages = [{"role": "user", "content": "你好，请回复'连接成功'"}]
        result = self.chat(messages, max_tokens=20)
        if result.success:
            return {
                "success": True,
                "message": f"连接成功！模型: {result.model}",
                "response": result.content,
                "model": result.model,
                "usage": result.usage
            }
        else:
            return {"success": False, "message": result.error}

    def get_safe_config(self) -> Dict:
        """获取安全配置（隐藏 API Key）"""
        safe = self.config.copy()
        api_key = safe.get("api_key", "")
        if api_key:
            if len(api_key) > 12:
                safe["api_key"] = api_key[:8] + "****" + api_key[-4:]
            else:
                safe["api_key"] = "****"
        return safe

# 全局实例
llm_adapter = LLMAdapter()
