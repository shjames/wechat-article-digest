import json
import time
import http.client
from datetime import datetime
from typing import Any, Dict, List, Optional
import hashlib
import os

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
        self.cache_dir = "./cache"
        os.makedirs(self.cache_dir, exist_ok=True)

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
        # 检查文章列表缓存
        account_hash = hashlib.md5(account_name.encode('utf-8')).hexdigest()
        articles_cache_file = os.path.join(self.cache_dir, f"articles_{account_hash}.json")

        # 先尝试使用任何缓存，包括过期缓存
        if os.path.exists(articles_cache_file):
            try:
                with open(articles_cache_file, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                    articles = cache_data.get("articles", [])
                    if articles:
                        timestamp = cache_data.get("timestamp", 0)
                        if time.time() - timestamp < 3600:  # 1小时有效期
                            print(f"  从缓存获取文章列表: {articles_cache_file}")
                        else:
                            print(f"  使用过期缓存: {articles_cache_file}")
                        return articles[:self.article_limit]
            except Exception as e:
                print(f"  读取文章列表缓存失败: {e}")

        # 缓存不存在或读取失败，调用API
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

            # 缓存文章列表
            if articles:
                with open(articles_cache_file, "w", encoding="utf-8") as f:
                    json.dump({"account": account_name, "articles": articles, "timestamp": time.time()}, f)
                print(f"  文章列表已缓存: {articles_cache_file}")

            return articles[:self.article_limit]
        except Exception as e:
            print(f"获取公众号 {account_name} 文章失败: {e}")
            return []

    def _get_cache_key(self, article_url: str) -> str:
        return hashlib.md5(article_url.encode('utf-8')).hexdigest()

    def fetch_article_detail(self, article_url: str) -> str:
        cache_key = self._get_cache_key(article_url)
        cache_file = os.path.join(self.cache_dir, f"article_{cache_key}.json")

        # 检查缓存
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                    if cache_data.get("content", ""):
                        print(f"  从缓存获取文章内容: {cache_file}")
                        return cache_data["content"]
            except Exception as e:
                print(f"  读取缓存失败: {e}")

        # 缓存不存在，调用API
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
            content = result.get("content", "")

            # 缓存结果
            if content:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump({"url": article_url, "content": content, "timestamp": time.time()}, f)
                print(f"  文章内容已缓存: {cache_file}")

            return content
        except Exception as e:
            print(f"获取文章详情失败: {e}")
            return ""

    def build_summary_prompt(self, article_content: str) -> str:
        return self.summary_prompt_template.replace("{article_content}", article_content)

    def _preprocess_article_content(self, article_content: str) -> str:
        # 去除HTML标签
        import re
        content = re.sub(r'<.*?>', '', article_content)
        # 去除多余空格和换行
        content = re.sub(r'\s+', ' ', content).strip()
        # 去除冗余信息
        redundant_patterns = [
            r'关注.*公众号',
            r'扫码.*关注',
            r'点击.*查看',
            r'分享.*好友',
            r'点赞.*收藏',
            r'广告.*推广',
            r'免责声明.*'
        ]
        for pattern in redundant_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        return content

    def fallback_summary(self, article_content: str) -> str:
        if not article_content:
            return "文章内容为空"

        article_content = article_content.strip()
        preview = article_content[:300] + "..." if len(article_content) > 300 else article_content
        return f"简单摘要：{preview}"

    def summarize_article(self, article_content: str) -> str:
        if not article_content:
            return "文章内容为空"

        # 缓存总结结果
        content_hash = hashlib.md5(article_content.encode('utf-8')).hexdigest()
        summary_cache_file = os.path.join(self.cache_dir, f"summary_{content_hash}.json")

        if os.path.exists(summary_cache_file):
            try:
                with open(summary_cache_file, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                    if cache_data.get("summary", ""):
                        print(f"  从缓存获取总结结果: {summary_cache_file}")
                        return cache_data["summary"]
            except Exception as e:
                print(f"  读取总结缓存失败: {e}")

        # 预处理文章内容，去除冗余信息
        processed_content = self._preprocess_article_content(article_content)

        # 优化prompt，减少token使用
        prompt = self.build_summary_prompt(processed_content)

        try:
            summary = self.llm_client.generate(prompt)
            # 缓存总结结果
            with open(summary_cache_file, "w", encoding="utf-8") as f:
                json.dump({"content_hash": content_hash, "summary": summary, "timestamp": time.time()}, f)
            print(f"  总结结果已缓存: {summary_cache_file}")
            return summary
        except Exception as e:
            print(f"文章总结失败，已使用兜底摘要: {e}")
            return self.fallback_summary(processed_content)

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

    # 默认执行单次运行模式
    wechat_summary.run_once()


if __name__ == "__main__":
    main()