"""
LLM 客户端模块 - 支持多提供商切换
支持：DeepSeek / OpenAI / Claude / SiliconFlow / 自定义 OpenAI-compatible API
"""

import os
import re
from typing import Dict, Any, Optional

import yaml


class LLMClient:
    """统一的 LLM 客户端，支持多提供商"""

    def __init__(self, config_path: str = "config/llm_config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.provider = self.config['active_provider']
        self.provider_cfg = self.config['providers'][self.provider]
        self.gen_cfg = self.config['generation']

        # 获取 API key
        self.api_key = self._get_api_key()
        self.base_url = self._resolve_env_vars(self.provider_cfg['base_url'])
        self.model = self.provider_cfg['default_model']

        # 初始化客户端
        self.client = self._init_client()

    def _get_api_key(self) -> str:
        """从环境变量获取 API key"""
        env_var = self.provider_cfg['api_key_env']
        api_key = os.environ.get(env_var)
        if not api_key:
            raise ValueError(
                f"未找到 {self.provider} 的 API key。"
                f"请在环境变量中设置 {env_var}"
            )
        return api_key

    @staticmethod
    def _resolve_env_vars(value: str) -> str:
        """解析字符串中的环境变量引用"""
        pattern = re.compile(r'\$\{(\w+)\}')
        def replacer(match):
            env_var = match.group(1)
            env_value = os.environ.get(env_var)
            if env_value is None:
                raise ValueError(f"环境变量 {env_var} 未设置")
            return env_value
        return pattern.sub(replacer, value)

    def _init_client(self):
        """初始化 OpenAI-compatible 客户端"""
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "请先安装 openai 包: pip install openai"
            )

        return OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def chat(self, prompt: str, task_type: str = "summary", model: Optional[str] = None) -> str:
        """
        发送聊天请求

        Args:
            prompt: 提示词
            task_type: 任务类型 (relevance/summary/deep_research)
            model: 可选，覆盖默认模型

        Returns:
            LLM 生成的文本
        """
        use_model = model or self.model
        gen_params = self.gen_cfg.get(task_type, self.gen_cfg['summary'])

        # 构建请求参数
        kwargs = {
            "model": use_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": gen_params.get("temperature", 0.3),
            "max_tokens": gen_params.get("max_tokens", 2048),
        }

        # 添加 response_format（仅支持 json_object 的提供商）
        if gen_params.get("response_format") == "json_object":
            if self.provider not in ["claude"]:
                kwargs["response_format"] = {"type": "json_object"}

        resp = self.client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content

    def switch_provider(self, provider: str) -> None:
        """切换到其他 LLM 提供商"""
        if provider not in self.config['providers']:
            available = list(self.config['providers'].keys())
            raise ValueError(f"未知提供商 '{provider}'。可用: {available}")

        self.provider = provider
        self.provider_cfg = self.config['providers'][provider]
        self.api_key = self._get_api_key()
        self.base_url = self._resolve_env_vars(self.provider_cfg['base_url'])
        self.model = self.provider_cfg['default_model']
        self.client = self._init_client()
        print(f"已切换到: {self.provider_cfg['name']} (模型: {self.model})")

    def list_providers(self) -> Dict[str, str]:
        """列出所有可用的提供商"""
        return {
            k: v['name']
            for k, v in self.config['providers'].items()
        }

    def get_info(self) -> Dict[str, str]:
        """获取当前配置信息"""
        return {
            "provider": self.provider,
            "name": self.provider_cfg['name'],
            "model": self.model,
            "base_url": self.base_url,
        }


def format_prompt(template: str, **kwargs) -> str:
    """
    使用 Jinja2 风格格式化 prompt 模板
    支持 {{ variable }} 语法
    """
    from string import Formatter

    class CustomFormatter(Formatter):
        def format_field(self, value, format_spec):
            return str(value)

    formatter = CustomFormatter()
    try:
        return formatter.format(template, **kwargs)
    except KeyError as e:
        missing_key = str(e).strip("'")
        # 如果变量缺失，保留原样
        return template.replace(f"{{{{{missing_key}}}}}", f"{{{missing_key}}}")
