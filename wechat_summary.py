import json
import time
import http.client
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
import schedule


class LLMClient:
    """
    基于 sdk_type 的统一模型调用器

    支持：
    - openai      -> OpenAI SDK 兼容体系
    - anthropic  -> Anthropic SDK 兼容体系
    - gemini     -> Google Gemini SDK

    配置建议：
    {
      "llm": {
        "sdk_type": "anthropic",
        "model": "MiniMax-M2.7",
        "api_key": "xxx",
        "base_url": "https://api.minimax.io/anthropic"
      }
    }

    或：
    {
      "llm": {
        "sdk_type": "openai",
        "model": "deepseek-chat",
        "api_key": "xxx",
        "base_url": "https://api.deepseek.com"
      }
    }
    """

    def __init__(self, llm_config: Dict[str, Any]):
        self.sdk_type = str(llm_config.get("sdk_type", "")).strip().lower()
        self.model = str(llm_config.get("model", "")).strip()
        self.api_key = str(llm_config.get("api_key", "")).strip()
        self.base_url = str(llm_config.get("base_url", "")).strip()
        self.timeout = int(llm_config.get("timeout", 60))
        self.max_tokens = int(llm_config.get("max_tokens", 1000))
        self.temperature = float(llm_config.get("temperature", 0.3))
        self.system_prompt = str(
            llm_config.get(
                "system_prompt",
                "你是一个擅长总结微信公众号文章的助手，请用简洁准确的中文总结重点。"
            )
        ).strip()

        if not self.sdk_type:
            raise ValueError("llm.sdk_type 未配置，可选值：openai / anthropic / gemini")
        if not self.model:
            raise ValueError("llm.model 未配置")
        if not self.api_key:
            raise ValueError("llm.api_key 未配置")

    def generate(self, user_prompt: str) -> str:
        if self.sdk_type == "openai":
            return self._generate_with_openai(user_prompt)

        if self.sdk_type == "anthropic":
            return self._generate_with_anthropic(user_prompt)

        if self.sdk_type == "gemini":
            return self._generate_with_gemini(user_prompt)

        raise ValueError(f"不支持的 llm.sdk_type: {self.sdk_type}")

    def _generate_with_openai(self, user_prompt: str) -> str:
        """
        使用 OpenAI SDK 调用兼容 OpenAI Chat Completions 的模型服务

        适用示例：
        - OpenAI
        - DeepSeek
        - Moonshot
        - 通义千问兼容接口
        - 智谱兼容接口
        - 各类 OpenAI 兼容网关
        """
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError("未安装 openai 依赖，请先执行: pip install openai") from e

        client_kwargs: Dict[str, Any] = {
            "api_key": self.api_key
        }
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        client = OpenAI(**client_kwargs)

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout=self.timeout
        )

        if response.choices and response.choices[0].message and response.choices[0].message.content:
            return response.choices[0].message.content.strip()

        raise ValueError("OpenAI SDK 返回内容为空")

    def _generate_with_anthropic(self, user_prompt: str) -> str:
        """
        使用 Anthropic SDK 调用 Anthropic 官方或 Anthropic-compatible 服务

        适用示例：
        - Anthropic Claude
        - MiniMax 官方提供的 anthropic-compatible 接口
        - 其他兼容 Anthropic Messages API 的平台
        """
        try:
            from anthropic import Anthropic
        except ImportError as e:
            raise ImportError("未安装 anthropic 依赖，请先执行: pip install anthropic") from e

        client_kwargs: Dict[str, Any] = {
            "api_key": self.api_key
        }
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        client = Anthropic(**client_kwargs)

        response = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=self.system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            timeout=self.timeout
        )

        text_parts: List[str] = []
        for item in getattr(response, "content", []) or []:
            item_type = getattr(item, "type", None)
            if item_type == "text":
                text_value = getattr(item, "text", "")
                if text_value:
                    text_parts.append(text_value)

        final_text = "".join(text_parts).strip()
        if final_text:
            return final_text

        raise ValueError("Anthropic SDK 返回内容为空")

    def _generate_with_gemini(self, user_prompt: str) -> str:
        """
        使用 Google Gemini SDK
        """
        try:
            import google.generativeai as genai
        except ImportError as e:
            raise ImportError(
                "未安装 google-generativeai 依赖，请先执行: pip install google-generativeai"
            ) from e

        genai.configure(api_key=self.api_key)

        generation_config = {
            "temperature": self.temperature,
            "max_output_tokens": self.max_tokens,
        }

        model = genai.GenerativeModel(
            model_name=self.model,
            system_instruction=self.system_prompt,
            generation_config=generation_config
        )

        response = model.generate_content(user_prompt)

        text = getattr(response, "text", "")
        if text:
            return text.strip()

        candidates = getattr(response, "candidates", None)
        if candidates:
            try:
                parts = candidates[0].content.parts
                merged = "".join([getattr(p, "text", "") for p in parts]).strip()
                if merged:
                    return merged
            except Exception:
                pass

        raise ValueError("Gemini SDK 返回内容为空")


