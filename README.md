# OpenAlex MCP Server

使用 FastMCP 构建的学术论文搜索 MCP 服务器，为 AI Agent（如 Cursor、Claude Desktop）提供 OpenAlex 全功能搜索和查询能力。

## 支持的实体类型

| 实体类型 | 搜索 | 获取 | 说明 |
|----------|------|------|------|
| `works` | ✅ | ✅ | 论文、书籍、数据集、学位论文 |
| `authors` | ✅ | ✅ | 作者 |
| `sources` | ✅ | ✅ | 期刊、会议、预印本服务器 |
| `institutions` | ✅ | ✅ | 大学、研究机构 |
| `topics` | ✅ | ✅ | 主题分类 |
| `publishers` | ✅ | ✅ | 出版商 |
| `funders` | ✅ | ✅ | 资助机构 |
| `continents` | ✅ | ✅ | 大洲 |
| `countries` | ✅ | ✅ | 国家 |

## 快速开始

### 方式一：uvx 免安装运行（推荐）

```bash
uvx --from git+https://github.com/h-lu/openalex openalex-mcp
```

### 方式二：本地运行

```bash
cd /Users/wangxq/Documents/openalex
uv sync
uv run openalex-mcp
```

## 配置 Cursor

编辑 `~/.cursor/mcp.json`:

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

## 工具详解

### 1. `search_openalex` - 统一搜索

**参数:**
- `query` (必需): 搜索关键词
- `entity_type`: 实体类型 (默认 `"works"`)
  - `"works"` - 论文
  - `"authors"` - 作者
  - `"sources"` - 期刊
  - `"institutions"` - 机构
  - `"topics"` - 主题
  - `"publishers"` - 出版商
  - `"funders"` - 资助机构
  - `"continents"` - 大洲
  - `"countries"` - 国家
- `year_from` / `year_to`: 年份范围 (仅 works)
- `country`: 国家代码 (如 "CN", "US")
- `institution`: 机构名称
- `open_access`: 是否开放获取 (仅 works)
- `sort_by`: 排序方式
  - `"cited_by_count"` - 引用数 (默认)
  - `"publication_date"` - 发表日期
  - `"relevance"` - 相关度
  - `"works_count"` - 论文数
- `limit`: 返回数量 (默认 10)

**示例:**
```
搜索 2024 年的深度学习论文:
search_openalex("deep learning", year_from=2024)

搜索中国的机构:
search_openalex("university", entity_type="institutions", country="CN")

搜索开放获取的 AI 论文:
search_openalex("artificial intelligence", open_access=True)

搜索资助机构:
search_openalex("NSF", entity_type="funders")

搜索主题:
search_openalex("machine learning", entity_type="topics")
```

### 2. `fetch_openalex` - 获取详情

**参数:**
- `identifier` (必需): 实体标识符
  - OpenAlex ID: `W4391403992`, `A5012301204`, `I27837315`
  - DOI: `10.1038/s41586-021-03819-2` (仅论文)
  - ORCID: `0000-0001-6187-6610` (仅作者)
  - ROR: `https://ror.org/042nb2s44` (仅机构)
- `entity_type`: 实体类型 (默认 `"work"`)
  - `"work"`, `"author"`, `"source"`, `"institution"`, `"topic"`, `"publisher"`, `"funder"`, `"continent"`, `"country"`
- `include_related`: 是否包含相关信息 (默认 False)
  - 作者: 代表作
  - 期刊: 高引论文
  - 机构: 知名作者
  - 主题: 代表论文

**示例:**
```
获取论文详情:
fetch_openalex("10.1038/s41586-021-03819-2")

获取作者及其代表作:
fetch_openalex("A5012301204", entity_type="author", include_related=True)

获取机构详情:
fetch_openalex("I27837315", entity_type="institution")

获取 MIT 及其知名作者:
fetch_openalex("I63966007", entity_type="institution", include_related=True)
```

## 使用场景示例

### 1. 查找某领域的高引论文
```
search_openalex("large language model", year_from=2023, sort_by="cited_by_count", limit=20)
```

### 2. 查找某机构的研究成果
```
search_openalex("climate change", institution="MIT", year_from=2020)
```

### 3. 查找某国家的顶级作者
```
search_openalex("", entity_type="authors", country="CN", sort_by="cited_by_count", limit=10)
```

### 4. 查找资助机构
```
search_openalex("National Natural Science Foundation", entity_type="funders")
fetch_openalex("F1234567", entity_type="funder", include_related=True)
```

### 5. 探索研究主题
```
search_openalex("quantum computing", entity_type="topics")
fetch_openalex("T12345", entity_type="topic", include_related=True)
```

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `OPENALEX_EMAIL` | 用于 OpenAlex API 的邮箱（提高速率限制 1→10 次/秒） | `openalex-mcp@example.com` |

## 开发

### 运行测试

```bash
uv run python test_server.py
```

### HTTP 模式调试

```bash
uv run openalex-mcp --http
# 访问 http://localhost:8000
```

## 数据来源

[OpenAlex](https://openalex.org) - 免费开放的学术文献数据库
- 2.5 亿+ 学术论文
- 1 亿+ 作者
- 25 万+ 期刊和会议
- 10 万+ 机构
- 4500+ 资助机构

## License

MIT
