# -*- coding: utf-8 -*-
"""Etsy Open API v3 封装（零依赖，仅用标准库）。

只使用公开数据端点（仅需 API key，无需 OAuth）。
端点可用性以 Etsy 官方文档为准；调用失败时抛出 EtsyAPIError 并给出可读信息。
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://openapi.etsy.com/v3/application"
USER_AGENT = "etsy-picker/1.0 (product research tool)"


class EtsyAPIError(Exception):
    """API 调用错误，message 为对用户可读的说明。"""


class EtsyAPI:
    def __init__(self, api_key=None):
        self.api_key = api_key or load_api_key()
        if not self.api_key:
            raise EtsyAPIError(
                "未配置 Etsy API key。请通过 ETSY_API_KEY 环境变量、--api-key 参数，"
                "或写入 ~/.etsy_picker/key 文件提供。申请教程见 README.md。"
            )

    # ---------- 基础请求 ----------
    def _get(self, path, params=None, retries=3):
        """GET 请求，带超时、限流退避与错误翻译。"""
        url = BASE_URL + path
        if params:
            url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v not in (None, "")})
        headers = {
            "x-api-key": self.api_key,
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        }
        last_err = None
        for attempt in range(retries):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                body = ""
                try:
                    body = e.read().decode("utf-8", "replace")[:300]
                except Exception:
                    pass
                if e.code == 403 and "key" in body.lower():
                    raise EtsyAPIError("API key 无效或未获授权，请检查 key 是否正确。")
                if e.code == 429:
                    last_err = EtsyAPIError("触发 Etsy API 限流（429），已重试。")
                    time.sleep(1.5 * (attempt + 1))
                    continue
                if e.code == 404:
                    raise EtsyAPIError("请求的资源不存在（404），请检查 ID 或类目是否正确。")
                last_err = EtsyAPIError("Etsy API 返回错误 %s：%s" % (e.code, body[:200]))
            except urllib.error.URLError as e:
                last_err = EtsyAPIError("无法连接 Etsy API：%s" % e.reason)
            except TimeoutError:
                last_err = EtsyAPIError("请求 Etsy API 超时。")
            if attempt < retries - 1:
                time.sleep(1.0 * (attempt + 1))
        raise last_err if last_err else EtsyAPIError("请求失败，未知原因。")

    # ---------- 公开端点 ----------
    def search_listings(self, keywords=None, taxonomy_id=None, sort_on=None,
                        sort_order="DESC", limit=25, offset=0):
        """搜索活跃商品。sort_on 仅支持 API 侧字段（score/created/price/updated），
        本工具的指标排序在本地完成，见 analysis.py。"""
        limit = max(1, min(int(limit), 100))
        return self._get("/listings/active", {
            "keywords": keywords,
            "taxonomy_id": taxonomy_id,
            "sort_on": sort_on,
            "sort_order": sort_order,
            "limit": limit,
            "offset": offset,
        })

    def get_listing(self, listing_id):
        """单个商品详情（含标题、价格、tags、收藏数等）。"""
        return self._get("/listings/%s" % listing_id)

    def get_listing_images(self, listing_id):
        """商品图片列表。"""
        return self._get("/listings/%s/images" % listing_id)

    def get_shop(self, shop_id):
        """店铺信息（含 rating / review_count，店铺级评论数据）。"""
        return self._get("/shops/%s" % shop_id)

    def get_shop_active_listings(self, shop_id, limit=25, offset=0):
        """指定店铺的活跃商品。"""
        limit = max(1, min(int(limit), 100))
        return self._get("/shops/%s/listings/active" % shop_id, {
            "limit": limit,
            "offset": offset,
        })

    def get_taxonomy(self):
        """全类目树（buyer 端点）。失败时抛错，调用方按可选功能处理。"""
        return self._get("/taxonomy/buyer/get")

    # ---------- 批量辅助 ----------
    def fetch_shops(self, shop_ids):
        """按需批量获取店铺信息，返回 {shop_id: shop}。去重，失败项跳过并记录。"""
        result, failed = {}, []
        for sid in sorted(set(shop_ids)):
            try:
                result[sid] = self.get_shop(sid)
            except EtsyAPIError:
                failed.append(sid)
            time.sleep(0.3)  # 温和限速
        return result, failed


def load_api_key():
    """从环境变量或 ~/.etsy_picker/key 读取 key。"""
    key = os.environ.get("ETSY_API_KEY", "").strip()
    if key:
        return key
    try:
        key_file = os.path.join(os.path.expanduser("~"), ".etsy_picker", "key")
        with open(key_file, "r", encoding="utf-8") as f:
            key = f.read().strip()
        return key or None
    except (OSError, IOError):
        return None
