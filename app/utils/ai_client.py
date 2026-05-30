"""
LLM 客户端封装
"""

from typing import Optional, Dict, Any
import json
import re
from app.utils.logger import logger

class LLMClient:
    """统一的 LLM 客户端接口"""
    
    def __init__(
        self,
        provider: str = "deepseek",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "deepseek-chat"
    ):
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self._client = None
        
        if provider == "deepseek":
            self._init_deepseek()
        elif provider == "openai":
            self._init_openai()
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def _init_deepseek(self):
        """初始化 DeepSeek 客户端"""
        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url or "https://api.deepseek.com/v1"
            )
        except ImportError:
            raise ImportError("Please install openai: pip install openai")
    
    def _init_openai(self):
        """初始化 OpenAI 客户端"""
        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        except ImportError:
            raise ImportError("Please install openai: pip install openai")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        生成文本
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词（可选）
            temperature: 温度参数
            max_tokens: 最大 token 数
            
        Returns:
            str: 生成的文本
        """
        if not self._client:
            raise RuntimeError("LLM client not initialized")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"LLM generation failed: {str(e)}")
    
    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        生成 JSON 格式的响应
        
        Returns:
            Dict: 解析后的 JSON 对象
        """
        # 在 prompt 中强调需要 JSON 格式
        json_prompt = prompt + "\n\n重要：只返回标准 JSON，不要有其他说明文字。"
        
        response = self.generate(
            prompt=json_prompt,
            system_prompt=system_prompt,
            temperature=temperature
        )
        
        # 尝试提取 JSON
        return self._extract_json(response)
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """从文本中提取 JSON"""
        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取 ```json ... ``` 块
        json_pattern = r'```json\s*([\s\S]*?)\s*```'
        match = re.search(json_pattern, text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 尝试提取 { ... } 块
        json_pattern = r'\{[\s\S]*\}'
        match = re.search(json_pattern, text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        
        raise ValueError(f"Failed to extract JSON from response: {text[:200]}")
