#!/usr/bin/env bash
# 部署后自检：服务器上跑，三条命令确认接口和静态都通了
set -e
BASE="${BASE:-http://127.0.0.1:8787}"
echo "1) health"
curl -sS "$BASE/health"; echo
echo "2) 国内选型"
curl -sS "$BASE/match?q=%E6%B1%89%E5%BE%B3%2035%20%E8%A1%8D%E6%A1%8F" | head -c 300; echo
echo "3) 海外对码"
curl -sS "$BASE/match?q=FMSI%204524" | head -c 300; echo
echo "OK"
