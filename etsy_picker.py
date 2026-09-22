# -*- coding: utf-8 -*-
"""Etsy 选品分析工具 CLI。

用法示例：
  python etsy_picker.py search --keywords "vintage ring" --sort hot --limit 30
  python etsy_picker.py search --keywords "jewelry" --taxonomy-id 6548 --sort estimate --csv out.csv
  python etsy_picker.py listing --id 123456789
  python etsy_picker.py shop --id 654321 --sort reviews --limit 50
  python etsy_picker.py shop --name "SomeShopName" --sort rating
  python etsy_picker.py taxonomy --search jewelry
  python etsy_picker.py analyze --keywords "gift for mom" --limit 40 --top 15
"""
import argparse
import sys

import analysis
import etsy_api
import report

COLUMNS = [
    ("ID", "listing_id"),
    ("标题", "title"),
    ("店铺", "shop_name"),
    ("价格$", "price_usd"),
    ("收藏", "num_favorers"),
    ("评论", "review_count"),
    ("评分", "rating"),
    ("热销分", "hot_score"),
    ("估算分", "estimate_score"),
    ("链接", "url"),
]


def _make_api(args):
    return etsy_api.EtsyAPI(api_key=args.api_key)


def _fetch_with_shops(api, listings):
    """为列表补店铺信息（用于评分/评论回退与店铺名展示）。"""
    shop_ids = [l.get("shop_id") for l in listings if l.get("shop_id")]
    shop_map, failed = api.fetch_shops(shop_ids)
    if failed:
        print("[提示] %d 个店铺信息获取失败，相关评分/评论列将显示为缺失。" % len(failed))
    return shop_map


def _show(listings, shop_map, sort_mode):
    listings = analysis.sort_listings(listings, sort_mode, shop_map)
    report.print_table(analysis.analyze_listings(listings, shop_map), COLUMNS)
    print("\n排序口径：%s" % analysis.SORT_MODES.get((sort_mode or "hot").lower(), ""))


def cmd_search(args):
    api = _make_api(args)
    print("正在搜索：%s（类目 %s，最多 %d 条）..." % (
        args.keywords or "全部", args.taxonomy_id or "-", args.limit))
    data = api.search_listings(keywords=args.keywords, taxonomy_id=args.taxonomy_id,
                               limit=args.limit, offset=args.offset)
    listings = data.get("results") or []
    if not listings:
        print("未找到商品，试试其他关键词或类目。")
        return
    print("命中 %s 条，展示 %d 条。" % (data.get("count", "?"), len(listings)))
    shop_map = _fetch_with_shops(api, listings)
    _show(listings, shop_map, args.sort)
    if args.csv:
        _export(args.csv, listings, shop_map)


def cmd_listing(args):
    api = _make_api(args)
    try:
        listing = api.get_listing(args.id)
    except etsy_api.EtsyAPIError as e:
        print("错误：%s" % e)
        return
    shop_map = _fetch_with_shops(api, [listing])
    print("\n=== 商品详情 ===")
    print("标题：%s" % listing.get("title"))
    print("链接：%s" % listing.get("url"))
    print("价格：%s  %s" % (listing.get("price", {}).get("amount"), listing.get("price", {}).get("currency_code")))
    print("收藏数：%s   评论数：%s   评分：%s" % (
        listing.get("num_favorers") or 0,
        analysis.get_review_count(listing, shop_map),
        analysis.get_rating(listing, shop_map) or "-"))
    print("类目：%s" % " > ".join(listing.get("taxonomy_path") or []))
    print("tags：%s" % ", ".join(listing.get("tags") or []))
    print("描述：%s" % (listing.get("description") or "")[:500])
    try:
        imgs = api.get_listing_images(args.id).get("results") or []
        print("\n图片（%d 张）：" % len(imgs))
        for i, img in enumerate(imgs[:8], 1):
            print("  %d. %s" % (i, img.get("url_fullxfull") or img.get("url_570xN") or "-"))
    except etsy_api.EtsyAPIError as e:
        print("[提示] 图片获取失败：%s" % e)


def cmd_shop(args):
    api = _make_api(args)
    shop_id = args.id
    if not shop_id:
        try:
            data = api._get("/shops", {"shop_name": args.name})
            shops = data.get("results") or data.get("shops") or []
            if not shops:
                print("未找到店铺：%s" % args.name)
                return
            shop_id = shops[0].get("shop_id")
            print("按名称命中店铺：%s（ID %s）" % (shops[0].get("shop_name"), shop_id))
        except etsy_api.EtsyAPIError as e:
            print("错误：%s" % e)
            return
    try:
        shop = api.get_shop(shop_id)
    except etsy_api.EtsyAPIError as e:
        print("错误：%s" % e)
        return
    print("\n=== 店铺：%s ===" % shop.get("shop_name"))
    print("评分：%s   评论数：%s   会员：%s" % (
        shop.get("rating") or "-", shop.get("review_count") or 0, shop.get("num_favorers") or 0))
    print("链接：%s" % (shop.get("url") or "https://www.etsy.com/shop/" + str(shop.get("shop_name"))))
    data = api.get_shop_active_listings(shop_id, limit=args.limit, offset=args.offset)
    listings = data.get("results") or []
    if not listings:
        print("该店铺暂无活跃商品。")
        return
    print("活跃商品 %s 条，展示 %d 条。" % (data.get("count", "?"), len(listings)))
    shop_map = {shop_id: shop}
    _show(listings, shop_map, args.sort)
    if args.csv:
        _export(args.csv, listings, shop_map)


