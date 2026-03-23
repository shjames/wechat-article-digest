# WeChat Article Summary Skill

一个用于抓取微信公众号最近文章并调用大模型自动生成摘要的 Skill。

这版采用 **sdk_type 统一模型调用架构**，不再在代码里维护不同模型厂商的默认 URL 映射，而是由用户通过配置文件显式指定：

- sdk_type
- model
- api_key
- base_url

这样更适合长期维护，也更适合放进 OpenClaw 或类似 Agent / Skill 平台中使用。

---

## 一、Skill 功能

本 Skill 可以完成以下工作：

1. 根据公众号名称抓取该公众号最近发布的文章
2. 获取文章详情正文
3. 调用用户自定义配置的大模型进行文章总结
4. 输出统一格式的 Markdown 总结文件
5. 支持单次执行
6. 支持定时执行

输出结果示例：

- `wechat_articles_summary.md`

---

## 二、项目文件结构

建议目录结构如下：

```bash
wechat-article-summary-skill/
├── config.json
├── requirements.txt
├── wechat_summary.py
├── wechat_articles_summary.md   # 运行后生成
└── SKILL.md
```
