"""
OpenAlex MCP Server - 使用 FastMCP 构建的学术论文搜索工具

提供给 AI Agent (如 Cursor, Claude Desktop) 使用的 MCP 工具，
用于搜索和获取 OpenAlex 上的学术论文信息。

最佳实践 (2025.12):
- 工具数量精简: 使用 search + fetch 模式（参考 ChatGPT Deep Research）
- 清晰的工具职责: 每个工具有明确单一的用途
- 类型提示完整: 所有函数都有完整的类型注解

支持的实体类型:
- works: 论文、书籍、数据集、学位论文
- authors: 作者
- sources: 期刊、会议、预印本服务器
- institutions: 大学、研究机构
- topics: 主题分类
- publishers: 出版商
- funders: 资助机构
- continents/countries: 地理位置

运行方式:
    1. stdio 模式 (用于 Cursor/Claude Desktop): python openalex_mcp_server.py
    2. http 模式 (用于调试): python openalex_mcp_server.py --http
    3. 使用 fastmcp CLI: fastmcp run openalex_mcp_server.py
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
    OpenAlex 学术论文搜索工具。提供两个核心工具：
    
    1. search_openalex - 搜索各类学术实体
    2. fetch_openalex - 获取具体实体的详细信息
    
    支持的实体类型:
    - works: 论文、书籍、数据集
    - authors: 作者
    - sources: 期刊、会议
    - institutions: 大学、研究机构
    - topics: 主题分类
    - publishers: 出版商
    - funders: 资助机构
    - continents/countries: 地理位置
    
    典型工作流:
    1. 使用 search_openalex 搜索，获取 ID 列表
    2. 使用 fetch_openalex 获取感兴趣项目的详细信息
    
    数据来源: OpenAlex (https://openalex.org) - 包含 2.5 亿+ 学术论文
    """
)

# OpenAlex API 基础URL
BASE_URL = "https://api.openalex.org"

# 添加邮箱以提高速率限制 (1次/秒 -> 10次/秒)
# 通过环境变量 OPENALEX_EMAIL 配置，可在 mcp.json 的 env 字段中设置
OPENALEX_EMAIL = os.environ.get("OPENALEX_EMAIL", "openalex-mcp@example.com")
DEFAULT_PARAMS = {"mailto": OPENALEX_EMAIL}

# 支持的实体类型映射
ENTITY_TYPES = {
    # 搜索时使用的实体类型（复数形式）
    "works": "works",
    "authors": "authors", 
    "sources": "sources",
    "institutions": "institutions",
    "topics": "topics",
    "publishers": "publishers",
    "funders": "funders",
    "continents": "continents",
    "countries": "countries",
}

# fetch 时使用的实体类型（单数形式映射到复数）
ENTITY_TYPE_SINGULAR = {
    "work": "works",
    "author": "authors",
    "source": "sources",
    "institution": "institutions",
    "topic": "topics",
    "publisher": "publishers",
    "funder": "funders",
    "continent": "continents",
    "country": "countries",
}


def _make_request(endpoint: str, params: dict | None = None) -> dict:
    """发送 API 请求的辅助函数"""
    url = f"{BASE_URL}/{endpoint}"
    all_params = {**DEFAULT_PARAMS, **(params or {})}
    response = requests.get(url, params=all_params, timeout=30)
    response.raise_for_status()
    return response.json()


def _format_paper_brief(paper: dict) -> dict:
    """格式化论文简要信息"""
    authorships = paper.get("authorships", [])
    first_author = authorships[0].get("author", {}).get("display_name") if authorships else "Unknown"
    
    primary_location = paper.get("primary_location", {}) or {}
    source = primary_location.get("source", {}) or {}
    
    return {
        "id": paper.get("id", "").replace("https://openalex.org/", ""),
        "title": paper.get("title"),
        "doi": paper.get("doi"),
        "publication_date": paper.get("publication_date"),
        "cited_by_count": paper.get("cited_by_count"),
        "first_author": first_author,
        "author_count": len(authorships),
        "journal": source.get("display_name"),
        "is_oa": paper.get("open_access", {}).get("is_oa"),
    }


