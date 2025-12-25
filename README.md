# OpenAlex MCP Server

OpenAlex 学术文献搜索 MCP 服务器，为 AI Agent 提供强大的论文搜索和查询能力。

## 三个核心工具

| 工具 | 用途 | 适用场景 |
|------|------|----------|
| `search_openalex` | 简单搜索 | 基本关键词搜索 |
| `query_openalex` | 高级查询 | 复杂过滤器组合 |
| `fetch_openalex` | 获取详情 | 按 ID/DOI 获取完整信息 |

## 支持的实体类型

works, authors, sources, institutions, topics, publishers, funders, keywords, continents, countries

## 快速配置 Cursor

编辑 `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "openalex": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/h-lu/openalex-mcp", "openalex-mcp"],
      "env": {
        "OPENALEX_EMAIL": "your-email@example.com"
      }
    }
  }
}
```

## 工具使用

### 1. `search_openalex` - 简单搜索

```
search_openalex("deep learning", year_from=2024, is_oa=True)
search_openalex("MIT", entity_type="institutions", country="US")
search_openalex("machine learning", entity_type="keywords")
```

### 2. `query_openalex` - 高级查询 (支持原生 filter)

**Filter 语法:**
- AND (逗号): `publication_year:2024,is_oa:true`
- OR (管道): `publication_year:2023|2024`
- NOT (感叹号): `publication_year:!2024`
- 范围: `cited_by_count:>100`

**示例:**
```
# 2024年中国 AI 高引论文
query_openalex(
    filter="publication_year:2024,authorships.countries:CN,cited_by_count:>50",
    search="artificial intelligence"
)

# MIT 在 Nature 发表的论文
query_openalex(
    filter="authorships.institutions.id:I63966007,primary_location.source.id:S137773608"
)

# 按年份分组统计
query_openalex(
    filter="authorships.countries:CN",
    search="LLM",
    group_by="publication_year"
)
```

**常用过滤器:**
| 过滤器 | 示例 |
|--------|------|
| publication_year | `publication_year:2024` |
| cited_by_count | `cited_by_count:>100` |
| is_oa | `is_oa:true` |
| language | `language:en` |
| type | `type:article` |
| authorships.countries | `authorships.countries:CN` |
| authorships.institutions.id | `authorships.institutions.id:I27837315` |
| primary_location.source.id | `primary_location.source.id:S23254222` |
| keywords.keyword | `keywords.keyword:machine learning` |
| funders.id | `funders.id:F1234567` |

### 3. `fetch_openalex` - 获取详情

```
# 通过 DOI
fetch_openalex("10.1038/s41586-021-03819-2")

# 通过 ID，包含相关实体
fetch_openalex("A5012301204", entity_type="author", include_related=True)

# 获取机构详情和知名作者
fetch_openalex("I63966007", entity_type="institution", include_related=True)
```

## 返回的论文详情

论文详情包含丰富信息:
- 基本信息: title, doi, year, type, language
- 引用: cited_by_count, fwci (影响因子)
- 作者: 姓名、机构、国家、ORCID
- **关键词**: keywords (带相关性分数)
- **资助**: funders, awards
- **可持续发展目标**: sustainable_development_goals
- 摘要: abstract (自动重建)
- 开放获取: is_oa, oa_status, pdf_url

## 本地开发

```bash
# 安装
cd /Users/wangxq/Documents/openalex
uv sync

# 运行
uv run openalex-mcp

# HTTP 调试模式
uv run openalex-mcp --http
```

## 数据来源

[OpenAlex](https://openalex.org) - 2.5亿+ 学术论文

## License

MIT
