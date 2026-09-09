import sqlite3
from pathlib import Path

from request import get_url_apparels
from type import get_product_type

DB_PATH = Path(__file__).resolve().parent / "snkrdunk_cache.db"


def init_database():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id TEXT,
                name TEXT,
                url TEXT,
                PRIMARY KEY (id, name)
            )
        """)


def get_or_fetch_url(product_id, product_name):
    # Mỗi lần gọi mở một connection mới để connection luôn thuộc
    # đúng thread đang thực thi hàm này.
    with sqlite3.connect(DB_PATH) as conn:
        result = conn.execute(
            "SELECT url FROM products WHERE id = ? AND name = ?",
            (product_id, product_name),
        ).fetchone()

        if result:
            print("Đã tìm thấy trong CSDL cục bộ!")
            return result[0]

        print("Chưa có, tiến hành cào dữ liệu từ SNKRDUNK...")

        product_type = get_product_type(product_id)
        if product_type == "products":
            new_url = f"https://snkrdunk.com/products/{product_id}"
        else:
            new_url = get_url_apparels(product_id, product_name)

        if not new_url or new_url == "not found":
            return None

        conn.execute(
            "INSERT OR REPLACE INTO products (id, name, url) VALUES (?, ?, ?)",
            (product_id, product_name, new_url),
        )
        conn.commit()
        return new_url


init_database()
