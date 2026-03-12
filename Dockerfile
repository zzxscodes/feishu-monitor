FROM python:3.11-slim

WORKDIR /app

# 仅使用 psycopg2-binary，无需编译依赖；避免 apt 占用大量磁盘/缓存

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY monitor_feishu.py /app/monitor_feishu.py

# 环境变量默认值（可通过 docker run -e 覆盖）
# 默认连接主机上的 PostgreSQL (172.17.0.1:5432，主机在bridge网络中的IP)，与 ailending 共享数据库
# ailending 写入 errors 和 account_balances 表，feishu_monitor 读取并发送飞书通知
# 如需连接其他数据库，通过环境变量覆盖：docker run -e DB_HOST=新地址 -e DB_PORT=新端口 ...
ENV DB_HOST=*.*.*.* \
    DB_PORT=**** \
    DB_NAME=bitfinex_monitor \
    DB_USER=bfx_monitor \
    DB_PASSWORD=Ailending2025 \
    CHECK_INTERVAL_SECONDS=300 \
    FEISHU_WEBHOOK="******

CMD ["python", "monitor_feishu.py"]



