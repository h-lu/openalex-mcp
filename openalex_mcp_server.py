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

工具设计 (3个):
1. search_openalex - 简单搜索（用户友好接口）
2. query_openalex - 高级查询（支持原生 filter 语法）
3. fetch_openalex - 获取实体详情

运行方式:
    1. stdio 模式: python openalex_mcp_server.py
    2. http 模式: python openalex_mcp_server.py --http
"""

import datetime
import os
import requests
from typing import Optional, Literal
from fastmcp import FastMCP

# 创建 MCP 服务器实例
mcp = FastMCP(
    name="OpenAlex",
    instructions="""
    OpenAlex 学术文献搜索工具。提供三个核心工具：
    
    1. search_openalex - 简单搜索（适合基本查询）
    2. query_openalex - 高级查询（支持复杂过滤器组合）
    3. fetch_openalex - 获取实体详情
    
    支持的实体: works, authors, sources, institutions, topics, publishers, funders, keywords, continents, countries
    
    数据来源: OpenAlex (https://openalex.org) - 2.5亿+ 学术论文
    """
)

# API 配置
BASE_URL = "https://api.openalex.org"
OPENALEX_EMAIL = os.environ.get("OPENALEX_EMAIL", "openalex-mcp@example.com")
DEFAULT_PARAMS = {"mailto": OPENALEX_EMAIL}

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


def _request(endpoint: str, params: dict | None = None) -> dict:
    """发送 API 请求"""
    url = f"{BASE_URL}/{endpoint}"
    all_params = {**DEFAULT_PARAMS, **(params or {})}
    response = requests.get(url, params=all_params, timeout=30)
    response.raise_for_status()
    return response.json()


def _clean_id(id_str: str) -> str:
    """清理 OpenAlex ID，移除 URL 前缀"""
    if id_str:
        return id_str.replace("https://openalex.org/", "")
    return id_str


def _format_work_brief(w: dict) -> dict:
    """格式化论文简要信息"""
    auths = w.get("authorships", [])
    loc = w.get("primary_location", {}) or {}
    src = loc.get("source", {}) or {}
    return {
        "id": _clean_id(w.get("id", "")),
        "title": w.get("title"),
        "doi": w.get("doi"),
        "year": w.get("publication_year"),
        "cited_by_count": w.get("cited_by_count"),
        "first_author": auths[0].get("author", {}).get("display_name") if auths else None,
        "authors_count": len(auths),
        "journal": src.get("display_name"),
        "type": w.get("type"),
        "is_oa": w.get("open_access", {}).get("is_oa"),
    }


def _format_work_full(w: dict) -> dict:
    """格式化论文完整信息"""
    # 作者信息
    authors = [{
        "name": a.get("author", {}).get("display_name"),
        "id": _clean_id(a.get("author", {}).get("id", "")),
        "orcid": a.get("author", {}).get("orcid"),
        "position": a.get("author_position"),
        "institutions": [i.get("display_name") for i in a.get("institutions", [])],
        "countries": a.get("countries", []),
    } for a in w.get("authorships", [])]
    
    # 位置信息
    loc = w.get("primary_location", {}) or {}
    src = loc.get("source", {}) or {}
    
    # 主题
    topic = w.get("primary_topic", {}) or {}
    
    # 关键词
    keywords = [{"keyword": k.get("display_name"), "score": round(k.get("score", 0), 3)} 
                for k in w.get("keywords", [])[:15]]
    
    # 资助/奖项 (新的 awards 字段)
    awards = w.get("awards", [])
    funders = [{
        "id": _clean_id(f.get("id", "")),
        "name": f.get("display_name"),
        "country": f.get("country_code"),
    } for f in w.get("funders", [])]
    
    # 可持续发展目标
    sdgs = [{
        "id": s.get("id"),
        "name": s.get("display_name"),
        "score": s.get("score"),
    } for s in w.get("sustainable_development_goals", [])]
    
    # 重建摘要
    abstract = None
    if w.get("abstract_inverted_index"):
        words = []
        for word, positions in w["abstract_inverted_index"].items():
            for pos in positions:
                words.append((pos, word))
        words.sort()
        abstract = " ".join(word for _, word in words)
    
    return {
        "id": _clean_id(w.get("id", "")),
        "title": w.get("title"),
        "doi": w.get("doi"),
        "publication_date": w.get("publication_date"),
        "publication_year": w.get("publication_year"),
        "type": w.get("type"),
        "language": w.get("language"),
        "cited_by_count": w.get("cited_by_count"),
        "fwci": w.get("fwci"),
        "is_retracted": w.get("is_retracted"),
        "is_oa": w.get("open_access", {}).get("is_oa"),
        "oa_status": w.get("open_access", {}).get("oa_status"),
        "pdf_url": loc.get("pdf_url"),
        "journal": src.get("display_name"),
        "publisher": src.get("host_organization_name"),
        "volume": w.get("biblio", {}).get("volume"),
        "issue": w.get("biblio", {}).get("issue"),
        "pages": f"{w.get('biblio', {}).get('first_page', '')}-{w.get('biblio', {}).get('last_page', '')}".strip("-"),
        "authors": authors,
        "keywords": keywords,
        "funders": funders,
        "awards": awards,
        "sustainable_development_goals": sdgs if sdgs else None,
        "primary_topic": topic.get("display_name"),
        "field": topic.get("field", {}).get("display_name") if topic.get("field") else None,
        "domain": topic.get("domain", {}).get("display_name") if topic.get("domain") else None,
        "referenced_works_count": w.get("referenced_works_count"),
        "abstract": abstract,
    }


def _format_author(a: dict) -> dict:
    """格式化作者信息"""
    return {
        "id": _clean_id(a.get("id", "")),
        "name": a.get("display_name"),
        "orcid": a.get("orcid"),
        "works_count": a.get("works_count"),
        "cited_by_count": a.get("cited_by_count"),
        "h_index": a.get("summary_stats", {}).get("h_index"),
        "affiliations": [i.get("display_name") for i in a.get("affiliations", [])[:5]],
        "topics": [t.get("display_name") for t in a.get("topics", [])[:5]],
    }


def _format_source(s: dict) -> dict:
    """格式化期刊/来源信息"""
    return {
        "id": _clean_id(s.get("id", "")),
        "name": s.get("display_name"),
        "issn": s.get("issn_l"),
        "type": s.get("type"),
        "publisher": s.get("host_organization_name"),
        "works_count": s.get("works_count"),
        "cited_by_count": s.get("cited_by_count"),
        "is_oa": s.get("is_oa"),
        "homepage": s.get("homepage_url"),
    }


def _format_institution(i: dict) -> dict:
    """格式化机构信息"""
    return {
        "id": _clean_id(i.get("id", "")),
        "name": i.get("display_name"),
        "ror": i.get("ror"),
        "type": i.get("type"),
        "country": i.get("country_code"),
        "city": i.get("geo", {}).get("city") if i.get("geo") else None,
        "works_count": i.get("works_count"),
        "cited_by_count": i.get("cited_by_count"),
        "homepage": i.get("homepage_url"),
    }


def _format_topic(t: dict) -> dict:
    """格式化主题信息"""
    return {
        "id": _clean_id(t.get("id", "")),
        "name": t.get("display_name"),
        "description": t.get("description"),
        "works_count": t.get("works_count"),
        "subfield": t.get("subfield", {}).get("display_name") if t.get("subfield") else None,
        "field": t.get("field", {}).get("display_name") if t.get("field") else None,
        "domain": t.get("domain", {}).get("display_name") if t.get("domain") else None,
        "keywords": t.get("keywords", [])[:10],
    }


def _format_funder(f: dict) -> dict:
    """格式化资助机构信息"""
    return {
        "id": _clean_id(f.get("id", "")),
        "name": f.get("display_name"),
        "country": f.get("country_code"),
        "description": f.get("description"),
        "works_count": f.get("works_count"),
        "cited_by_count": f.get("cited_by_count"),
        "grants_count": f.get("grants_count"),
        "homepage": f.get("homepage_url"),
    }


def _format_keyword(k: dict) -> dict:
    """格式化关键词信息"""
    return {
        "id": _clean_id(k.get("id", "")),
        "keyword": k.get("display_name"),
        "works_count": k.get("works_count"),
        "cited_by_count": k.get("cited_by_count"),
    }


def _format_entity_brief(entity: dict, entity_type: str) -> dict:
    """根据类型格式化实体简要信息"""
    if entity_type == "works":
        return _format_work_brief(entity)
    
    base = {
        "id": _clean_id(entity.get("id", "")),
        "name": entity.get("display_name"),
    }
    
    if entity_type == "authors":
        base["works_count"] = entity.get("works_count")
        base["cited_by_count"] = entity.get("cited_by_count")
    elif entity_type == "sources":
        base["type"] = entity.get("type")
        base["works_count"] = entity.get("works_count")
    elif entity_type == "institutions":
        base["type"] = entity.get("type")
        base["country"] = entity.get("country_code")
        base["works_count"] = entity.get("works_count")
    elif entity_type == "topics":
        base["works_count"] = entity.get("works_count")
        base["field"] = entity.get("field", {}).get("display_name") if entity.get("field") else None
    elif entity_type == "publishers":
        base["works_count"] = entity.get("works_count")
    elif entity_type == "funders":
        base["country"] = entity.get("country_code")
        base["works_count"] = entity.get("works_count")
    elif entity_type == "keywords":
        base["keyword"] = entity.get("display_name")
        base["works_count"] = entity.get("works_count")
    elif entity_type in ("continents", "countries"):
        base["code"] = entity.get("country_code") or _clean_id(entity.get("id", "")).split("/")[-1]
        base["works_count"] = entity.get("works_count")
    
    return base


def _format_entity_full(entity: dict, entity_type: str) -> dict:
    """根据类型格式化实体完整信息"""
    formatters = {
        "works": _format_work_full,
        "authors": _format_author,
        "sources": _format_source,
        "institutions": _format_institution,
        "topics": _format_topic,
        "funders": _format_funder,
        "keywords": _format_keyword,
    }
    formatter = formatters.get(entity_type)
    if formatter:
        return formatter(entity)
    
    # 默认格式
    return {
        "id": _clean_id(entity.get("id", "")),
        "name": entity.get("display_name"),
        "works_count": entity.get("works_count"),
        "cited_by_count": entity.get("cited_by_count"),
    }


# ============================================================================
# MCP Tools
# ============================================================================

@mcp.tool(
    name="search_openalex",
    description="简单搜索 OpenAlex 实体。适合基本查询，如按关键词搜索论文、作者或机构。",
    tags={"search", "openalex"}
)
def search_openalex(
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
        limit: 返回数量 (默认15, 最大50)
    
    Returns:
        搜索结果列表
    
    示例:
        搜索 2024 年 AI 论文: search_openalex("artificial intelligence", year_from=2024)
        搜索中国机构: search_openalex("university", entity_type="institutions", country="CN")
        搜索 LLM 关键词: search_openalex("large language model", entity_type="keywords")
    """
    endpoint = ENTITY_ENDPOINTS.get(entity_type, "works")
    
    params = {"search": query, "per-page": min(limit, 50)}
    
    # 构建过滤器
    filters = []
    if entity_type == "works":
        current_year = datetime.datetime.now().year
        if year_from and year_to:
            filters.append(f"publication_year:{year_from}-{year_to}")
        elif year_from:
            filters.append(f"publication_year:{year_from}-{current_year}")
        elif year_to:
            filters.append(f"publication_year:1900-{year_to}")
        
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
    
    try:
        data = _request(endpoint, params)
        results = [_format_entity_brief(e, endpoint) for e in data.get("results", [])]
        return {
            "total_count": data.get("meta", {}).get("count"),
            "entity_type": endpoint,
            "results": results
        }
    except requests.exceptions.HTTPError as e:
        return {"error": f"搜索失败: {str(e)}"}


@mcp.tool(
    name="query_openalex",
    description="高级查询 OpenAlex，支持原生 filter 语法和复杂过滤器组合。适合复杂的组合查询。",
    tags={"query", "openalex", "advanced"}
)
def query_openalex(
    entity_type: SEARCH_ENTITY_TYPES = "works",
    filter: Optional[str] = None,
    search: Optional[str] = None,
    sort: str = "cited_by_count:desc",
    group_by: Optional[str] = None,
    limit: int = 25
) -> dict:
    """
    高级查询 OpenAlex - 支持原生 filter 语法。
    
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
        group_by: 分组聚合字段 (如 publication_year, authorships.countries)
        limit: 返回数量 (默认25, 最大200)
    
    Returns:
        查询结果或分组统计
    
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
        
    复杂查询示例:
        - 2024年中国AI论文: filter="publication_year:2024,authorships.countries:CN", search="artificial intelligence"
        - MIT高引论文: filter="authorships.institutions.id:I63966007,cited_by_count:>100"
        - Nature期刊开放获取: filter="primary_location.source.id:S137773608,is_oa:true"
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
    
    try:
        data = _request(endpoint, params)
        
        # 如果是分组查询
        if group_by and data.get("group_by"):
            return {
                "total_count": data.get("meta", {}).get("count"),
                "entity_type": endpoint,
                "group_by": group_by,
                "groups": data.get("group_by", [])
            }
        
        results = [_format_entity_brief(e, endpoint) for e in data.get("results", [])]
        return {
            "total_count": data.get("meta", {}).get("count"),
            "entity_type": endpoint,
            "results": results
        }
    except requests.exceptions.HTTPError as e:
        return {"error": f"查询失败: {str(e)}"}


@mcp.tool(
    name="fetch_openalex",
    description="获取 OpenAlex 实体的详细信息。支持 ID、DOI、ORCID 等标识符。",
    tags={"fetch", "openalex"}
)
def fetch_openalex(
    identifier: str,
    entity_type: FETCH_ENTITY_TYPES = "work",
    include_related: bool = False
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
        include_related: 是否包含相关实体 (如作者的代表作、机构的知名作者)
    
    Returns:
        实体详细信息，包含 keywords、funders、awards、SDGs 等
    
    示例:
        获取论文: fetch_openalex("10.1038/s41586-021-03819-2")
        获取作者: fetch_openalex("A5012301204", entity_type="author", include_related=True)
        获取机构: fetch_openalex("I63966007", entity_type="institution")
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
    
    try:
        data = _request(f"{endpoint}/{id_clean}")
        result = _format_entity_full(data, endpoint)
        
        # 获取相关实体
        if include_related:
            if entity_type == "author":
                works = _request("works", {
                    "filter": f"author.id:{data['id']}",
                    "sort": "cited_by_count:desc",
                    "per-page": 5,
                })
                result["top_works"] = [_format_work_brief(w) for w in works.get("results", [])]
            
            elif entity_type == "source":
                works = _request("works", {
                    "filter": f"primary_location.source.id:{data['id']}",
                    "sort": "cited_by_count:desc",
                    "per-page": 5,
                })
                result["top_works"] = [_format_work_brief(w) for w in works.get("results", [])]
            
            elif entity_type == "institution":
                authors = _request("authors", {
                    "filter": f"affiliations.institution.id:{data['id']}",
                    "sort": "cited_by_count:desc",
                    "per-page": 5,
                })
                result["top_authors"] = [_format_author(a) for a in authors.get("results", [])]
            
            elif entity_type == "funder":
                works = _request("works", {
                    "filter": f"funders.id:{data['id']}",
                    "sort": "cited_by_count:desc",
                    "per-page": 5,
                })
                result["top_works"] = [_format_work_brief(w) for w in works.get("results", [])]
        
        return result
        
    except requests.exceptions.HTTPError as e:
        return {"error": f"获取失败: {str(e)}"}


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
