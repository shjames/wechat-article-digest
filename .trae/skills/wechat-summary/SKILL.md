---
name: "wechat-summary"
description: "抓取指定微信公众号最新文章，使用AI总结内容，并按公众号分类输出Markdown格式报告。Invoke when user wants to collect and summarize WeChat official account articles."
---

# 微信公众号文章抓取与总结

## 功能说明

这个skill可以帮助你：
1. 配置微信公众号名称列表
2. 使用极致了API平台接口抓取公众号最新文章
3. 对每篇文章进行AI总结
4. 按公众号分类整理并输出Markdown格式报告

## 使用方法

### 1. 配置

首先编辑 `config.json` 文件，配置：
- API密钥
- 公众号列表
- 定时任务间隔（分钟）

### 2. 运行程序

```bash
python wechat_summary.py
```

### 3. 输出结果

程序会生成 `wechat_articles_summary.md` 文件，包含所有公众号文章的分类总结。

## 文件结构

- `config.json` - 配置文件
- `wechat_summary.py` - 主程序
- `requirements.txt` - 依赖包列表

## 依赖安装

```bash
pip install -r requirements.txt
```

## 注意事项

- 需要在极致了API平台获取API密钥
- 定时任务会持续运行，按指定间隔执行
