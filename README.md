# 冰岛一日游 — 多平台发团价格 & 路线地图

抓取 **4 家运营商** 的一日游线路(发团价 + 经过点),统一转成结构化数据,并生成一个 Excel(troll.is)和一个可交互路线地图。**价格统一为冰岛克朗 ISK**。

| 运营商 | 数量 | 数据方式 | 价格 |
|---|---|---|---|
| [troll.is](https://troll.is/day-tour/) | 12 | schema.org JSON-LD 真实坐标行程 | **Bókun API 实时 ISK 起价** |
| [bustravel.is](https://bustravel.is/) | 29 | Bókun `activity` API(部分带真实坐标行程)+ LLM 抽站点 → 地理编码 | **Bókun API 实时 ISK 起价** |
| [cn.adventures.is](https://cn.adventures.is/) | 57 | `api.adventures.is` 价格 + LLM 从中文页抽站点 → 地理编码 | **api.adventures.is 实时 ISK 起价** |
| [magicicelandtravel.com](https://www.magicicelandtravel.com/) | 11 | (本轮未更新;产品 ID 被 Duda 运行时注入,需浏览器逐页采) | 未标价 |

共 **109 条线路**(单点活动已过滤)。价格来源:三家均使用 **Bókun** 预订引擎,起价通过其 `widgets.bokun.io/widgets/<channel>/activity/<id>` 接口取到(无需选日期)。

## 成品

| 文件 | 说明 |
|---|---|
| `index.html` | **MapLibre 版(推荐,GitHub Pages 主页)**:移动端优先的**原生 App 式 UI**——地图全屏铺满作主视觉,手机上是可拖拽的**底部抽屉**(收起只露「N 条线路 + 运营商」,上滑展开区域/途径点/线路列表,三档吸附),桌面端是「地图 + 右侧结果栏」双栏。真实底图(**街道 / 卫星 / 地形** 可切换)+ 109 条线路按运营商着色。玻璃拟态浮层控件、原生手势(滚轮/双指捏合/拖动)、悬停高亮、点击线路锁定、点圆点或「途径点」多选筛线路、途径点自动避让标签、深/浅色自适应、刘海安全区适配。**需联网**(加载 MapLibre + 底图瓦片)。 |
| `troll_tours_map.html` | 手搓 SVG 版:**自包含、离线可开**(不依赖任何外部资源),作后备。同样的 44 条线路 + 筛选/多选途径点/手机适配。 |
| `troll_daily_tours_prices.xlsx` | troll.is 12 条线路的价格表(仅 troll.is,价格齐全)。 |

> 在线地图:见仓库 GitHub Pages 链接(Settings → Pages)。所有线路均按各家真实一日游行程绘制。

## 目录结构

```
travelMengting/
├── troll_tours_map.html            # 成品:44 条线路交互地图(自包含,离线可开)
├── troll_daily_tours_prices.xlsx   # 成品:troll.is 价格表
├── README.md
├── data/
│   ├── tours.json                  # troll.is 结构化数据(真实坐标)
│   ├── iceland.geojson             # 冰岛轮廓(Natural Earth 50m,已精简)
│   ├── troll_sitemap.xml
│   ├── html/                       # troll.is 12 个页面原始 HTML
│   └── sources/                    # 另 3 家运营商的数据
│       ├── prefetch.json           # 36 个页面的标题+可见文字+Google Maps 链接
│       ├── tours/t00..t35.json     # 拆分后每团一个文件(喂给抽取 agent)
│       ├── extracted.json          # LLM 抽取结果(名称/价格/币种/区域/有序站点)
│       ├── geocache.json           # 地名 → 坐标 缓存(seed + Nominatim)
│       └── sources_tours.json      # 合并 + 地理编码后的 32 条线路
└── scripts/
    ├── fetch_all.py                # troll.is:下载+解析 → data/tours.json
    ├── parse_itinerary.py          # troll.is:JSON-LD 提取
    ├── build_tours_xlsx.py         # 生成 xlsx
    ├── prefetch_sources.py         # 另 3 家:下载 36 个页面文字 → prefetch.json
    ├── geocode.py                  # 地名地理编码(seed 表 + OSM Nominatim)
    ├── build_sources.py            # extracted + geocache → sources_tours.json
    ├── build_map.py                # 合并 4 家 → troll_tours_map.html
    └── map_template.html           # 地图模板(build_map.py 注入数据)
```

## 数据管线(另 3 家运营商)

1. `prefetch_sources.py` — 按各站 sitemap 选出每家 ~12 条经典 day tour,下载页面可见文字。
2. **抽取(多 agent 工作流)** — 每个页面一个 LLM agent,读文件返回 `{名称, 价格, 币种, 区域, 有序站点[规范地名]}`;中文/营销名转成规范冰岛地名。结果 → `extracted.json`。
3. `geocode.py` — 收集全部唯一地名,先查内置 seed 坐标表,余下走 OSM Nominatim(限速 1 req/s)→ `geocache.json`。
4. `build_sources.py` — 站点名映射坐标,<2 个可定位站点的(纯单点活动)略去 → `sources_tours.json`。
5. `build_map.py` — 合并 troll.is(真实坐标)+ 3 家(估算)→ 44 条线路地图。

重新生成:
```bash
pip install openpyxl                 # 仅 xlsx 需要
python scripts/prefetch_sources.py   # 需要 curl
# 抽取这一步是多 agent 工作流,已把结果存进 data/sources/extracted.json
python scripts/geocode.py
python scripts/build_sources.py
python scripts/build_map.py
```

## 重要说明 / 注意事项

- **着色 = 运营商**(Troll.is 蓝 / Magic 橙 / BusTravel 绿 / Adventures 紫)。区域改为筛选维度。
- **实线 = troll.is 的真实坐标;虚线 = 另 3 家的地理编码估算坐标**(站点位置准,连线为示意直线,非真实驾驶路径)。
- **价格为各页面原始币种**:Troll.is=USD,BusTravel=ISK;magicicelandtravel / adventures 的价格多为 JS 动态加载,静态页面取不到,故大量显示「未标价」。**不同币种不可直接比较**。
- troll.is 里 **Silfra 浮潜 / Reykjadalur 骑马 / Landmannalaugar** 三条为人工补充坐标;Landmannalaugar 含 Hjálparfoss / Háifoss / Landmannalaugar 三站。
- 站点有序性来自页面标题/行程文字,属**尽力还原**;个别线路站点顺序或选取可能与实际略有出入(每条 tooltip/列表可展开核对,并附原网址)。
- 抓取日期:**2026-07-25**。

## troll.is 价格表(xlsx)补充

- 价格币种 USD,`每人` 起价;#11–12 为私人 VIP 特价团(#12 按整团报价)。均价只按 10 条标准小团算。
