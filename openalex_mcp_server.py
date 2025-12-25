"""
OpenAlex MCP Server - 使用 FastMCP 构建的学术论文搜索工具

提供给 AI Agent (如 Cursor, Claude Desktop) 使用的 MCP 工具，
用于搜索和获取 OpenAlex 上的学术论文信息。

支持的实体类型:
- works: 论文、书籍、数据集、学位论文
- authors: 作者
- sources: 期刊、会议、预印本服务器
- institutions: 大学、研究机构
- topics: 主题分类
- publishers: 出版商
- funders: 资助机构
- keywords: 关键词
- continents/countries: 地理位置

工具设计 (7个):
1. search_openalex - 简单搜索（用户友好接口）
2. query_openalex - 高级查询（支持原生 filter 语法、select、cursor）
3. fetch_openalex - 获取实体详情（支持 include_related）
4. sample_openalex - 随机采样（支持 seed 可重复）
5. batch_fetch_openalex - 批量 ID 查询（最多 50 个）
6. autocomplete_openalex - 实体自动补全
7. ngrams_openalex - 获取论文 N-grams 文本分析数据

运行方式:
    1. stdio 模式: python openalex_mcp_server.py
    2. http 模式: python openalex_mcp_server.py --http
"""

import os
import asyncio
import httpx
from typing import Optional, Literal
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

# 创建 MCP 服务器实例
mcp = FastMCP(
    name="OpenAlex",
    instructions="""
    OpenAlex 学术文献搜索工具 - 全球最大的开放学术数据库 (2.5亿+ 学术论文)。
    
    ## 核心工具 (7个)
    
    | 工具 | 用途 | 适用场景 |
    |------|------|----------|
    | search_openalex | 简单搜索 | 按关键词搜索论文、作者、机构 |
    | query_openalex | 高级查询 | 复杂过滤条件、分组聚合、游标分页 |
    | fetch_openalex | 获取详情 | 单个实体的完整信息 |
    | sample_openalex | 随机采样 | 可重复的随机抽样 |
    | batch_fetch_openalex | 批量获取 | 一次查询多个 ID (最多50个) |
    | autocomplete_openalex | 自动补全 | 快速获取实体 ID |
    | ngrams_openalex | N-grams | 论文全文的词频分析 |
    
    ## 实体类型
    works, authors, sources, institutions, topics, publishers, funders, keywords, continents, countries
    
    ## ⚠️ 最佳实践
    
    ### 两步查询模式
    查询特定作者/机构的论文时:
    1. 先用 autocomplete 获取 ID: autocomplete_openalex("Stanford", entity_type="institutions")
    2. 再用 query 过滤: query_openalex(filter="authorships.institutions.id:I97018004")
    
    ### 批量查询
    有多个 DOI/ID 时，使用 batch_fetch_openalex 而非循环调用 (性能提升 50x)
    
    ### 随机采样
    不要用随机页码采样，使用 sample_openalex 的 seed 参数确保可重复
    
    ### 字段选择
    使用 select 参数只获取需要的字段，大幅减少响应数据量:
    - 基础: "id,title,doi"
    - 详细: "id,title,doi,publication_year,cited_by_count,authorships"
    
    ### 分组聚合 (group_by)
    统计分析时使用 group_by，支持 30+ 分组方式:
    - 按年份: group_by="publication_year"
    - 按国家: group_by="authorships.countries"
    - 按期刊: group_by="primary_location.source.id"
    - 按开放获取: group_by="is_oa"
    
    ### 游标分页
    遍历大量数据时使用 cursor:
    - 首次: cursor="*"
    - 后续: 使用返回的 meta.next_cursor
    """
)

# API 配置
BASE_URL = "https://api.openalex.org"
OPENALEX_EMAIL = os.environ.get("OPENALEX_EMAIL", "openalex-mcp@example.com")
DEFAULT_PARAMS = {"mailto": OPENALEX_EMAIL}

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # 秒
RATE_LIMIT_DELAY = 5.0  # 遇到 429 时等待时间