def _format_paper_full(paper: dict) -> dict:
    """格式化论文完整信息"""
    # 提取作者信息
    authors = []
    for authorship in paper.get("authorships", []):
        authors.append({
            "name": authorship.get("author", {}).get("display_name"),
            "orcid": authorship.get("author", {}).get("orcid"),
            "position": authorship.get("author_position"),
            "institutions": [
                inst.get("display_name") 
                for inst in authorship.get("institutions", [])
            ],
            "countries": authorship.get("countries", [])
        })
    
    # 提取期刊信息
    primary_location = paper.get("primary_location", {}) or {}
    source = primary_location.get("source", {}) or {}
    
    # 提取主题信息
    primary_topic = paper.get("primary_topic", {}) or {}
    
    # 提取关键词
    keywords = [kw.get("display_name") for kw in paper.get("keywords", [])[:8]]
    
    return {
        "id": paper.get("id", "").replace("https://openalex.org/", ""),
        "doi": paper.get("doi"),
        "title": paper.get("title"),
        "publication_date": paper.get("publication_date"),
        "publication_year": paper.get("publication_year"),
        "language": paper.get("language"),
        "type": paper.get("type"),
        "cited_by_count": paper.get("cited_by_count"),
        "fwci": paper.get("fwci"),
        "is_top_1_percent": paper.get("citation_normalized_percentile", {}).get("is_in_top_1_percent"),
        "journal": source.get("display_name"),
        "publisher": source.get("host_organization_name"),
        "volume": paper.get("biblio", {}).get("volume"),
        "issue": paper.get("biblio", {}).get("issue"),
        "pages": f"{paper.get('biblio', {}).get('first_page', '')}-{paper.get('biblio', {}).get('last_page', '')}".strip("-"),
        "authors": authors,
        "is_oa": paper.get("open_access", {}).get("is_oa"),
        "oa_status": paper.get("open_access", {}).get("oa_status"),
        "pdf_url": primary_location.get("pdf_url"),
        "primary_topic": primary_topic.get("display_name"),
        "field": primary_topic.get("field", {}).get("display_name"),
        "domain": primary_topic.get("domain", {}).get("display_name"),
        "keywords": keywords,
        "referenced_works_count": paper.get("referenced_works_count"),
        "abstract": _reconstruct_abstract(paper.get("abstract_inverted_index")),
    }


def _reconstruct_abstract(inverted_index: dict | None) -> str | None:
    """从倒排索引重建摘要文本"""
    if not inverted_index:
        return None
    
    # 重建摘要
    words = []
    for word, positions in inverted_index.items():
        for pos in positions:
            words.append((pos, word))
    
    words.sort(key=lambda x: x[0])
    return " ".join(word for _, word in words)


def _format_author(author: dict) -> dict:
    """格式化作者信息"""
    return {
        "id": author.get("id", "").replace("https://openalex.org/", ""),
        "name": author.get("display_name"),
        "orcid": author.get("orcid"),
        "works_count": author.get("works_count"),
        "cited_by_count": author.get("cited_by_count"),
        "h_index": author.get("summary_stats", {}).get("h_index"),
        "affiliations": [
            inst.get("display_name") 
            for inst in author.get("affiliations", [])[:3]
        ],
        "topics": [
            topic.get("display_name")
            for topic in author.get("topics", [])[:5]
        ],
    }


def _format_source(source: dict) -> dict:
    """格式化期刊/来源信息"""
    return {
        "id": source.get("id", "").replace("https://openalex.org/", ""),
        "name": source.get("display_name"),
        "issn": source.get("issn_l"),
        "publisher": source.get("host_organization_name"),
        "type": source.get("type"),
        "works_count": source.get("works_count"),
        "cited_by_count": source.get("cited_by_count"),
        "is_oa": source.get("is_oa"),
        "homepage_url": source.get("homepage_url"),
    }


