# 把引擎放到公网（让任何人都能`真查`）

现状：`qhqiqi.cn/b1x` 是 **GitHub Pages 静态站**，它只会发文件，不会跑 Python。
所以线上点「实时选型查询」时，接口 `127.0.0.1:8787` 连不上 → 自动切 8 条离线缓存。
要让任何人真查，必须把 **引擎跑在一台有公网 IP 的机器上**（你有阿里云，正好）。

---

## 方案 B（推荐）：整个 /b1x 搬到阿里云

好处：静态和接口同一个域，前端**不用改一行**（我已在 `app/match.js` 里加了同源判断）。

### 1. 上传代码（在你的 Windows 上）

```powershell
cd Y:\hks
tar -czf b1x-deploy.tar.gz p2 data app index.html p2\web
scp b1x-deploy.tar.gz root@<你的服务器IP>:/tmp/
```

### 2. 服务器上解包并跑服务

```bash
mkdir -p /opt/b1x && tar -xzf /tmp/b1x-deploy.tar.gz -C /opt/b1x
# 引擎是纯标准库，不需要 pip install
/usr/bin/python3 /opt/b1x/p2/scripts/api_server.py --port 8787 --host 127.0.0.1
# 先手动跑一遍，看到 "serving on 8787" 再 Ctrl+C，交给 systemd
```

### 3. 装成系统服务

```bash
sudo cp /opt/b1x/deploy/systemd/gy-match-api.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now gy-match-api
systemctl status gy-match-api --no-pager
curl -sS http://127.0.0.1:8787/health
```

### 4. 静态文件 + nginx

```bash
sudo mkdir -p /var/www/b1x
sudo cp -r /opt/b1x/app /opt/b1x/p2 /opt/b1x/index.html /var/www/b1x/
sudo cp /opt/b1x/deploy/nginx/b1x-aliyun.conf /etc/nginx/conf.d/
sudo nginx -t && sudo systemctl reload nginx
```

### 5. 证书 + DNS

```bash
sudo certbot --nginx -d qhqiqi.cn -d www.qhqiqi.cn     # 已有的证书可跳过
```

然后把 `qhqiqi.cn` 的 **A 记录** 从 GitHub Pages 的 IP（185.199.111.153）
改成**你阿里云的公网 IP**。改完等 TTL（通常 10 分钟）。

### 6. 验收

```bash
bash /opt/b1x/deploy/smoke.sh                                  # 本机
curl -sS https://qhqiqi.cn/b1x/api/health                      # 公网
curl -sS "https://qhqiqi.cn/b1x/api/match?q=FMSI%204524"       # 公网真查
```

浏览器打开 https://qhqiqi.cn/b1x/app/match.html 直接输入——**这就是别人也能真查的样子**。

---

## 方案 A（改动最小）：只把接口放子域

静态继续留 GitHub Pages，只加一条 DNS：

1. 阿里云 DNS 加 A 记录 `api.qhqiqi.cn` → 服务器 IP
2. 服务器上装 `deploy/nginx/api-subdomain.conf`，证书 `certbot -d api.qhqiqi.cn`
3. 演示链接改成 `https://qhqiqi.cn/b1x/app/match.html?api=https://api.qhqiqi.cn`

（前端已支持 `?api=` 参数，不用改代码；但每换一次链接就要记得带参数。）

---

## 方案 C：Docker（服务器上已装 docker 时）

```bash
cd /opt/b1x && docker compose -f deploy/docker-compose.yml up -d --build
curl -sS http://127.0.0.1:8787/health
```

---

## 注意事项

- **端口只绑 127.0.0.1**，对外一律走 nginx（443），别把 8787 开到公网。
- 引擎零依赖，但**必须带 `data/structured/`**（skus.json / export_refs.json / aliases.json），少了就起不来。
- `资料包/`（100MB PDF）**不用上传**，线上只需要结构化数据。
- 阿里云安全组记得放行 **443**（80 用于 certbot 验证）。
- 服务起不来先看 `journalctl -u gy-match-api -n 50`。