# 实体类型映射
SEARCH_ENTITY_TYPES = Literal["works", "authors", "sources", "institutions", "topics", "publishers", "funders", "keywords", "continents", "countries"]
FETCH_ENTITY_TYPES = Literal["work", "author", "source", "institution", "topic", "publisher", "funder", "keyword", "continent", "country"]

ENTITY_ENDPOINTS = {
    "works": "works", "work": "works",
    "authors": "authors", "author": "authors",
    "sources": "sources", "source": "sources",
    "institutions": "institutions", "institution": "institutions",
    "topics": "topics", "topic": "topics",
    "publishers": "publishers", "publisher": "publishers",
    "funders": "funders", "funder": "funders",
    "keywords": "keywords", "keyword": "keywords",
    "continents": "continents", "continent": "continents",
    "countries": "countries", "country": "countries",
}


def _make_error_response(status_code: int, message: str, details: str = None) -> dict:
    """构建标准化错误响应"""
    error_types = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        429: "rate_limited",
        500: "server_error",
        502: "bad_gateway",
        503: "service_unavailable",
        504: "gateway_timeout",
    }
    
    error = {
        "error": True,
        "error_type": error_types.get(status_code, "unknown"),
        "status_code": status_code,
        "message": message,
    }
    
    if details:
        error["details"] = details
    
    # 添加建议
    if status_code == 404:
        error["suggestion"] = "检查实体 ID 是否正确，或尝试使用 autocomplete 搜索"
    elif status_code == 429:
        error["suggestion"] = "请求过于频繁，请等待几秒后重试"
    elif status_code == 400:
        error["suggestion"] = "检查 filter 语法是否正确，参考 resource://openalex-filters"
    
    return error


async def _request(endpoint: str, params: dict | None = None) -> dict:
    """发送异步 API 请求，带重试和速率限制处理"""
    url = f"{BASE_URL}/{endpoint}"
    all_params = {**DEFAULT_PARAMS, **(params or {})}
    
    last_error = None
    async with httpx.AsyncClient(timeout=30) as client:
        for attempt in range(MAX_RETRIES):
            try:
                response = await client.get(url, params=all_params)
                
                # 处理速率限制
                if response.status_code == 429:
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RATE_LIMIT_DELAY)
                        continue
                    return _make_error_response(
                        429, 
                        "请求过于频繁，已达到 API 速率限制",
                        f"已重试 {MAX_RETRIES} 次"
                    )
                
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code if e.response else 500
                
                # 4xx 错误不重试（除了 429）
                if 400 <= status_code < 500 and status_code != 429:
                    return _make_error_response(
                        status_code,
                        f"请求失败: {str(e)}",
                        e.response.text[:500] if e.response else None
                    )
                
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                    
            except httpx.TimeoutException:
                last_error = "请求超时"
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY)
                    
            except httpx.ConnectError as e:
                last_error = f"连接错误: {str(e)}"
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY)
    
    return _make_error_response(
        503,
        f"请求失败 (已重试 {MAX_RETRIES} 次)",
        str(last_error)
    )


# ============================================================================
# MCP Tools
# ============================================================================

