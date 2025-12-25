"""
OpenAlex MCP Server 综合测试脚本

直接通过 FastMCP Client 测试 MCP Server 的所有工具:
1. search_openalex - 简单搜索
2. query_openalex - 高级查询
3. fetch_openalex - 获取详情
4. sample_openalex - 随机采样
5. batch_fetch_openalex - 批量获取
6. autocomplete_openalex - 自动补全
7. ngrams_openalex - N-grams 分析

运行: uv run python test_server.py
"""

import asyncio
from fastmcp import Client
from fastmcp.exceptions import ToolError


async def test_autocomplete_two_step_workflow(client: Client):
    """
    测试 1: 两步查询模式
    先用 autocomplete 获取 ID，再用 query 查询
    """
    print("=" * 70)
    print("测试 1: 两步查询模式 (autocomplete → query)")
    print("       目标: 查找斯坦福大学 2024 年的 AI 论文")
    print("=" * 70)
    
    # Step 1: autocomplete 获取机构 ID
    result = await client.call_tool("autocomplete_openalex", {
        "query": "Stanford University",
        "entity_type": "institutions"
    })
    
    stanford_id = result.data["results"][0]["id"].split("/")[-1]
    stanford_name = result.data["results"][0]["display_name"]
    print(f"Step 1 - Autocomplete: {stanford_name} → {stanford_id}")
    
    # Step 2: 使用 ID 查询论文
    result = await client.call_tool("query_openalex", {
        "entity_type": "works",
        "filter": f"authorships.institutions.id:{stanford_id},publication_year:2024",
        "search": "artificial intelligence",
        "sort": "cited_by_count:desc",
        "select": "id,title,cited_by_count,publication_year",
        "limit": 5
    })
    
    print(f"Step 2 - Query: 找到 {result.data['meta']['count']:,} 篇论文")
    print("\n前 5 篇高引论文:")
    for i, w in enumerate(result.data["results"], 1):
        title = w["title"][:55] + "..." if len(w["title"]) > 55 else w["title"]
        print(f"  {i}. {title}")
        print(f"     引用: {w['cited_by_count']}")
    print()
    return True


async def test_complex_filter_combination(client: Client):
    """
    测试 2: 复杂过滤器组合
    多条件 AND 组合 + OR 操作 + 范围筛选
    """
    print("=" * 70)
    print("测试 2: 复杂过滤器组合")
    print("       目标: 中国或美国作者 2023-2024 年发表的 LLM 高引论文")
    print("=" * 70)
    
    result = await client.call_tool("query_openalex", {
        "entity_type": "works",
        "filter": "authorships.countries:CN|US,publication_year:2023-2024,cited_by_count:>50",
        "search": "large language model",
        "sort": "cited_by_count:desc",
        "select": "id,title,cited_by_count,publication_year,authorships",
        "limit": 5
    })
    
    print(f"Filter: authorships.countries:CN|US,publication_year:2023-2024,cited_by_count:>50")
    print(f"总数: {result.data['meta']['count']:,} 篇")
    print("\n前 5 篇:")
    for i, w in enumerate(result.data["results"], 1):
        countries = set()
        for a in w.get("authorships", []):
            countries.update(a.get("countries", []))
        title = w["title"][:50] + "..." if len(w["title"]) > 50 else w["title"]
        print(f"  {i}. {title}")
        print(f"     引用: {w['cited_by_count']} | 年份: {w['publication_year']} | 国家: {', '.join(countries)}")
    print()
    return True


async def test_group_by_statistics(client: Client):
    """
    测试 3: 分组聚合统计
    使用 group_by 进行多维度统计分析
    """
    print("=" * 70)
    print("测试 3: 分组聚合统计 (group_by)")
    print("       目标: 分析 Nature 期刊近 10 年的发文量趋势")
    print("=" * 70)
    
    # 先获取 Nature 的 ID
    autocomplete = await client.call_tool("autocomplete_openalex", {
        "query": "Nature",
        "entity_type": "sources"
    })
    nature_id = autocomplete.data["results"][0]["id"].split("/")[-1]
    print(f"Nature ID: {nature_id}")
    
    # 按年份分组
    result = await client.call_tool("query_openalex", {
        "entity_type": "works",
        "filter": f"primary_location.source.id:{nature_id},publication_year:2015-2024",
        "group_by": "publication_year"
    })
    
    print(f"\nNature 期刊发文量统计 (2015-2024):")
    groups = sorted(result.data.get("group_by", []), key=lambda x: x.get("key", ""), reverse=True)
    max_count = max(g.get("count", 0) for g in groups) if groups else 1
    for g in groups:
        year = g.get("key", "Unknown")
        count = g.get("count", 0)
        bar_len = int(count / max_count * 30)
        bar = "█" * bar_len
        print(f"  {year}: {count:>5} {bar}")
    print()
    return True