def _format_institution(inst: dict) -> dict:
    """格式化机构信息"""
    return {
        "id": inst.get("id", "").replace("https://openalex.org/", ""),
        "name": inst.get("display_name"),
        "ror": inst.get("ror"),
        "type": inst.get("type"),
        "country": inst.get("country_code"),
        "city": inst.get("geo", {}).get("city"),
        "works_count": inst.get("works_count"),
        "cited_by_count": inst.get("cited_by_count"),
        "homepage_url": inst.get("homepage_url"),
        "image_url": inst.get("image_url"),
    }


def _format_topic(topic: dict) -> dict:
    """格式化主题信息"""
    return {
        "id": topic.get("id", "").replace("https://openalex.org/", ""),
        "name": topic.get("display_name"),
        "description": topic.get("description"),
        "works_count": topic.get("works_count"),
        "cited_by_count": topic.get("cited_by_count"),
        "subfield": topic.get("subfield", {}).get("display_name"),
        "field": topic.get("field", {}).get("display_name"),
        "domain": topic.get("domain", {}).get("display_name"),
        "keywords": topic.get("keywords", [])[:10],
    }


def _format_publisher(publisher: dict) -> dict:
    """格式化出版商信息"""
    return {
        "id": publisher.get("id", "").replace("https://openalex.org/", ""),
        "name": publisher.get("display_name"),
        "alternate_titles": publisher.get("alternate_titles", []),
        "country_codes": publisher.get("country_codes", []),
        "works_count": publisher.get("works_count"),
        "cited_by_count": publisher.get("cited_by_count"),
        "sources_count": publisher.get("sources_api_url", "").split("per-page=")[0] if publisher.get("sources_api_url") else None,
        "homepage_url": publisher.get("homepage_url"),
    }


def _format_funder(funder: dict) -> dict:
    """格式化资助机构信息"""
    return {
        "id": funder.get("id", "").replace("https://openalex.org/", ""),
        "name": funder.get("display_name"),
        "alternate_titles": funder.get("alternate_titles", []),
        "country_code": funder.get("country_code"),
        "description": funder.get("description"),
        "works_count": funder.get("works_count"),
        "cited_by_count": funder.get("cited_by_count"),
        "grants_count": funder.get("grants_count"),
        "homepage_url": funder.get("homepage_url"),
    }


def _format_geo(geo: dict) -> dict:
    """格式化地理位置信息"""
    return {
        "id": geo.get("id", "").replace("https://openalex.org/", ""),
        "name": geo.get("display_name"),
        "code": geo.get("country_code") or geo.get("id", "").split("/")[-1],
        "works_count": geo.get("works_count"),
        "cited_by_count": geo.get("cited_by_count"),
    }


def _format_entity_brief(entity: dict, entity_type: str) -> dict:
    """根据实体类型格式化简要信息"""
    base = {
        "id": entity.get("id", "").replace("https://openalex.org/", ""),
        "name": entity.get("display_name"),
    }
    
    if entity_type == "works":
        return _format_paper_brief(entity)
    elif entity_type == "authors":
        base.update({
            "works_count": entity.get("works_count"),
            "cited_by_count": entity.get("cited_by_count"),
        })
    elif entity_type == "sources":
        base.update({
            "type": entity.get("type"),
            "works_count": entity.get("works_count"),
            "publisher": entity.get("host_organization_name"),
        })
    elif entity_type == "institutions":
        base.update({
            "type": entity.get("type"),
            "country": entity.get("country_code"),
            "works_count": entity.get("works_count"),
        })
    elif entity_type == "topics":
        base.update({
            "works_count": entity.get("works_count"),
            "field": entity.get("field", {}).get("display_name") if entity.get("field") else None,
        })
    elif entity_type == "publishers":
        base.update({
            "works_count": entity.get("works_count"),
            "country_codes": entity.get("country_codes", []),
        })
    elif entity_type == "funders":
        base.update({
            "works_count": entity.get("works_count"),
            "country_code": entity.get("country_code"),
        })
    elif entity_type in ("continents", "countries"):
        base.update({
            "code": entity.get("country_code") or entity.get("id", "").split("/")[-1],
            "works_count": entity.get("works_count"),
        })
    
    return base