@mcp.tool(
    name="search_openalex",
    description="简单搜索 OpenAlex 实体。适合基本查询，如按关键词搜索论文、作者或机构。",
    tags={"search", "openalex"}
)
async def search_openalex(
    query: str,
    entity_type: SEARCH_ENTITY_TYPES = "works",
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    country: Optional[str] = None,
    is_oa: Optional[bool] = None,
    sort: Literal["cited_by_count", "publication_date", "relevance", "works_count"] = "cited_by_count",
    limit: int = 15
) -> dict:
    """
    简单搜索 OpenAlex 实体。
    
    Args:
        query: 搜索关键词，支持 Boolean 语法如 "AI AND ML"、"deep learning" NOT NLP
        entity_type: 实体类型 (works/authors/sources/institutions/topics/publishers/funders/keywords)
        year_from: 起始年份 (仅 works 有效)
        year_to: 结束年份 (仅 works 有效)
        country: 国家代码如 CN, US, DE (对 works/authors/institutions 有效)
        is_oa: 是否开放获取 (仅 works 有效)
        sort: 排序方式
        limit: 返回数量 (默认15, 最大200)
    
    Returns:
        原始 OpenAlex API 响应，包含 meta 和 results
    
    示例:
        搜索 2024 年 AI 论文: search_openalex("artificial intelligence", year_from=2024)
        搜索中国机构: search_openalex("university", entity_type="institutions", country="CN")
        搜索 LLM 关键词: search_openalex("large language model", entity_type="keywords")
    """
    endpoint = ENTITY_ENDPOINTS.get(entity_type, "works")
    
    params = {"search": query, "per-page": min(limit, 200)}
    
    # 构建过滤器
    filters = []
    if entity_type == "works":
        if year_from and year_to:
            filters.append(f"publication_year:{year_from}-{year_to}")
        elif year_from:
            filters.append(f"publication_year:>={year_from}")
        elif year_to:
            filters.append(f"publication_year:<={year_to}")
        
        if is_oa is not None:
            filters.append(f"is_oa:{str(is_oa).lower()}")
        
        if country:
            filters.append(f"authorships.countries:{country.upper()}")
    
    elif entity_type == "authors" and country:
        filters.append(f"affiliations.institution.country_code:{country.upper()}")
    
    elif entity_type == "institutions" and country:
        filters.append(f"country_code:{country.upper()}")
    
    if filters:
        params["filter"] = ",".join(filters)
    
    # 排序
    sort_map = {
        "cited_by_count": "cited_by_count:desc",
        "publication_date": "publication_date:desc",
        "works_count": "works_count:desc",
    }
    if sort in sort_map:
        params["sort"] = sort_map[sort]
    
    return await _request(endpoint, params)


