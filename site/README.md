# Light-Science 官网

单页静态站点，没有构建步骤。把整个 `site/` 目录上传到服务器的网站根目录即可；所有引用都是相对路径，也可以放在子路径下（例如 `https://example.com/light-science/`）。

## 目录

```text
site/
├── index.html          # 中文页
├── en/index.html       # 英文页（<html lang="en" data-base="../">，与中文页共用下面的资源）
├── assets/
│   ├── site.css        # 样式（色板取自 Logo）
│   ├── site.js         # 交互与动效
│   └── img/            # 由 docs/assets 生成的网页尺寸副本（WebP / PNG）
└── vendor/             # GSAP 3.12.5 与 ScrollTrigger，本地引用，不依赖 CDN
```

## 本地预览

```bash
cd site
python -m http.server 8080
```

然后打开 <http://localhost:8080>。直接双击 `index.html` 也能看，但剪贴板复制在 `file://` 下会退回兼容写法。

## 当前部署（lightchuan.xyz）

- 服务器：138.2.76.212（Ubuntu 24.04，nginx），用户 `ubuntu`。和 lightchuan.site / .shop / .space 共用这台机器，彼此独立配置。
- 站点文件：`/var/www/light-science/releases/<UTC 时间戳>/`，`/var/www/light-science/current` 指向当前版本；回滚时把 `current` 改指上一个版本即可。
- nginx 配置：`/etc/nginx/sites-available/lightchuan.xyz`（已链接到 `sites-enabled`），日志 `/var/log/nginx/lightchuan.xyz.*.log`。
- 证书：certbot webroot 方式（`-w /var/lib/letsencrypt`），证书名 `lightchuan.xyz`，覆盖 `lightchuan.xyz` 与 `www.lightchuan.xyz`；续期由 `certbot.timer` 负责。
- 发布新版本：把 `site/`（不含本 README）打包上传，解压到新的时间戳目录，权限设为目录 755、文件 644，再更新 `current` 链接；HTML 设置了 `no-cache`，静态资源按常规缓存。

## 部署提示

- **Nginx**：`root` 指向 `site/`，建议给 `assets/` 与 `vendor/` 设置长缓存，例如 `location ~* \.(webp|png|css|js)$ { expires 30d; }`。
- **域名确定后**：把 `index.html` 里 `og:image` 改成完整网址（如 `https://你的域名/assets/img/og-image.png`），并按需补充 `<link rel="canonical">` 与 `og:url`，社交平台的分享卡片才能正确显示。
- **字体**：标题使用 Google Fonts 的 Noto Serif SC，以不阻塞渲染的方式加载；访问不到时自动退回系统字体（Windows 为微软雅黑，macOS 为宋体）。如需在国内稳定显示衬线标题，可把字体文件自托管后替换该 `<link>`。
- **GitHub Star 数**：页面在浏览器端读取 GitHub 公共 API，失败或限流时只显示“GitHub”，不影响其他内容。

## 中英文两页

两页共用 `assets/site.js`：脚本按 `<html lang>` 选择文案，按 `data-base` 找资源。改技能表、数据图说明或方法图案例时，`site.js` 里每条数据都写成 `L('中文', 'English')`，两种语言一起改；页面上的静态文字分别在 `index.html` 和 `en/index.html` 里。顶栏的“EN / 中文”互相链接。

## 更新图片

图片副本由原图生成，原图仍在 `docs/assets/`。替换或新增数据图后，重新生成对应的 WebP，并在 `assets/site.js` 的 `CHARTS` 中更新标题、说明和数据来源。

## 许可

页面代码与文案沿用仓库根目录的 MIT License。`vendor/` 中的 GSAP 按其自身许可提供，见 [vendor/README.md](vendor/README.md)。数据图、方法图和二维码沿用仓库中对应资源的来源说明。