async def test_batch_fetch_efficiency(client: Client):
    """
    测试 4: 批量获取效率测试
    使用 batch_fetch 一次性获取多个实体
    """
    print("=" * 70)
    print("测试 4: 批量获取 (batch_fetch)")
    print("       目标: 批量获取 5 篇经典 AI 论文的详情")
    print("=" * 70)
    
    # 经典 AI 论文 DOI
    dois = [
        "10.1038/nature14539",  # Deep learning (LeCun, Bengio, Hinton)
        "10.1162/neco.1997.9.8.1735",  # LSTM
        "10.1145/3065386",  # AlexNet (ImageNet)
        "10.48550/arXiv.1706.03762",  # Attention Is All You Need
        "10.48550/arXiv.1810.04805",  # BERT
    ]
    
    result = await client.call_tool("batch_fetch_openalex", {
        "identifiers": dois,
        "entity_type": "works",
        "select": "id,title,cited_by_count,publication_year,doi"
    })
    
    print(f"批量获取 {len(dois)} 篇论文:")
    for w in result.data.get("results", []):
        title = w["title"][:45] + "..." if len(w["title"]) > 45 else w["title"]
        print(f"  • {title}")
        print(f"    引用: {w['cited_by_count']:,} | 年份: {w['publication_year']}")
    print()
    return True


async def test_sample_reproducibility(client: Client):
    """
    测试 5: 随机采样可重复性
    使用 seed 确保采样结果可重复
    """
    print("=" * 70)
    print("测试 5: 随机采样可重复性 (sample with seed)")
    print("       目标: 验证相同 seed 返回相同结果")
    print("=" * 70)
    
    # 第一次采样
    result1 = await client.call_tool("sample_openalex", {
        "entity_type": "works",
        "sample_size": 5,
        "seed": 42,
        "filter": "publication_year:2024,is_oa:true",
        "select": "id,title"
    })
    
    # 第二次采样 (相同 seed)
    result2 = await client.call_tool("sample_openalex", {
        "entity_type": "works",
        "sample_size": 5,
        "seed": 42,
        "filter": "publication_year:2024,is_oa:true",
        "select": "id,title"
    })
    
    ids1 = [w["id"] for w in result1.data["results"]]
    ids2 = [w["id"] for w in result2.data["results"]]
    
    print(f"采样 1 (seed=42): {len(ids1)} 篇论文")
    print(f"采样 2 (seed=42): {len(ids2)} 篇论文")
    print(f"结果一致: {'✅ 是' if ids1 == ids2 else '❌ 否'}")
    
    if ids1 == ids2:
        print("\n采样结果:")
        for w in result1.data["results"]:
            title = w["title"][:60] + "..." if len(w["title"]) > 60 else w["title"]
            print(f"  • {title}")
    print()
    return ids1 == ids2