@mcp.tool(
    name="query_openalex",
    description="高级查询 OpenAlex，支持原生 filter 语法、字段选择和游标分页。适合复杂的组合查询。",
    tags={"query", "openalex", "advanced"}
)
async def query_openalex(
    entity_type: SEARCH_ENTITY_TYPES = "works",
    filter: Optional[str] = None,
    search: Optional[str] = None,
    sort: str = "cited_by_count:desc",
    group_by: Optional[str] = None,
    select: Optional[str] = None,
    cursor: Optional[str] = None,
    limit: int = 25
) -> dict:
    """
    高级查询 OpenAlex - 支持原生 filter 语法、字段选择和游标分页。
    
    Args:
        entity_type: 实体类型
        filter: OpenAlex 原生 filter 语法，支持:
            - 单个过滤: publication_year:2024
            - 范围: cited_by_count:>100 或 publication_year:2020-2024
            - AND (逗号): publication_year:2024,is_oa:true
            - OR (管道): publication_year:2023|2024
            - NOT (感叹号): publication_year:!2024
            - 嵌套: authorships.institutions.country_code:CN
        search: 搜索关键词，支持 Boolean: (AI AND ML) NOT NLP, "exact phrase"
        sort: 排序 (如 cited_by_count:desc, publication_date:desc, relevance_score:desc)
        group_by: 分组聚合字段，用于统计分析，支持 30+ 分组方式:
            - 按年份: publication_year
            - 按国家: authorships.countries
            - 按期刊: primary_location.source.id
            - 按开放获取: is_oa
            - 按类型: type
            - 按语言: language
            - 按机构类型: authorships.institutions.type
            - 按资助机构: funders.id
            - 按大洲: authorships.institutions.continent
        select: 选择返回字段 (如 "id,title,doi,cited_by_count")，减少响应数据量
        cursor: 游标分页，用于遍历大量数据。首次请求使用 "*"，后续使用返回的 next_cursor
        limit: 返回数量 (默认25, 最大200)
    
    Returns:
        原始 OpenAlex API 响应，包含 meta, results, 以及可能的 group_by 或 next_cursor
    
    常用 filter 示例:
        - 年份: publication_year:2024
        - 引用数: cited_by_count:>100
        - 开放获取: is_oa:true
        - 国家: authorships.countries:CN
        - 机构: authorships.institutions.id:I27837315
        - 期刊: primary_location.source.id:S23254222
        - 关键词: keywords.keyword:machine learning
        - 主题: primary_topic.field.id:F123
        - 语言: language:en
        - 类型: type:article
        - 资助机构: funders.id:F123456
        - 大洲: authorships.institutions.continent:asia
        
    字段选择 (select) 示例:
        - 基础: "id,title,doi"
        - 详细: "id,title,doi,publication_year,cited_by_count,authorships"
        
    游标分页示例:
        - 首次: cursor="*"
        - 后续: cursor=返回的 meta.next_cursor 值
        
    分组聚合 (group_by) 示例:
        - 统计每年发文量: query_openalex(filter="authorships.institutions.id:I97018004", group_by="publication_year")
        - 统计各国发文量: query_openalex(filter="publication_year:2024", group_by="authorships.countries")
        - 统计开放获取比例: query_openalex(filter="publication_year:2024", group_by="is_oa")
    """
    endpoint = ENTITY_ENDPOINTS.get(entity_type, "works")
    
    params = {"per-page": min(limit, 200)}
    
    if filter:
        params["filter"] = filter
    
    if search:
        params["search"] = search
    
    if sort:
        params["sort"] = sort
    
    if group_by:
        params["group_by"] = group_by
    
    if select:
        params["select"] = select
    
    if cursor:
        params["cursor"] = cursor
    
    return await _request(endpoint, params)


@mcp.tool(
    name="fetch_openalex",
    description="获取 OpenAlex 实体的详细信息。支持 ID、DOI、ORCID 等标识符。",
    tags={"fetch", "openalex"}
)
async def fetch_openalex(
    identifier: str,
    entity_type: FETCH_ENTITY_TYPES = "work",
    select: Optional[str] = None
) -> dict:
    """
    获取 OpenAlex 实体详情。
    
    Args:
        identifier: 实体标识符:
            - OpenAlex ID: W4391403992, A5012301204, I27837315
            - DOI: 10.1038/s41586-021-03819-2 (仅 work)
            - ORCID: 0000-0001-6187-6610 (仅 author)
            - ROR: https://ror.org/042nb2s44 (仅 institution)
        entity_type: 实体类型 (work/author/source/institution/topic/publisher/funder/keyword)
        select: 选择返回字段 (如 "id,title,doi,cited_by_count")
    
    Returns:
        原始 OpenAlex API 响应，包含实体完整信息
    
    示例:
        获取论文: fetch_openalex("10.1038/s41586-021-03819-2")
        获取作者: fetch_openalex("A5012301204", entity_type="author")
        获取机构: fetch_openalex("I63966007", entity_type="institution")
    
    注意:
        - 如需获取相关实体，可使用返回结果中的 ID 列表进行后续查询
        - 例如: 论文的 authorships[].author.id 可用于获取作者详情
    """
    endpoint = ENTITY_ENDPOINTS.get(entity_type, "works")
    
    # 规范化标识符
    id_clean = identifier.strip().replace("https://openalex.org/", "")
    
    # DOI 格式化
    if entity_type == "work" and (id_clean.startswith("10.") or "doi.org" in id_clean):
        if not id_clean.startswith("https://doi.org/"):
            id_clean = f"https://doi.org/{id_clean.replace('doi.org/', '')}"
    
    # ORCID 格式化
    if entity_type == "author" and id_clean.startswith("0000-"):
        id_clean = f"https://orcid.org/{id_clean}"
    
    params = {}
    if select:
        params["select"] = select
    
    return await _request(f"{endpoint}/{id_clean}", params if params else None)


