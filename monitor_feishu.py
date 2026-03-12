import os
import time
from datetime import datetime
from typing import Optional, Tuple

import psycopg2
import requests


FEISHU_WEBHOOK = os.getenv(
    "FEISHU_WEBHOOK",
    "******
)

DB_HOST = os.getenv("DB_HOST", "54.199.228.0")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "bitfinex_monitor")
DB_USER = os.getenv("DB_USER", "bfx_monitor")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Ailending2025")

CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))  

LOG_FILE = os.getenv("LOG_FILE")


def write_log(level: str, message: str) -> None:
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {message}"
    print(line, flush=True)

    if LOG_FILE:
        try:
            os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        except Exception:
            pass
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass


def get_connection():
    write_log("INFO", f"Connecting to DB {DB_HOST}:{DB_PORT}/{DB_NAME} as {DB_USER}")
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def get_latest_row(cursor, table_name: str) -> Optional[Tuple]:
    cursor.execute(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT 1;")
    row = cursor.fetchone()
    return row


def get_latest_error_row(cursor) -> Optional[Tuple]:
    # errors 表只关心 WARNING 及以上，避免 INFO 心跳/运行状态刷屏
    cursor.execute(
        "SELECT * FROM errors WHERE level IN ('WARNING','ERROR','CRITICAL','FATAL') "
        "ORDER BY id DESC LIMIT 1;"
    )
    return cursor.fetchone()


def format_row(columns, row) -> str:
    data = {col.name: value for col, value in zip(columns, row)}
    lines = [f"{k}={v}" for k, v in data.items()]
    return "\n".join(lines)


def send_feishu_text(text: str) -> None:
    if "AILENDING" not in text:
        text = f"AILENDING\n{text}"

    payload = {
        "msg_type": "text",
        "content": {
            "text": text,
        },
    }
    try:
        resp = requests.post(FEISHU_WEBHOOK, json=payload, timeout=10)
        resp.raise_for_status()
        write_log("INFO", "Feishu message sent successfully.")
    except Exception as e:
        write_log("ERROR", f"Failed to send message to Feishu: {e}")
        try:
            write_log("ERROR", f"Response: {resp.status_code}, {resp.text}")
        except Exception:
            pass


def main():
    last_asset_id: Optional[int] = None
    last_error_id: Optional[int] = None

    write_log("INFO", f"Monitor started, interval={CHECK_INTERVAL_SECONDS}s, log_file={LOG_FILE}")

    while True:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    latest_asset = get_latest_row(cur, "account_balances")
                    asset_text = None
                    if latest_asset:
                        latest_asset_id = latest_asset[0] 
                        if last_asset_id is None:
                            last_asset_id = latest_asset_id
                        elif latest_asset_id != last_asset_id:
                            last_asset_id = latest_asset_id
                            asset_text = "最新 account_balances 记录：\n" + format_row(
                                cur.description, latest_asset
                            )

                    latest_error = get_latest_error_row(cur)
                    error_text = None
                    if latest_error:
                        latest_error_id = latest_error[0]
                        if last_error_id is None:
                            last_error_id = latest_error_id
                        elif latest_error_id != last_error_id:
                            last_error_id = latest_error_id
                            error_text = "最新 errors 记录：\n" + format_row(
                                cur.description, latest_error
                            )

            if asset_text or error_text:
                parts = []
                if asset_text:
                    parts.append(asset_text)
                if error_text:
                    parts.append(error_text)
                message = "\n\n".join(parts)
                write_log("INFO", f"Sending Feishu message:\n{message}")
                send_feishu_text(message)
            else:
                write_log("INFO", "No new asset/error records, nothing to send.")

        except Exception as e:
            write_log("ERROR", f"Monitor loop error: {e}")

        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()


