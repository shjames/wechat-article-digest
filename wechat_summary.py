import requests
import json
import time
import schedule
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
        url = "https://api.jizhile.com/v1/wechat/articles"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        params = {
            "account_name": account_name
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json().get("articles", [])
        except Exception as e:
            print(f"获取公众号 {account_name} 文章失败: {e}")
            return []

    def summarize_article(self, article_content):
        url = "https://api.jizhile.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "gpt-4",
            "messages": [
                {
                    "role": "system",
                    "content": "请用中文总结以下文章的重点内容，要求简洁明了，突出核心观点。"
                },
                {
                    "role": "user",
                    "content": article_content
                }
            ],
            "max_tokens": 500
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"文章总结失败: {e}")
            return "总结失败"

    def process_account(self, account_name):
        print(f"正在处理公众号: {account_name}")
        articles = self.fetch_articles(account_name)
        
        if not articles:
            print(f"公众号 {account_name} 未获取到文章")
            return
        
        self.article_summaries[account_name] = []
        
        for article in articles:
            print(f"  正在总结文章: {article.get('title', '无标题')}")
            article_content = article.get("content", "")
            summary = self.summarize_article(article_content)
            
            self.article_summaries[account_name].append({
                "title": article.get("title", "无标题"),
                "url": article.get("url", ""),
                "publish_time": article.get("publish_time", ""),
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