@mcp.tool(
    name="sample_openalex",
    description="随机采样 OpenAlex 实体。支持可重复抽样（使用 seed）。",
    tags={"sample", "openalex", "random"}
)
async def sample_openalex(
    entity_type: SEARCH_ENTITY_TYPES = "works",
    sample_size: int = 20,
    seed: Optional[int] = None,
    filter: Optional[str] = None,
    select: Optional[str] = None
) -> dict:
    """
    随机采样 OpenAlex 实体。
    
    ⚠️ 重要: 不要使用随机页码来采样，这会导致偏差！使用此工具的 sample 参数。
    
    Args:
        entity_type: 实体类型
        sample_size: 采样数量 (默认20, 最大10000)
        seed: 随机种子，相同 seed 返回相同结果，用于可重复采样
        filter: 可选的过滤器，在采样前先过滤
        select: 选择返回字段
    
    Returns:
        原始 OpenAlex API 响应，包含随机采样的实体
    
    示例:
        随机采样 100 篇论文: sample_openalex(sample_size=100)
        可重复采样: sample_openalex(sample_size=50, seed=42)
        采样 2024 年论文: sample_openalex(sample_size=50, filter="publication_year:2024")
    
    大规模采样策略:
        对于 >10000 的采样，使用多次采样 + 不同 seed + 去重:
        1. sample_openalex(sample_size=1000, seed=1)
        2. sample_openalex(sample_size=1000, seed=2)
        3. sample_openalex(sample_size=1000, seed=3)
        然后按 ID 去重
    """
    endpoint = ENTITY_ENDPOINTS.get(entity_type, "works")
    
    params = {"sample": min(sample_size, 10000)}
    
    if seed is not None:
        params["seed"] = seed
    
    if filter:
        params["filter"] = filter
    
    if select:
        params["select"] = select
    
    return await _request(endpoint, params)


@mcp.tool(
    name="batch_fetch_openalex",
    description="批量获取多个实体。使用管道符一次性查询最多 50 个 ID，避免循环调用。",
    tags={"batch", "openalex", "bulk"}
)
async def batch_fetch_openalex(
    identifiers: list[str],
    entity_type: SEARCH_ENTITY_TYPES = "works",
    select: Optional[str] = None
) -> dict:
    """
    批量获取多个 OpenAlex 实体。
    
    ⚠️ 重要: 有多个 ID 时，使用此工具而非循环调用 fetch_openalex，性能提升 50x！
    
    Args:
        identifiers: 实体标识符列表 (最多 50 个)
            - OpenAlex IDs: ["W123", "W456", "W789"]
            - DOIs: ["10.1038/xxx", "10.1126/yyy"]
        entity_type: 实体类型 (works/authors/sources/institutions 等)
        select: 选择返回字段
    
    Returns:
        原始 OpenAlex API 响应，包含批量查询结果
    
    示例:
        批量获取论文: batch_fetch_openalex(["W123", "W456", "W789"])
        批量获取 DOI: batch_fetch_openalex(["10.1038/xxx", "10.1126/yyy"])
        只获取特定字段: batch_fetch_openalex(["W1", "W2"], select="id,title,cited_by_count")
    """
    if not identifiers:
        raise ToolError("identifiers 不能为空")
    
    if len(identifiers) > 50:
        raise ToolError(f"最多支持 50 个标识符，当前 {len(identifiers)} 个")
    
    endpoint = ENTITY_ENDPOINTS.get(entity_type, "works")
    
    # 处理标识符
    processed_ids = []
    for id_str in identifiers:
        id_clean = id_str.strip().replace("https://openalex.org/", "")
        
        # DOI 格式化
        if entity_type == "works" and (id_clean.startswith("10.") or "doi.org" in id_clean):
            if not id_clean.startswith("https://doi.org/"):
                id_clean = f"https://doi.org/{id_clean.replace('doi.org/', '')}"
        
        processed_ids.append(id_clean)
    
    # 确定过滤字段
    if entity_type == "works":
        # 检查是否包含 DOI
        if any(id_str.startswith("https://doi.org/") or id_str.startswith("10.") for id_str in processed_ids):
            filter_field = "doi"
        else:
            filter_field = "ids.openalex"
    else:
        filter_field = "ids.openalex"
    
    # 使用管道符连接
    filter_value = "|".join(processed_ids)
    
    params = {
        "filter": f"{filter_field}:{filter_value}",
        "per-page": min(len(identifiers), 50)
    }
    
    if select:
        params["select"] = select
    
    return await _request(endpoint, params)


