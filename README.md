# OpenAlex MCP Server

使用 FastMCP 构建的学术论文搜索 MCP 服务器，为 AI Agent（如 Cursor、Claude Desktop）提供 OpenAlex 论文搜索和查询功能。

## 设计理念 (2025.12 最佳实践)

遵循 ChatGPT Deep Research 模式，将工具精简为 **2 个核心工具**：

| 工具 | 功能 |
|------|------|
| `search_openalex` | 统一搜索入口 - 搜索论文、作者或期刊 |
| `fetch_openalex` | 统一详情获取 - 通过 ID 或 DOI 获取完整信息 |

## 快速开始

### 方式一：uvx 免安装运行（推荐）

无需安装，直接从 GitHub 运行：

```bash
uvx --from git+https://github.com/h-lu/openalex openalex-mcp
```

### 方式二：本地安装

```bash
cd /Users/wangxq/Documents/openalex
uv sync
uv run python openalex_mcp_server.py
```

### 方式三：pip 安装

```bash
pip install git+https://github.com/h-lu/openalex
openalex-mcp
```

## 配置 Cursor

编辑 `~/.cursor/mcp.json`:

### 使用 uvx（推荐，免安装）

```json
{
  "mcpServers": {
    "openalex": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/h-lu/openalex", "openalex-mcp"],
      "env": {
        "OPENALEX_EMAIL": "your-email@example.com"
      }
    }
  }
}
```

### 使用本地安装

```json
{
  "mcpServers": {
    "openalex": {
      "command": "uv",
      "args": ["run", "--directory", "/Users/wangxq/Documents/openalex", "python", "openalex_mcp_server.py"],
      "env": {
        "OPENALEX_EMAIL": "your-email@example.com"
      }
    }
  }
}
```

### 使用 Python 直接运行

```json
{
  "mcpServers": {
    "openalex": {
      "command": "/Users/wangxq/Documents/openalex/.venv/bin/python",
      "args": ["/Users/wangxq/Documents/openalex/openalex_mcp_server.py"],
      "env": {
        "OPENALEX_EMAIL": "your-email@example.com"
      }
    }
  }
}
```

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `OPENALEX_EMAIL` | 用于 OpenAlex API 的邮箱（提高速率限制从 1次/秒 到 10次/秒） | `openalex-mcp@example.com` |

## 工具详解

### 1. `search_openalex`

统一搜索入口，支持搜索论文、作者和期刊。

**参数:**
- `query` (必需): 搜索关键词
- `entity_type`: 搜索类型 - `"works"` | `"authors"` | `"sources"`，默认 `"works"`
- `year_from`: 起始年份（仅对论文有效）
- `year_to`: 结束年份（仅对论文有效）
- `sort_by`: 排序方式 - `"cited_by_count"` | `"publication_date"` | `"relevance"`
- `limit`: 返回数量，默认 10

**示例:**
```
搜索 2024 年的 LLM 经济学论文:
search_openalex("large language model economics", year_from=2024, sort_by="cited_by_count")

搜索作者:
search_openalex("Daron Acemoglu", entity_type="authors")

搜索期刊:
search_openalex("American Economic Review", entity_type="sources")
```

### 2. `fetch_openalex`

获取实体的详细信息，支持 OpenAlex ID 和 DOI。

**参数:**
- `identifier` (必需): 实体标识符（ID 或 DOI）
- `entity_type`: 实体类型 - `"work"` | `"author"` | `"source"`，默认 `"work"`
- `include_works`: 是否包含代表作品列表（对作者/期刊有效）

**示例:**
```
通过 DOI 获取论文:
fetch_openalex("10.1080/00207543.2024.2309309")

通过 ID 获取作者详情（含代表作）:
fetch_openalex("A5012301204", entity_type="author", include_works=True)

获取期刊信息:
fetch_openalex("S23254222", entity_type="source")
```

## 典型工作流

```
用户: 帮我找 2024 年关于 LLM 在经济学应用的论文

AI: 我来搜索一下...
    → search_openalex("LLM economics", year_from=2024, limit=5)
    
    找到 5 篇相关论文:
    1. W4391403992 - Generative AI in supply chain... (203 引用)
    2. ...
    
用户: 第一篇看起来不错，给我详细信息

AI: 获取详情...
    → fetch_openalex("W4391403992")
    
    标题: Generative AI in supply chain and operations management
    作者: Ilya Jackson (MIT), Dmitry Ivanov (Berlin)...
    引用数: 203, FWCI: 202.18
    ...
```

## 返回字段说明

### 论文 (work) 详情

| 字段 | 说明 |
|------|------|
| `id` | OpenAlex ID (如 W4391403992) |
| `doi` | DOI 链接 |
| `title` | 论文标题 |
| `publication_date` | 发表日期 |
| `cited_by_count` | 被引次数 |
| `fwci` | 字段加权引用影响 (Field-Weighted Citation Impact) |
| `is_top_1_percent` | 是否位于前 1% 高引论文 |
| `authors` | 作者列表（含机构信息） |
| `journal` | 期刊名称 |
| `is_oa` | 是否开放获取 |
| `pdf_url` | PDF 链接（如果开放获取） |
| `abstract` | 摘要文本 |
| `keywords` | 关键词列表 |

### 作者 (author) 详情

| 字段 | 说明 |
|------|------|
| `id` | OpenAlex ID (如 A5012301204) |
| `name` | 作者姓名 |
| `orcid` | ORCID |
| `works_count` | 论文总数 |
| `cited_by_count` | 被引总数 |
| `h_index` | H 指数 |
| `affiliations` | 所属机构 |
| `top_works` | 代表作列表（需设置 include_works=True） |

## 开发

### 运行测试

```bash
uv run python test_server.py
```

### HTTP 模式调试

```bash
uv run python openalex_mcp_server.py --http
# 服务器将在 http://localhost:8000 运行
```

## 数据来源

所有数据来自 [OpenAlex](https://openalex.org)，一个免费开放的学术文献数据库，包含超过 2.5 亿篇学术论文的元数据。

## License

MIT
