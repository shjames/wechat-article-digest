import requests
import json
import time
import schedule
import http.client
from datetime import datetime

class WeChatSummary:
    def __init__(self, config_file="config.json"):
        self.config = self.load_config(config_file)
        self.api_key = self.config.get("api_key", "")
        self.official_accounts = self.config.get("official_accounts", [])
        self.interval = self.config.get("interval", 60)
        self.article_summaries = {}

    def load_config(self, config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"配置文件 {config_file} 不存在，使用默认配置")
            return {
                "api_key": "",
                "official_accounts": [],
                "interval": 60
            }

    def fetch_articles(self, account_name):
        conn = http.client.HTTPSConnection("www.dajiala.com")
        payload = json.dumps({
           "biz": "",
           "url": "",
           "name": account_name,
           "key": self.api_key,
           "verifycode": ""
        })
        headers = {
           'Content-Type': 'application/json'
        }
        
        try:
            conn.request("POST", "/fbmain/monitor/v3/post_condition", payload, headers)
            res = conn.getresponse()
            data = res.read()
            result = json.loads(data.decode("utf-8"))
            return result.get("data", [])
        except Exception as e:
            print(f"获取公众号 {account_name} 文章失败: {e}")
            return []

    def fetch_article_detail(self, article_url):
        conn = http.client.HTTPSConnection("www.dajiala.com")
        encoded_url = article_url.replace("&", "%26").replace("?", "%3F").replace("=", "%3D")
        url = f"/fbmain/monitor/v3/article_detail?url={encoded_url}&key={self.api_key}&mode=2&verifycode="
        
        try:
            conn.request("GET", url)
            res = conn.getresponse()
            data = res.read()
            result = json.loads(data.decode("utf-8"))
            return result.get("content", "")
        except Exception as e:
            print(f"获取文章详情失败: {e}")
            return ""

    def summarize_article(self, article_content):
        # 调用Minimax大模型进行文章总结
        url = "https://api.minimax.chat/v1/text/chatcompletion"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "abab6-chat",
            "messages": [
                {
                    "role": "user",
                    "content": f"请用最简洁且准确的语言总结以下文章内容：\n\n{article_content}"
                }
            ],
            "max_tokens": 500
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            # 检查返回结果的结构
            if "reply" in result:
                return result["reply"]
            elif "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                # 尝试使用简单摘要作为备选方案
                if not article_content:
                    return "文章内容为空"
                if len(article_content) > 300:
                    summary = article_content[:300] + "..."
                else:
                    summary = article_content
                return f"简单摘要: {summary}"
        except Exception as e:
            print(f"文章总结失败: {e}")
            # 尝试使用简单摘要作为备选方案
            if not article_content:
                return "文章内容为空"
            if len(article_content) > 300:
                summary = article_content[:300] + "..."
            else:
                summary = article_content
            return f"简单摘要: {summary}"

    def process_account(self, account_name):
        print(f"正在处理公众号: {account_name}")
        articles = self.fetch_articles(account_name)
        
        if not articles:
            print(f"公众号 {account_name} 未获取到文章")
            return
        
        self.article_summaries[account_name] = []
        
        for article in articles:
            print(f"  正在总结文章: {article.get('title', '无标题')}")
            # 先尝试获取文章详情内容
            article_url = article.get("url", "")
            article_content = self.fetch_article_detail(article_url)
            
            # 如果没有获取到文章详情，则使用标题和链接
            if not article_content:
                article_content = f"标题: {article.get('title', '无标题')}\n链接: {article.get('url', '')}"
            
            summary = self.summarize_article(article_content)
            
            self.article_summaries[account_name].append({
                "title": article.get("title", "无标题"),
                "url": article.get("url", ""),
                "publish_time": article.get("post_time_str", article.get("publish_time", "")),
                "summary": summary
            })

    def generate_markdown(self):
        md_content = f"# 微信公众号文章总结\n\n"
        md_content += f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        md_content += "---\n\n"
        
        for account_name, articles in self.article_summaries.items():
            md_content += f"## {account_name}\n\n"
            
            for idx, article in enumerate(articles, 1):
                md_content += f"### {idx}. {article['title']}\n\n"
                md_content += f"- 发布时间: {article['publish_time']}\n"
                md_content += f"- 原文链接: {article['url']}\n\n"
                md_content += f"**文章总结:**\n\n"
                md_content += f"{article['summary']}\n\n"
                md_content += "---\n\n"
        
        output_file = "wechat_articles_summary.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(md_content)
        
        print(f"总结报告已生成: {output_file}")

    def run_once(self):
        print("=" * 50)
        print(f"开始执行任务 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
        self.article_summaries = {}
        
        for account in self.official_accounts:
            self.process_account(account)
        
        if self.article_summaries:
            self.generate_markdown()
        else:
            print("未获取到任何文章")
        
        print("=" * 50)
        print(f"任务完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)

    def run_scheduled(self):
        print(f"启动定时任务，每 {self.interval} 分钟执行一次")
        schedule.every(self.interval).minutes.do(self.run_once)
        
        self.run_once()
        
        while True:
            schedule.run_pending()
            time.sleep(60)

def main():
    wechat_summary = WeChatSummary()
    
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