@mcp.tool(
    name="autocomplete_openalex",
    description="实体名称自动补全。快速获取匹配实体的 ID，用于后续查询。",
    tags={"autocomplete", "openalex"}
)
async def autocomplete_openalex(
    query: str,
    entity_type: Literal["works", "authors", "sources", "institutions", "topics", "publishers", "funders"] = "works"
) -> dict:
    """
    实体名称自动补全。
    
    用于快速查找实体 ID，实现两步查询模式:
    1. 用 autocomplete 获取实体 ID
    2. 用 query_openalex 的 filter 查询相关数据
    
    Args:
        query: 搜索词
        entity_type: 实体类型
    
    Returns:
        原始 OpenAlex API 响应，包含匹配实体的 ID 和名称
    
    示例:
        查找作者: autocomplete_openalex("Einstein", entity_type="authors")
        查找期刊: autocomplete_openalex("Nature", entity_type="sources")
        查找机构: autocomplete_openalex("MIT", entity_type="institutions")
    
    两步查询示例:
        1. result = autocomplete_openalex("Stanford", entity_type="institutions")
           → 获取 ID: I97018004
        2. query_openalex(filter="authorships.institutions.id:I97018004,publication_year:2024")
    """
    return await _request(f"autocomplete/{entity_type}", {"q": query})


@mcp.tool(
    name="ngrams_openalex",
    description="获取论文的 N-grams 数据，用于文本分析和词频统计。",
    tags={"ngrams", "openalex", "text"}
)
async def ngrams_openalex(
    work_id: str,
    ngram: Optional[str] = None
) -> dict:
    """
    获取论文的 N-grams (词频) 数据。
    
    N-grams 是论文全文中的词或短语及其出现频率，可用于:
    - 文本分析和关键词提取
    - 词频统计和趋势分析
    - 论文内容特征分析
    
    Args:
        work_id: 论文 ID (OpenAlex ID 如 W2023271753，或 DOI 如 10.1038/xxx)
        ngram: 可选，过滤特定的 n-gram (如 "machine learning")
    
    Returns:
        原始 OpenAlex API 响应，包含 ngrams 列表:
        - ngram: 词或短语
        - ngram_count: 在该论文中出现的次数
        - ngram_tokens: 词的数量 (1=unigram, 2=bigram, 等)
        - term_frequency: 词频 (出现次数 / 总词数)
    
    示例:
        获取论文全部 N-grams: ngrams_openalex("W2023271753")
        搜索特定词: ngrams_openalex("W2023271753", ngram="climate change")
        使用 DOI: ngrams_openalex("10.1038/s41586-021-03819-2")
    
    注意:
        - 仅支持部分论文 (有全文数据的论文)
        - 返回按 term_frequency 降序排列
        - 可能包含大量数据，建议使用 ngram 参数过滤
    """
    # 规范化 work_id
    id_clean = work_id.strip().replace("https://openalex.org/", "")
    
    # DOI 格式化
    if id_clean.startswith("10.") or "doi.org" in id_clean:
        if not id_clean.startswith("https://doi.org/"):
            id_clean = f"https://doi.org/{id_clean.replace('doi.org/', '')}"
    
    params = {}
    if ngram:
        params["search"] = ngram
    
    return await _request(f"works/{id_clean}/ngrams", params if params else None)