class WeChatSummary:
    def __init__(self, config_file: str = "config.json"):
        self.config = self.load_config(config_file)

        wechat_api_config = self.config.get("wechat_api", {})
        self.wechat_api_provider = str(
            wechat_api_config.get("provider", "dajiala")
        ).strip().lower()
        self.wechat_api_key = str(wechat_api_config.get("api_key", "")).strip()

        self.llm_config = self.config.get("llm", {})
        self.official_accounts = self.config.get("official_accounts", [])
        self.interval = int(self.config.get("interval", 60))
        self.article_limit = int(self.config.get("article_limit", 5))
        self.summary_prompt_template = str(
            self.config.get(
                "summary_prompt_template",
                "请用最简洁且准确的语言总结以下文章内容：\n\n{article_content}"
            )
        )

        self.article_summaries: Dict[str, List[Dict[str, Any]]] = {}

        self._validate_basic_config()
        self.llm_client = LLMClient(self.llm_config)

    def _validate_basic_config(self):
        if not self.wechat_api_key:
            raise ValueError("wechat_api.api_key 未配置，请在 config.json 中填写")
        if not self.official_accounts:
            raise ValueError("official_accounts 未配置，请至少填写一个公众号名称")
        if self.wechat_api_provider != "dajiala":
            raise ValueError(
                f"当前仅支持 wechat_api.provider=dajiala，收到: {self.wechat_api_provider}"
            )

    def load_config(self, config_file: str) -> Dict[str, Any]:
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件 {config_file} 不存在，请先创建配置文件")
        except json.JSONDecodeError as e:
            raise ValueError(f"配置文件 {config_file} JSON 格式错误: {e}")

    def fetch_articles(self, account_name: str) -> List[Dict[str, Any]]:
        """
        当前实现使用 dajiala 抓取公众号文章
        """
        conn = http.client.HTTPSConnection("www.dajiala.com")
        payload = json.dumps({
            "biz": "",
            "url": "",
            "name": account_name,
            "key": self.wechat_api_key,
            "verifycode": ""
        })
        headers = {
            "Content-Type": "application/json"
        }

        try:
            conn.request("POST", "/fbmain/monitor/v3/post_condition", payload, headers)
            res = conn.getresponse()
            data = res.read()
            result = json.loads(data.decode("utf-8"))
            articles = result.get("data", [])
            return articles[:self.article_limit]
        except Exception as e:
            print(f"获取公众号 {account_name} 文章失败: {e}")
            return []

    def fetch_article_detail(self, article_url: str) -> str:
        conn = http.client.HTTPSConnection("www.dajiala.com")
        encoded_url = (
            article_url
            .replace("&", "%26")
            .replace("?", "%3F")
            .replace("=", "%3D")
        )
        url = (
            f"/fbmain/monitor/v3/article_detail"
            f"?url={encoded_url}&key={self.wechat_api_key}&mode=2&verifycode="
        )

        try:
            conn.request("GET", url)
            res = conn.getresponse()
            data = res.read()
            result = json.loads(data.decode("utf-8"))
            return result.get("content", "")
        except Exception as e:
            print(f"获取文章详情失败: {e}")
            return ""

    def build_summary_prompt(self, article_content: str) -> str:
        return self.summary_prompt_template.replace("{article_content}", article_content)

    def fallback_summary(self, article_content: str) -> str:
        if not article_content:
            return "文章内容为空"

        article_content = article_content.strip()
        preview = article_content[:300] + "..." if len(article_content) > 300 else article_content
        return f"简单摘要：{preview}"

    def summarize_article(self, article_content: str) -> str:
        if not article_content:
            return "文章内容为空"

        prompt = self.build_summary_prompt(article_content)

        try:
            return self.llm_client.generate(prompt)
        except Exception as e:
            print(f"文章总结失败，已使用兜底摘要: {e}")
            return self.fallback_summary(article_content)

    def process_account(self, account_name: str):
        print(f"正在处理公众号: {account_name}")
        articles = self.fetch_articles(account_name)

        if not articles:
            print(f"公众号 {account_name} 未获取到文章")
            return

        self.article_summaries[account_name] = []

        for article in articles:
            title = article.get("title", "无标题")
            article_url = article.get("url", "")
            publish_time = article.get("post_time_str", article.get("publish_time", ""))

            print(f"  正在总结文章: {title}")
            article_content = self.fetch_article_detail(article_url)

            if not article_content:
                article_content = f"标题: {title}\n链接: {article_url}"

            summary = self.summarize_article(article_content)

            self.article_summaries[account_name].append({
                "title": title,
                "url": article_url,
                "publish_time": publish_time,
                "summary": summary
            })

    def generate_markdown(self, output_file: str = "wechat_articles_summary.md"):
        md_content = "# 微信公众号文章总结\n\n"
        md_content += f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        md_content += "---\n\n"

        for account_name, articles in self.article_summaries.items():
            md_content += f"## {account_name}\n\n"

            for idx, article in enumerate(articles, 1):
                md_content += f"### {idx}. {article['title']}\n\n"
                md_content += f"- 发布时间: {article['publish_time']}\n"
                md_content += f"- 原文链接: {article['url']}\n\n"
                md_content += "**文章总结：**\n\n"
                md_content += f"{article['summary']}\n\n"
                md_content += "---\n\n"

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(md_content)

        print(f"总结报告已生成: {output_file}")

    def run_once(self):
        print("=" * 60)
        print(f"开始执行任务 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        self.article_summaries = {}

        for account in self.official_accounts:
            self.process_account(account)

        if self.article_summaries:
            self.generate_markdown()
        else:
            print("未获取到任何文章")

        print("=" * 60)
        print(f"任务完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

    def run_scheduled(self):
        print(f"启动定时任务，每 {self.interval} 分钟执行一次")
        schedule.every(self.interval).minutes.do(self.run_once)

        self.run_once()

        while True:
            schedule.run_pending()
            time.sleep(60)


def main():
    try:
        wechat_summary = WeChatSummary()
    except Exception as e:
        print(f"初始化失败: {e}")
        return

    print("请选择运行模式:")
    print("1. 单次执行")
    print("2. 定时执行")

    choice = input("请输入选项 (1/2): ").strip()

    if choice == "1":
        wechat_summary.run_once()
    elif choice == "2":
        wechat_summary.run_scheduled()
    else:
        print("无效选项，默认单次执行")
        wechat_summary.run_once()


if __name__ == "__main__":
    main()