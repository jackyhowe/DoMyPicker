# Etsy 选品分析工具（etsy-picker）

基于 Etsy 官方 API 的命令行选品分析工具：按类目 / 指定商品 / 指定店铺三个维度查询，按热销、评论、好评、浏览、加购等方向排序，并分析标题关键词、Tags 词频与图片信息，输出终端表格或 CSV，辅助 Etsy 选品决策。

## 环境要求



* Python 3.8+（**零第三方依赖**，仅用标准库，无需 pip install）

* 一个免费的 Etsy API key

## 获取 API key（约 3 分钟）



1. 打开 [https://www.etsy.com/developers/register](https://www.etsy.com/developers/register) 或进入 [https://www.etsy.com/developers/](https://www.etsy.com/developers/)，用 Etsy 账号登录。

2. 注册一个应用（Name 随意，如 `etsy-picker`），提交后页面会显示一串 API key（字母数字混合，约 20 位）。

3. 配置 key（三选一）：

* 环境变量：`set ETSY_API_KEY=你的key`（PowerShell：`$env:ETSY_API_KEY="你的key"`）

* 命令行参数：`--api-key 你的key`

* 写入文件：`C:\Users\你的用户名\.etsy_picker\key`（内容仅一行 key）

> 本工具只用公开数据端点（仅需 key，无需 OAuth 授权流程）。

## 用法



```
\# 按关键词搜索并排序（默认按热销分）

python etsy\_picker.py search --keywords "vintage ring" --sort hot --limit 30

\# 指定类目 + 按估算分排序，导出 CSV

python etsy\_picker.py search --keywords "jewelry" --taxonomy-id 6548 --sort estimate --csv out.csv

\# 指定商品详情（含标题/价格/tags/图片 URL/描述）

python etsy\_picker.py listing --id 123456789

\# 指定店铺（按 ID 或名称）的商品排序分析

python etsy\_picker.py shop --id 654321 --sort reviews --limit 50

python etsy\_picker.py shop --name "ShopNameHere" --sort rating

\# 查看/搜索类目树，拿 taxonomy-id

python etsy\_picker.py taxonomy --search jewelry

\# 选品关键词指导：搜索一批商品，统计标题与 Tags 高频词

python etsy\_picker.py analyze --keywords "gift for mom" --limit 40 --top 15
```

### 排序方式（--sort）



| 值          | 含义      | 口径                                                    |
| ---------- | ------- | ----------------------------------------------------- |
| `hot`（默认）  | 热销      | 评论数 ×2.5 + 收藏数 ×0.5，**代理指标**，非真实销量                    |
| `reviews`  | 最多评论    | listing 级评论数；公开端点缺失时回退店铺级                             |
| `rating`   | 最多好评    | 平均评分（通常为店铺级），无评分商品排最后                                 |
| `favorers` | 最多收藏    | num\_favorers 降序                                      |
| `estimate` | 浏览 / 加购 | **启发式估算分**：收藏 ×1 + 评论 ×3 + 价格带加分（5–50 美元区间加分），仅用于横向比较 |

## 指标口径与限制（务必阅读）

**诚实声明：Etsy 不公开销量、浏览数、加购数**—— 这些只对卖家后台可见。本工具所有 "热销 / 浏览 / 加购" 排序都是基于公开信号的**代理或估算指标**，用于横向比较和初步筛选，不代表 Etsy 后台真实数据。



* 评论数与评分：v3 公开端点通常不返回 listing 级评论，工具自动回退到**店铺级** review\_count /rating 并照实展示；选品时请结合商品页人工复核。

* 图片：listing 详情命令返回图片 URL 列表，可自行下载或人工查看；工具不抓取页面。

* 限流：Etsy API 有速率限制，工具内置退避重试；批量拉取店铺信息时自动限速。

* 合规：本工具仅使用官方 API 与公开数据，不抓取网页，不触碰卖家后台数据。

## 文件结构



```
etsy-picker/

├── etsy\_picker.py   # CLI 入口

├── etsy\_api.py      # API 封装（urllib，限流重试，key 配置）

├── analysis.py      # 排序、评分模型、关键词/词频分析

├── report.py        # 终端表格 + CSV 导出（防公式注入）

└── README.md
```