def cmd_taxonomy(args):
    api = _make_api(args)
    try:
        tree = api.get_taxonomy()
    except etsy_api.EtsyAPIError as e:
        print("错误：%s（taxonomy 端点可能需要更高权限，可用关键词搜索替代）" % e)
        return
    flat = []
    def walk(nodes, path):
        for n in nodes or []:
            name = n.get("name")
            new_path = path + [name] if name else path
            if n.get("id"):
                flat.append((n["id"], " > ".join(new_path)))
            walk(n.get("children"), new_path)
    walk(tree.get("results") or [], [])
    if args.search:
        kw = args.search.lower()
        flat = [(i, p) for i, p in flat if kw in p.lower()]
    print("共 %d 个类目%s。" % (len(flat), "（已按 '%s' 过滤）" % args.search if args.search else ""))
    report.print_table([{"id": i, "path": p} for i, p in flat[:args.limit]],
                       [("类目 ID", "id"), ("路径", "path")])
    if args.csv:
        report.export_csv(args.csv, [{"id": i, "path": p} for i, p in flat],
                          [("类目 ID", "id"), ("路径", "path")])


def cmd_analyze(args):
    api = _make_api(args)
    print("正在抓取用于分析的商品（%s，最多 %d 条）..." % (args.keywords, args.limit))
    data = api.search_listings(keywords=args.keywords, taxonomy_id=args.taxonomy_id,
                               limit=args.limit, offset=args.offset)
    listings = data.get("results") or []
    if not listings:
        print("未找到商品，无法分析。")
        return
    print("\n=== 标题高频关键词（合并 %d 个商品）===" % len(listings))
    for w, c in analysis.title_word_frequency(listings, args.top):
        print("  %-24s %s" % (w, c))
    print("\n=== Tags 高频词（选品方向参考）===")
    for w, c in analysis.tag_frequency(listings, args.top):
        print("  %-24s %s" % (w, c))
    print("\n=== 按热销分排序的商品 ===")
    shop_map = _fetch_with_shops(api, listings)
    _show(listings, shop_map, "hot")
    if args.csv:
        _export(args.csv, listings, shop_map)


def _export(path, listings, shop_map):
    report.export_csv(path, analysis.analyze_listings(listings, shop_map), COLUMNS)
    print("已导出 CSV：%s" % path)


def main(argv=None):
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--api-key", help="Etsy API key（也可用环境变量 ETSY_API_KEY）")
    p = argparse.ArgumentParser(description="Etsy 选品分析工具（官方 API，仅需 API key）", parents=[common])
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("search", help="按关键词/类目搜索商品并排序", parents=[common])
    sp.add_argument("--keywords")
    sp.add_argument("--taxonomy-id", type=int)
    sp.add_argument("--sort", choices=list(analysis.SORT_MODES), default="hot")
    sp.add_argument("--limit", type=int, default=25)
    sp.add_argument("--offset", type=int, default=0)
    sp.add_argument("--csv")
    sp.set_defaults(fn=cmd_search)

    sp = sub.add_parser("listing", help="指定商品 ID 查看详情（含图片与 tags）", parents=[common])
    sp.add_argument("--id", type=int, required=True)
    sp.set_defaults(fn=cmd_listing)

    sp = sub.add_parser("shop", help="按店铺 ID 或名称查看商品并排序", parents=[common])
    sp.add_argument("--id", type=int)
    sp.add_argument("--name")
    sp.add_argument("--sort", choices=list(analysis.SORT_MODES), default="hot")
    sp.add_argument("--limit", type=int, default=25)
    sp.add_argument("--offset", type=int, default=0)
    sp.add_argument("--csv")
    sp.set_defaults(fn=cmd_shop)

    sp = sub.add_parser("taxonomy", help="列出/搜索 Etsy 类目树", parents=[common])
    sp.add_argument("--search")
    sp.add_argument("--limit", type=int, default=50)
    sp.add_argument("--csv")
    sp.set_defaults(fn=cmd_taxonomy)

    sp = sub.add_parser("analyze", help="搜索商品并做标题/Tags 词频分析（选品指导）", parents=[common])
    sp.add_argument("--keywords", required=True)
    sp.add_argument("--taxonomy-id", type=int)
    sp.add_argument("--limit", type=int, default=40)
    sp.add_argument("--top", type=int, default=15)
    sp.add_argument("--csv")
    sp.set_defaults(fn=cmd_analyze)

    args = p.parse_args(argv)
    try:
        args.fn(args)
    except etsy_api.EtsyAPIError as e:
        print("错误：%s" % e)
        return 1
    except KeyboardInterrupt:
        print("\n已取消。")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