def _format_entity_full(entity: dict, entity_type: str) -> dict:
    """根据实体类型格式化完整信息"""
    if entity_type == "works":
        return _format_paper_full(entity)
    elif entity_type == "authors":
        return _format_author(entity)
    elif entity_type == "sources":
        return _format_source(entity)
    elif entity_type == "institutions":
        return _format_institution(entity)
    elif entity_type == "topics":
        return _format_topic(entity)
    elif entity_type == "publishers":
        return _format_publisher(entity)
    elif entity_type == "funders":
        return _format_funder(entity)
    elif entity_type in ("continents", "countries"):
        return _format_geo(entity)
    else:
        return entity


# 定义搜索实体类型
SearchEntityType = Literal["works", "authors", "sources", "institutions", "topics", "publishers", "funders", "continents", "countries"]

# 定义获取实体类型
FetchEntityType = Literal["work", "author", "source", "institution", "topic", "publisher", "funder", "continent", "country"]


@mcp.tool(
    name="search_openalex",
    description="搜索学术实体：论文、作者、期刊、机构、主题、出版商、资助机构等。返回匹配结果的 ID 列表和摘要信息。",
    tags={"search", "openalex", "academic"}
)
def search_openalex(
    query: str,
    entity_type: SearchEntityType = "works",
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    country: Optional[str] = None,
    institution: Optional[str] = None,
    open_access: Optional[bool] = None,
    sort_by: Literal["cited_by_count", "publication_date", "relevance", "works_count"] = "cited_by_count",
    limit: int = 10
) -> dict:
    """
    在 OpenAlex 中搜索学术实体。
    
    Args:
        query: 搜索关键词，例如 "machine learning" 或 "Harvard University"
        entity_type: 实体类型，可选值:
            - "works": 论文、书籍、数据集（默认）
            - "authors": 作者
            - "sources": 期刊、会议、预印本服务器
            - "institutions": 大学、研究机构
            - "topics": 主题分类
            - "publishers": 出版商
            - "funders": 资助机构
            - "continents": 大洲
            - "countries": 国家
        year_from: 起始年份过滤（对 works 有效），例如 2020
        year_to: 结束年份过滤（对 works 有效），例如 2025
        country: 国家代码过滤（对 works/authors/institutions 有效），例如 "CN", "US"
        institution: 机构名称或ID过滤（对 works/authors 有效）
        open_access: 是否开放获取（仅对 works 有效）
        sort_by: 排序方式:
            - "cited_by_count": 按引用数排序（默认）
            - "publication_date": 按发表日期排序（仅 works）
            - "relevance": 按相关度排序
            - "works_count": 按论文数排序（适用于 authors/institutions/topics 等）
        limit: 返回结果数量，默认10，最大50
    
    Returns:
        包含搜索结果的字典:
        - total_count: 总匹配数
        - results: 结果列表，每项包含 id 和基本信息
        
    使用示例:
        搜索论文: search_openalex("deep learning", entity_type="works", year_from=2024)
        搜索作者: search_openalex("Yann LeCun", entity_type="authors")
        搜索机构: search_openalex("MIT", entity_type="institutions")
        搜索期刊: search_openalex("Nature", entity_type="sources")
        搜索主题: search_openalex("artificial intelligence", entity_type="topics")
        搜索出版商: search_openalex("Elsevier", entity_type="publishers")
        搜索资助机构: search_openalex("NSF", entity_type="funders")
        搜索国家: search_openalex("China", entity_type="countries")
    """
    # 验证实体类型
    if entity_type not in ENTITY_TYPES:
        return {"error": f"不支持的实体类型: {entity_type}。支持的类型: {list(ENTITY_TYPES.keys())}"}
    
    endpoint = ENTITY_TYPES[entity_type]
    
    params = {
        "search": query,
        "per-page": min(limit, 50),
    }
    
    # 构建过滤条件
    filters = []
    current_year = datetime.datetime.now().year
    
    # 年份过滤（仅对 works 有效）
    if entity_type == "works":
        if year_from and year_to:
            filters.append(f"publication_year:{year_from}-{year_to}")
        elif year_from:
            filters.append(f"publication_year:{year_from}-{current_year}")
        elif year_to:
            filters.append(f"publication_year:1900-{year_to}")
        
        # 开放获取过滤
        if open_access is not None:
            filters.append(f"is_oa:{str(open_access).lower()}")
        
        # 国家过滤
        if country:
            filters.append(f"authorships.countries:{country.upper()}")
        
        # 机构过滤
        if institution:
            filters.append(f"authorships.institutions.display_name.search:{institution}")
    
    # 作者的国家/机构过滤
    elif entity_type == "authors":
        if country:
            filters.append(f"affiliations.institution.country_code:{country.upper()}")
        if institution:
            filters.append(f"affiliations.institution.display_name.search:{institution}")
    
    # 机构的国家过滤
    elif entity_type == "institutions":
        if country:
            filters.append(f"country_code:{country.upper()}")
    
    if filters:
        params["filter"] = ",".join(filters)
    
    # 排序
    if sort_by == "cited_by_count":
        params["sort"] = "cited_by_count:desc"
    elif sort_by == "publication_date" and entity_type == "works":
        params["sort"] = "publication_date:desc"
    elif sort_by == "works_count" and entity_type != "works":
        params["sort"] = "works_count:desc"
    # relevance 是默认排序
    
    try:
        data = _make_request(endpoint, params)
        
        results = [_format_entity_brief(item, entity_type) for item in data.get("results", [])]
        
        return {
            "total_count": data.get("meta", {}).get("count"),
            "entity_type": entity_type,
            "results": results
        }
    except requests.exceptions.HTTPError as e:
        return {"error": f"搜索失败: {str(e)}"}