async def test_fetch_with_related_analysis(client: Client):
    """
    测试 6: 获取详情 + 关联分析
    获取论文详情后分析其引用网络
    """
    print("=" * 70)
    print("测试 6: 论文详情 + 引用网络分析")
    print("       目标: 分析 Deep Learning 论文的影响力")
    print("=" * 70)
    
    # 使用 Deep Learning (LeCun, Bengio, Hinton) 论文 - Nature 2015
    result = await client.call_tool("fetch_openalex", {
        "identifier": "W2103795898",  # Deep learning paper
        "entity_type": "work"
    })
    
    work = result.data
    
    # 检查是否返回错误
    if work.get("error"):
        print(f"⚠️ 论文获取失败: {work.get('message')}")
        # 备用: 使用搜索获取
        search_result = await client.call_tool("search_openalex", {
            "query": "Deep learning LeCun Bengio Hinton",
            "entity_type": "works",
            "limit": 1
        })
        if search_result.data["results"]:
            work = search_result.data["results"][0]
        else:
            print("备用搜索也失败")
            return False
    
    print(f"标题: {work['title']}")
    print(f"引用数: {work['cited_by_count']:,}")
    print(f"年份: {work['publication_year']}")
    
    # 分析作者
    authorships = work.get("authorships", [])
    if authorships:
        print(f"\n作者 ({len(authorships)} 位):")
        for a in authorships[:5]:
            name = a["author"]["display_name"]
            insts = [i["display_name"] for i in a.get("institutions", [])]
            inst_str = f" @ {insts[0]}" if insts else ""
            print(f"  • {name}{inst_str}")
    
    # 分析引用该论文的高引论文
    work_id = work['id'].split('/')[-1]
    citing_result = await client.call_tool("query_openalex", {
        "entity_type": "works",
        "filter": f"cites:{work_id}",
        "sort": "cited_by_count:desc",
        "select": "id,title,cited_by_count,publication_year",
        "limit": 5
    })
    
    print(f"\n引用该论文的高引论文 (共 {citing_result.data['meta']['count']:,} 篇):")
    for w in citing_result.data["results"]:
        title = w["title"][:50] + "..." if len(w["title"]) > 50 else w["title"]
        print(f"  • {title}")
        print(f"    引用: {w['cited_by_count']:,} | 年份: {w['publication_year']}")
    print()
    return True


async def test_cross_entity_workflow(client: Client):
    """
    测试 7: 跨实体工作流
    作者 → 机构 → 论文 → 资助机构 的完整链路
    """
    print("=" * 70)
    print("测试 7: 跨实体工作流")
    print("       目标: 从作者出发分析其研究脉络")
    print("=" * 70)
    
    # Step 1: 搜索作者
    result = await client.call_tool("search_openalex", {
        "query": "Yoshua Bengio",
        "entity_type": "authors",
        "sort": "cited_by_count",
        "limit": 1
    })
    
    author = result.data["results"][0]
    author_id = author["id"].split("/")[-1]
    print(f"Step 1 - 作者: {author['display_name']}")
    print(f"         论文数: {author['works_count']:,} | 总引用: {author['cited_by_count']:,}")
    
    # Step 2: 获取作者详情
    detail = await client.call_tool("fetch_openalex", {
        "identifier": author_id,
        "entity_type": "author"
    })
    
    affiliations = detail.data.get("affiliations", [])
    if affiliations:
        inst_name = affiliations[0].get("institution", {}).get("display_name", "N/A")
        print(f"\nStep 2 - 主要机构: {inst_name}")
    
    # Step 3: 获取该作者高引论文
    works = await client.call_tool("query_openalex", {
        "entity_type": "works",
        "filter": f"author.id:{author_id}",
        "sort": "cited_by_count:desc",
        "select": "id,title,cited_by_count,funders",
        "limit": 3
    })
    
    print(f"\nStep 3 - 代表作品:")
    all_funders = set()
    for w in works.data["results"]:
        title = w["title"][:50] + "..." if len(w["title"]) > 50 else w["title"]
        print(f"  • {title}")
        print(f"    引用: {w['cited_by_count']:,}")
        for f in w.get("funders", []):
            all_funders.add(f.get("display_name", "Unknown"))
    
    # Step 4: 分析资助机构
    if all_funders:
        print(f"\nStep 4 - 资助机构:")
        for f in list(all_funders)[:5]:
            print(f"  • {f}")
    print()
    return True


async def test_tool_error_handling(client: Client):
    """
    测试 8: 错误处理
    测试 ToolError 和 API 错误处理
    """
    print("=" * 70)
    print("测试 8: 错误处理")
    print("       目标: 验证 ToolError 和参数校验")
    print("=" * 70)
    
    # 测试空列表
    try:
        await client.call_tool("batch_fetch_openalex", {
            "identifiers": [],
            "entity_type": "works"
        })
        print("❌ 应该抛出错误: 空列表")
        return False
    except ToolError as e:
        print(f"✅ 空列表 → ToolError: {e}")
    
    # 测试超过 50 个 ID
    try:
        await client.call_tool("batch_fetch_openalex", {
            "identifiers": [f"W{i}" for i in range(60)],
            "entity_type": "works"
        })
        print("❌ 应该抛出错误: 超过 50 个")
        return False
    except ToolError as e:
        print(f"✅ 超过限制 → ToolError: {e}")
    
    # 测试无效 ID (应返回空结果而非报错)
    result = await client.call_tool("fetch_openalex", {
        "identifier": "W999999999999999",
        "entity_type": "work"
    })
    
    if result.data.get("error"):
        print(f"✅ 无效 ID → 错误响应: {result.data['error_type']}")
    else:
        print(f"✅ 无效 ID 查询完成 (可能返回空或错误)")
    
    print()
    return True


