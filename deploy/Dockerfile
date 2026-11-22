# 冠英匹配引擎 —— 零第三方依赖（纯标准库），镜像可跑在任意 x86/arm
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /srv
COPY p2 /srv/p2
COPY data /srv/data
EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8787/health')" || exit 1
CMD ["python", "/srv/p2/scripts/api_server.py", "--port", "8787", "--host", "0.0.0.0"]
