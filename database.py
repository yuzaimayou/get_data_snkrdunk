import sqlite3
from request import get_url_apparels
from type import get_product_type
conn=sqlite3.connect('snkrdunk_cache.db')
cursor=conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id TEXT,
        name TEXT,
        url TEXT,
        PRIMARY KEY (id,name)
    )
''')
conn.commit()

def get_or_fetch_url(product_id, product_name):
    # 3. Kiểm tra xem sản phẩm đã có URL trong CSDL chưa
    cursor.execute("SELECT url FROM products WHERE id = ? AND name=?", (product_id,product_name))
    result = cursor.fetchone()

    if result:
        print("Đã tìm thấy trong CSDL cục bộ!")
        return result[0] # Trả về URL
    else:
        print("Chưa có, tiến hành cào dữ liệu từ SNKRDUNK...")
        # (Gọi hàm cào dữ liệu của bạn ở đây)
        type=get_product_type(product_id)
        if(type=="products"):
            new_url=f'https://snkrdunk.com/products/{product_id}'
        else:
            new_url = get_url_apparels(product_id,product_name)
        if(new_url=='not found'):
            return None
        # 4. Lưu lại vào CSDL để lần sau không phải cào nữa
        cursor.execute("INSERT INTO products (id, name, url) VALUES (?, ?, ?)", 
                       (product_id, product_name, new_url))
        conn.commit()
        return new_url
