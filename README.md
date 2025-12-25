# OpenAlex MCP Server

OpenAlex 学术文献搜索 MCP 服务器，为 AI Agent 提供强大的论文搜索和查询能力。

---

## 📚 什么是 OpenAlex?

[OpenAlex](https://openalex.org) 是由非营利组织 OurResearch 于 2022 年推出的**免费开放学术数据库**，命名灵感来自古代亚历山大图书馆。它是 Elsevier Scopus 和 Clarivate Web of Science 等商业数据库的开放替代品。

### 数据规模

| 指标 | 数量 |
|------|------|
| 学术论文 | **2.6 亿+** |
| 数据源 | 25 万+ (期刊、会议、预印本) |
| 作者 | 9000 万+ |
| 机构 | 10 万+ |
| 日更新 | 数万篇新论文 |

### 收录内容

- 📄 期刊论文、会议论文、预印本
- 📘 书籍、书籍章节
- 📊 数据集、软件
- 🎓 博士/硕士论文
- 📑 灰色文献 (Grey Literature)

### OpenAlex 能做什么类型的研究?

| 研究领域 | 应用场景 |
|----------|----------|
| **文献计量学 (Bibliometrics)** | 引用分析、影响因子研究、论文产出统计 |
| **科学计量学 (Scientometrics)** | 学科发展趋势、研究前沿识别、热点追踪 |
| **合作网络分析** | 机构合作、国际合作、作者合作网络 |
| **研究评估** | 机构评估、团队产出分析、资助效果评估 |
| **知识图谱** | 概念关联、引用网络、主题演化 |
| **开放获取研究** | OA 比例分析、OA 政策效果评估 |
| **科研情报** | 竞争对手分析、人才发现、合作伙伴识别 |
| **研究趋势** | 新兴领域识别、跨学科研究、技术预见 |

### 相比商业数据库的优势

| 特性 | OpenAlex | Scopus/WoS |
|------|----------|------------|
| 成本 | ✅ 免费 | ❌ 昂贵订阅 |
| API 访问 | ✅ 免费无限制 | ⚠️ 受限 |
| 数据下载 | ✅ CC0 许可 | ❌ 版权限制 |
| 覆盖范围 | ✅ 更广泛 (含预印本、灰色文献) | ⚠️ 偏向传统期刊 |
| 语言多样性 | ✅ 多语言 | ⚠️ 偏向英语 |
| 全球南方覆盖 | ✅ 更包容 | ⚠️ 相对较少 |

---

## 七个核心工具

| 工具 | 用途 | 适用场景 |
|------|------|----------|
| `search_openalex` | 简单搜索 | 基本关键词搜索 |
| `query_openalex` | 高级查询 | 复杂过滤器、分组聚合、游标分页 |
| `fetch_openalex` | 获取详情 | 按 ID/DOI 获取完整信息 |
| `sample_openalex` | 随机采样 | 可重复的随机样本 |
| `batch_fetch_openalex` | 批量查询 | 一次查询多个 ID (最多50个) |
| `autocomplete_openalex` | 自动补全 | 快速获取实体 ID |
| `ngrams_openalex` | N-grams | 论文全文词频分析 |

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

## 最佳实践

⚠️ **重要**: 遵循 OpenAlex 官方 LLM API 指南

| ❌ 不要 | ✅ 应该 |
|--------|--------|
| 用随机页码采样 | 用 `sample_openalex` + `seed` |
| 循环查询多个 ID | 用 `batch_fetch_openalex` |
| 直接用名称过滤 | 先用 `autocomplete` 获取 ID |
| 获取全部字段 | 用 `select` 只取需要的 |
| 拉取全量数据统计 | 用 `group_by` 分组聚合 |

---

## 复杂搜索示例

### 📌 场景 1: 两步查询模式 (推荐)

**目标**: 查找斯坦福大学 2024 年发表的 AI 高引论文

```python
# Step 1: 获取机构 ID
result = autocomplete_openalex("Stanford University", entity_type="institutions")
# → I97018004

# Step 2: 使用 ID 查询
query_openalex(
    filter="authorships.institutions.id:I97018004,publication_year:2024",
    search="artificial intelligence",
    sort="cited_by_count:desc",
    select="id,title,doi,cited_by_count",
    limit=10
)
```

### 📌 场景 2: 多国合作论文分析

**目标**: 查找中国与美国合作发表的高引论文 (同时有两国作者)

```python
# 使用 + 符号表示 AND (两国都有作者)
query_openalex(
    filter="authorships.countries:CN+US,cited_by_count:>100,publication_year:2020-2024",
    sort="cited_by_count:desc",
    select="id,title,cited_by_count,authorships",
    limit=20
)
```

### 📌 场景 3: 多条件 OR 查询

**目标**: 搜索中国 OR 美国作者 2023-2024 年发表的 LLM 论文

```python
# 使用 | 符号表示 OR
query_openalex(
    filter="authorships.countries:CN|US,publication_year:2023|2024,cited_by_count:>50",
    search="large language model",
    sort="cited_by_count:desc"
)
```

### 📌 场景 4: 特定期刊分析

**目标**: 分析 Nature 期刊近 5 年气候变化研究趋势

```python
# Step 1: 获取期刊 ID
autocomplete_openalex("Nature", entity_type="sources")
# → S137773608

# Step 2: 按年份分组统计
query_openalex(
    filter="primary_location.source.id:S137773608,publication_year:2020-2024",
    search="climate change",
    group_by="publication_year"
)
```

### 📌 场景 5: 高引论文引用网络分析

**目标**: 找出引用 "Deep Learning" (Nature 2015) 论文最多的后续研究

```python
# Step 1: 获取论文详情
fetch_openalex("W2103795898")  # Deep learning paper

# Step 2: 查询引用该论文的高引论文
query_openalex(
    filter="cites:W2103795898",
    sort="cited_by_count:desc",
    select="id,title,cited_by_count,publication_year",
    limit=20
)
```

### 📌 场景 6: 资助机构研究分析

**目标**: 分析 NSF 资助的 AI 论文产出

```python
# Step 1: 获取 NSF 的 ID
autocomplete_openalex("National Science Foundation", entity_type="funders")
# → F4320332161

# Step 2: 查询并按年份分组
query_openalex(
    filter="funders.id:F4320332161",
    search="artificial intelligence",
    group_by="publication_year"
)
```

### 📌 场景 7: 高级布尔搜索

**目标**: 搜索医疗 AI 论文，排除综述类

```python
query_openalex(
    search='("machine learning" OR "deep learning") AND (healthcare OR medical) NOT review',
    filter="publication_year:2024,is_oa:true,language:en,type:article",
    sort="cited_by_count:desc",
    select="id,title,cited_by_count,type"
)
```

### 📌 场景 8: 作者研究脉络分析

**目标**: 分析 Yoshua Bengio 的研究轨迹

```python
# Step 1: 搜索作者
search_openalex("Yoshua Bengio", entity_type="authors", limit=1)
# → A1909006565

# Step 2: 获取作者详情 (含机构)
fetch_openalex("A1909006565", entity_type="author")

# Step 3: 获取代表作
query_openalex(
    filter="author.id:A1909006565",
    sort="cited_by_count:desc",
    select="id,title,cited_by_count,publication_year,funders",
    limit=10
)

# Step 4: 分析研究主题分布
query_openalex(
    filter="author.id:A1909006565",
    group_by="primary_topic.field.id"
)
```

### 📌 场景 9: 批量 DOI 查询

**目标**: 一次性获取多篇经典论文信息

```python
# 比循环调用快 50 倍!
batch_fetch_openalex(
    identifiers=[
        "10.1038/nature14539",       # Deep learning
        "10.1162/neco.1997.9.8.1735", # LSTM
        "10.1145/3065386",            # AlexNet
    ],
    select="id,title,cited_by_count,publication_year"
)
```

### 📌 场景 10: 可重复随机采样

**目标**: 获取可复现的随机样本用于研究

```python
# 相同 seed 返回相同结果
sample_openalex(
    sample_size=100,
    seed=42,
    filter="publication_year:2024,is_oa:true",
    select="id,title,doi"
)

# 大规模采样: 多次采样 + 去重
for seed in range(1, 6):
    sample_openalex(sample_size=1000, seed=seed, filter="publication_year:2024")
# 然后按 ID 去重
```

---

## Filter 语法速查

| 运算符 | 语法 | 示例 | 说明 |
|--------|------|------|------|
| AND | 逗号 `,` | `year:2024,is_oa:true` | 同时满足 |
| OR | 管道 `\|` | `year:2023\|2024` | 满足任一 |
| AND (同字段) | 加号 `+` | `countries:CN+US` | 两国都有作者 |
| NOT | 感叹号 `!` | `year:!2024` | 排除 |
| 大于 | `>` | `cited_by_count:>100` | 引用大于 100 |
| 小于 | `<` | `cited_by_count:<50` | 引用小于 50 |
| 范围 | `-` | `year:2020-2024` | 年份区间 |

### 常用过滤器

| 过滤器 | 说明 | 示例 |
|--------|------|------|
| `publication_year` | 发表年份 | `2024` 或 `2020-2024` |
| `cited_by_count` | 引用数 | `>100` 或 `50-200` |
| `is_oa` | 开放获取 | `true` 或 `false` |
| `language` | 语言 | `en`, `zh`, `de` |
| `type` | 文献类型 | `article`, `book`, `dataset` |
| `authorships.countries` | 作者国家 | `CN`, `US`, `CN\|US` |
| `authorships.institutions.id` | 作者机构 | `I97018004` (Stanford) |
| `primary_location.source.id` | 期刊 | `S137773608` (Nature) |
| `cites` | 引用了某论文 | `W2103795898` |
| `cited_by` | 被某论文引用 | `W2103795898` |
| `funders.id` | 资助机构 | `F4320332161` (NSF) |
| `abstract.search` | 摘要搜索 | `climate change` |
| `is_retracted` | 是否撤稿 | `false` |

### 布尔搜索语法 (search 参数)

```
"exact phrase"           # 精确短语
AND                      # 且
OR                       # 或
NOT                      # 非
(A OR B) AND C           # 括号组合
"machine learning" NOT review
```

---

## group_by 分组聚合

用于统计分析，避免拉取全量数据：

```python
query_openalex(filter="...", group_by="publication_year")           # 按年份
query_openalex(filter="...", group_by="authorships.countries")      # 按国家
query_openalex(filter="...", group_by="primary_location.source.id") # 按期刊
query_openalex(filter="...", group_by="is_oa")                      # 按开放获取
query_openalex(filter="...", group_by="type")                       # 按类型
query_openalex(filter="...", group_by="language")                   # 按语言
query_openalex(filter="...", group_by="primary_topic.field.id")     # 按研究领域
query_openalex(filter="...", group_by="authorships.institutions.type") # 按机构类型
```

⚠️ **注意**: `group_by` 一次只支持一个维度。多维度分析需要多次查询后合并。

---

## 游标分页 (遍历大量数据)

```python
# 首次请求
result = query_openalex(filter="publication_year:2024", cursor="*", limit=200)

# 后续请求 (使用返回的 next_cursor)
next_cursor = result["meta"]["next_cursor"]
result = query_openalex(filter="publication_year:2024", cursor=next_cursor, limit=200)

# 循环直到 next_cursor 为 None
```

---

## 错误处理

所有工具在失败时返回结构化错误：

```json
{
  "error": true,
  "error_type": "not_found",
  "status_code": 404,
  "message": "请求失败: 404 Client Error",
  "suggestion": "检查实体 ID 是否正确，或尝试使用 autocomplete 搜索"
}
```

错误类型: `bad_request`, `not_found`, `rate_limited`, `server_error`

---

## 本地开发

```bash
cd /Users/wangxq/Documents/openalex
uv sync
uv run openalex-mcp        # stdio 模式
uv run openalex-mcp --http # HTTP 调试
uv run python test_server.py  # 运行测试
```

## 数据来源

[OpenAlex](https://openalex.org) - 2.5亿+ 学术论文

## License

MIT