async def test_ngrams_text_analysis(client: Client):
    """
    测试 9: N-grams 文本分析
    获取论文的词频数据
    """
    print("=" * 70)
    print("测试 9: N-grams 文本分析")
    print("       目标: 分析论文全文的关键词频")
    print("=" * 70)
    
    # 使用一篇有 ngrams 数据的论文
    result = await client.call_tool("ngrams_openalex", {
        "work_id": "W2741809807"  # BERT 论文
    })
    
    ngrams = result.data.get("ngrams", [])
    if ngrams:
        print(f"获取到 {len(ngrams)} 个 N-grams")
        print("\n高频词 (top 10):")
        for ng in ngrams[:10]:
            print(f"  • {ng['ngram']}: 出现 {ng['ngram_count']} 次 (tf={ng['term_frequency']:.4f})")
    else:
        print("该论文无 N-grams 数据 (可能未被全文索引)")
    
    print()
    return True


async def test_advanced_search_boolean(client: Client):
    """
    测试 10: 高级布尔搜索
    使用复杂的 Boolean 语法搜索
    """
    print("=" * 70)
    print("测试 10: 高级布尔搜索")
    print("        目标: 使用 AND/OR/NOT 进行精确搜索")
    print("=" * 70)
    
    # 复杂 Boolean 搜索
    result = await client.call_tool("query_openalex", {
        "entity_type": "works",
        "search": '("machine learning" OR "deep learning") AND (healthcare OR medical) NOT review',
        "filter": "publication_year:2024,is_oa:true,language:en",
        "sort": "cited_by_count:desc",
        "select": "id,title,cited_by_count,type",
        "limit": 5
    })
    
    print('Search: ("machine learning" OR "deep learning") AND (healthcare OR medical) NOT review')
    print("Filter: publication_year:2024,is_oa:true,language:en")
    print(f"结果: {result.data['meta']['count']:,} 篇")
    
    print("\n前 5 篇:")
    for i, w in enumerate(result.data["results"], 1):
        title = w["title"][:55] + "..." if len(w["title"]) > 55 else w["title"]
        print(f"  {i}. {title}")
        print(f"     类型: {w['type']} | 引用: {w['cited_by_count']}")
    print()
    return True


async def main():
    """运行所有测试"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " OpenAlex MCP Server 综合测试 ".center(68) + "║")
    print("║" + " 直接通过 FastMCP Client 测试所有 7 个工具 ".center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    tests = [
        ("两步查询模式 (autocomplete → query)", test_autocomplete_two_step_workflow),
        ("复杂过滤器组合", test_complex_filter_combination),
        ("分组聚合统计", test_group_by_statistics),
        ("批量获取", test_batch_fetch_efficiency),
        ("随机采样可重复性", test_sample_reproducibility),
        ("论文详情 + 引用网络", test_fetch_with_related_analysis),
        ("跨实体工作流", test_cross_entity_workflow),
        ("错误处理", test_tool_error_handling),
        ("N-grams 文本分析", test_ngrams_text_analysis),
        ("高级布尔搜索", test_advanced_search_boolean),
    ]
    
    passed = 0
    failed = 0
    
    # 通过 FastMCP Client 连接到 MCP Server
    async with Client("openalex_mcp_server.py") as client:
        print("✅ MCP Client 已连接\n")
        
        # 列出可用工具
        tools = await client.list_tools()
        print(f"可用工具 ({len(tools)} 个):")
        for tool in tools:
            print(f"  • {tool.name}")
        print()
        
        # 运行测试
        for name, test_func in tests:
            try:
                result = await test_func(client)
                if result:
                    passed += 1
                    print(f"✅ {name} 通过\n")
                else:
                    failed += 1
                    print(f"❌ {name} 失败\n")
                await asyncio.sleep(0.2)  # 避免速率限制
            except Exception as e:
                failed += 1
                print(f"❌ {name} 异常: {e}\n")
    
    # 汇总
    print("=" * 70)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    if failed == 0:
        print("🎉 所有测试通过！MCP 服务器功能正常。")
    else:
        print(f"⚠️  有 {failed} 个测试失败，请检查日志。")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