@mcp.tool(
    name="fetch_openalex",
    description="获取论文、作者、期刊、机构等实体的详细信息。支持通过 OpenAlex ID 或 DOI 查询。",
    tags={"fetch", "openalex", "academic"}
)
def fetch_openalex(
    identifier: str,
    entity_type: FetchEntityType = "work",
    include_related: bool = False
) -> dict:
    """
    获取 OpenAlex 实体的详细信息。
    
    Args:
        identifier: 实体标识符，可以是:
            - OpenAlex ID: 如 "W4391403992", "A5012301204", "S23254222", "I27837315"
            - DOI: 如 "10.1080/00207543.2024.2309309" (仅对论文有效)
            - ORCID: 如 "0000-0001-6187-6610" (仅对作者有效)
            - ROR: 如 "https://ror.org/042nb2s44" (仅对机构有效)
            - 完整 URL: 如 "https://openalex.org/W4391403992"
        entity_type: 实体类型，可选值:
            - "work": 论文（默认）
            - "author": 作者
            - "source": 期刊
            - "institution": 机构
            - "topic": 主题
            - "publisher": 出版商
            - "funder": 资助机构
            - "continent": 大洲
            - "country": 国家
        include_related: 是否包含相关信息（如作者的代表作，机构的知名作者等），默认 False
    
    Returns:
        实体的详细信息
        
    使用示例:
        获取论文: fetch_openalex("10.1038/s41586-021-03819-2")
        获取作者: fetch_openalex("A5012301204", entity_type="author", include_related=True)
        获取期刊: fetch_openalex("S23254222", entity_type="source")
        获取机构: fetch_openalex("I27837315", entity_type="institution")
        获取主题: fetch_openalex("T10000", entity_type="topic")
    """
    # 验证实体类型
    if entity_type not in ENTITY_TYPE_SINGULAR:
        return {"error": f"不支持的实体类型: {entity_type}。支持的类型: {list(ENTITY_TYPE_SINGULAR.keys())}"}
    
    endpoint_type = ENTITY_TYPE_SINGULAR[entity_type]
    
    # 规范化标识符
    id_clean = identifier.strip()
    
    # 移除 URL 前缀
    if id_clean.startswith("https://openalex.org/"):
        id_clean = id_clean.replace("https://openalex.org/", "")
    
    # 对于 DOI，添加前缀
    if entity_type == "work" and (id_clean.startswith("10.") or "doi.org" in id_clean):
        if not id_clean.startswith("https://doi.org/"):
            if id_clean.startswith("doi.org/"):
                id_clean = f"https://{id_clean}"
            else:
                id_clean = f"https://doi.org/{id_clean}"
    
    # 对于 ORCID
    if entity_type == "author" and id_clean.startswith("0000-"):
        id_clean = f"https://orcid.org/{id_clean}"
    
    try:
        data = _make_request(f"{endpoint_type}/{id_clean}")
        result = _format_entity_full(data, endpoint_type)
        
        # 获取相关信息
        if include_related:
            if entity_type == "author":
                # 获取作者的代表作
                works_data = _make_request("works", {
                    "filter": f"author.id:{data['id']}",
                    "sort": "cited_by_count:desc",
                    "per-page": 5,
                    "select": "id,title,doi,publication_date,cited_by_count,primary_location"
                })
                result["top_works"] = [
                    {
                        "id": p.get("id", "").replace("https://openalex.org/", ""),
                        "title": p.get("title"),
                        "doi": p.get("doi"),
                        "cited_by_count": p.get("cited_by_count"),
                        "journal": (p.get("primary_location", {}) or {}).get("source", {}).get("display_name") if p.get("primary_location") else None,
                    }
                    for p in works_data.get("results", [])
                ]
            elif entity_type == "source":
                # 获取期刊的高引论文
                works_data = _make_request("works", {
                    "filter": f"primary_location.source.id:{data['id']}",
                    "sort": "cited_by_count:desc",
                    "per-page": 5,
                    "select": "id,title,doi,publication_date,cited_by_count,authorships"
                })
                result["top_works"] = [
                    {
                        "id": p.get("id", "").replace("https://openalex.org/", ""),
                        "title": p.get("title"),
                        "cited_by_count": p.get("cited_by_count"),
                        "first_author": p.get("authorships", [{}])[0].get("author", {}).get("display_name") if p.get("authorships") else None,
                    }
                    for p in works_data.get("results", [])
                ]
            elif entity_type == "institution":
                # 获取机构的知名作者
                authors_data = _make_request("authors", {
                    "filter": f"affiliations.institution.id:{data['id']}",
                    "sort": "cited_by_count:desc",
                    "per-page": 5,
                })
                result["top_authors"] = [
                    {
                        "id": a.get("id", "").replace("https://openalex.org/", ""),
                        "name": a.get("display_name"),
                        "works_count": a.get("works_count"),
                        "cited_by_count": a.get("cited_by_count"),
                    }
                    for a in authors_data.get("results", [])
                ]
            elif entity_type == "topic":
                # 获取主题下的高引论文
                works_data = _make_request("works", {
                    "filter": f"primary_topic.id:{data['id']}",
                    "sort": "cited_by_count:desc",
                    "per-page": 5,
                    "select": "id,title,doi,cited_by_count"
                })
                result["top_works"] = [
                    {
                        "id": p.get("id", "").replace("https://openalex.org/", ""),
                        "title": p.get("title"),
                        "cited_by_count": p.get("cited_by_count"),
                    }
                    for p in works_data.get("results", [])
                ]
        
        return result
        
    except requests.exceptions.HTTPError as e:
        return {"error": f"获取失败: {str(e)}"}


def main():
    """入口点函数，用于 uvx 和 pip install 后直接运行"""
    import sys
    
    # 检查是否使用 HTTP 模式
    if "--http" in sys.argv:
        print("Starting OpenAlex MCP Server in HTTP mode on port 8000...")
        mcp.run(transport="http", port=8000)
    else:
        # 默认使用 stdio 模式（用于 Cursor/Claude Desktop）
        mcp.run()


if __name__ == "__main__":
    main()