# ============================================================================
# MCP Resource: Filter 参考手册
# ============================================================================

@mcp.resource("resource://openalex-filters")
def get_filter_reference() -> str:
    """OpenAlex Filter 语法快速参考"""
    return """
# OpenAlex Filter 语法参考

## 逻辑运算
- AND (逗号): filter=A,B  →  A 且 B
- OR (管道):  filter=A|B  →  A 或 B
- NOT (感叹号): filter=!A  →  非 A
- 范围: filter=field:min-max 或 filter=field:>100

## Works 常用过滤器
| 过滤器 | 示例 | 说明 |
|--------|------|------|
| publication_year | publication_year:2024 | 发表年份 |
| cited_by_count | cited_by_count:>100 | 引用数 |
| is_oa | is_oa:true | 开放获取 |
| language | language:en | 语言 |
| type | type:article | 类型(article/book/dataset) |
| is_retracted | is_retracted:false | 是否撤稿 |
| authorships.countries | authorships.countries:CN | 作者国家 |
| authorships.institutions.id | authorships.institutions.id:I27837315 | 作者机构 |
| authorships.institutions.continent | authorships.institutions.continent:asia | 大洲 |
| primary_location.source.id | primary_location.source.id:S23254222 | 期刊 |
| primary_topic.field.id | primary_topic.field.id:F123 | 领域 |
| keywords.keyword | keywords.keyword:machine learning | 关键词 |
| funders.id | funders.id:F1234567 | 资助机构 |
| abstract.search | abstract.search:climate change | 摘要文本搜索 |

## 搜索语法 (search 参数)
- AND: machine AND learning
- OR: AI OR ML
- NOT: deep learning NOT NLP
- 精确短语: "large language model"
- 组合: (AI AND ML) NOT (NLP OR sentiment)

## 常见 ID 前缀
- W: Works (论文)
- A: Authors (作者)
- S: Sources (期刊)
- I: Institutions (机构)
- T: Topics (主题)
- P: Publishers (出版商)
- F: Funders (资助机构)

## 字段选择 (select 参数)
- 基础: select=id,title,doi
- 详细: select=id,title,doi,publication_year,cited_by_count,authorships
- 注意: 使用 select 可以大幅减少响应数据量

## 游标分页 (cursor 参数)
- 首次请求: cursor=*
- 后续请求: cursor=返回的 meta.next_cursor 值
- 适用于需要遍历大量数据的场景

## 分组聚合 (group_by 参数)
支持 30+ 分组方式，常用:
- publication_year: 按年份统计
- authorships.countries: 按国家统计  
- primary_location.source.id: 按期刊统计
- is_oa: 按开放获取状态统计
- type: 按文献类型统计
- language: 按语言统计
- authorships.institutions.type: 按机构类型统计
- authorships.institutions.continent: 按大洲统计

示例: 统计某机构每年发文量
  query_openalex(filter="authorships.institutions.id:I97018004", group_by="publication_year")

## 最佳实践
1. 两步查询: 先用 autocomplete 获取 ID，再用 filter 过滤
2. 批量查询: 多个 ID 使用管道符 | 连接，一次查询
3. 随机采样: 使用 sample 参数，不要用随机页码
4. 减少数据: 使用 select 只获取需要的字段
5. 统计分析: 使用 group_by 进行分组聚合，避免拉取全量数据
"""


# ============================================================================
# Entry Point
# ============================================================================

def main():
    """入口点函数"""
    import sys
    if "--http" in sys.argv:
        print("Starting OpenAlex MCP Server in HTTP mode on port 8000...")
        mcp.run(transport="http", port=8000)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
