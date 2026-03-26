# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python tool that fetches recent articles from WeChat official accounts and generates AI-powered summaries. Supports multiple LLM providers (OpenAI, Anthropic, Google Gemini) with intelligent caching to reduce API costs.

## Running the Application

**Single execution:**
```bash
python wechat_summary.py
```

**Output:** Generates `wechat_articles_summary.md` with article summaries.

## Configuration

All settings are in `config.json`:

- `wechat_api`: WeChat article fetching API credentials (currently only supports "dajiala" provider)
- `llm`: LLM configuration with `sdk_type` (openai/anthropic/gemini), `model`, `api_key`, `base_url`
- `official_accounts`: List of WeChat account names to monitor
- `article_limit`: Max articles per account (default: 5)
- `summary_prompt_template`: Template for article summarization

**Sensitive data:** API keys should be kept in `config.json` (gitignored). See `key.md` for key management notes.

## Architecture

**Core components:**

1. **LLMClient** (`wechat_summary.py:13-208`): Unified interface for multiple LLM SDKs
   - `_generate_with_openai()`: OpenAI-compatible APIs (OpenAI, DeepSeek, Moonshot, etc.)
   - `_generate_with_anthropic()`: Anthropic-compatible APIs (Claude, MiniMax, etc.)
   - `_generate_with_gemini()`: Google Gemini API

2. **WeChatSummary** (`wechat_summary.py:211-507`): Main orchestrator
   - `fetch_articles()`: Gets article list from WeChat API
   - `fetch_article_detail()`: Retrieves full article content
   - `summarize_article()`: Generates AI summary with caching
   - `process_account()`: Processes all articles for one account
   - `generate_markdown()`: Outputs final summary file

**Caching strategy:**
- Article lists: 1-hour validity (`./cache/articles_*.json`)
- Article content: Permanent (`./cache/article_*.json`)
- Summaries: Permanent (`./cache/summary_*.json`)
- Cache keys use MD5 hashes of URLs/content
- Falls back to expired cache on API failures

## Dependencies

Install with:
```bash
pip install -r requirements.txt
```

Required packages: `requests`, `schedule`, `openai`, `anthropic`, `google-generativeai`

## Adding New LLM Providers

To add a new LLM provider, extend `LLMClient`:

1. Add new `sdk_type` value in `generate()` method
2. Implement `_generate_with_<provider>()` method following existing patterns
3. Update `config.json` with new provider settings
4. Add SDK dependency to `requirements.txt`
