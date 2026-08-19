import aiosqlite

DB_NAME = "bot_database.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                username TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_menu_msg_id INTEGER
            )
        """)
        
        # Add column if it doesn't exist (for existing databases)
        try:
            await db.execute("ALTER TABLE users ADD COLUMN last_menu_msg_id INTEGER")
        except Exception:
            pass
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                price INTEGER,
                description TEXT,
                emoji_id TEXT DEFAULT '0'
            )
        """)
        
        try:
            await db.execute("ALTER TABLE products ADD COLUMN emoji_id TEXT DEFAULT '0'")
        except Exception:
            pass

        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                product_id INTEGER,
                status TEXT DEFAULT 'pending',
                receipt_photo_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users (telegram_id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        """)
        
        try:
            await db.execute("ALTER TABLE orders ADD COLUMN account_details TEXT")
        except Exception:
            pass
        
        await db.commit()

async def add_user(telegram_id: int, username: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)",
            (telegram_id, username)
        )
        await db.commit()

async def update_last_menu_msg_id(telegram_id: int, msg_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET last_menu_msg_id = ? WHERE telegram_id = ?", (msg_id, telegram_id))
        await db.commit()

async def get_last_menu_msg_id(telegram_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT last_menu_msg_id FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None

async def get_products():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM products") as cursor:
            return await cursor.fetchall()

async def add_product(name: str, price: int, description: str, emoji_id: str = "0"):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO products (name, price, description, emoji_id) VALUES (?, ?, ?, ?)",
            (name, price, description, emoji_id)
        )
        await db.commit()

async def delete_product(product_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        await db.commit()

async def get_product(product_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM products WHERE id = ?", (product_id,)) as cursor:
            return await cursor.fetchone()

async def create_order(telegram_id: int, product_id: int, receipt_photo_id: str):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT INTO orders (telegram_id, product_id, receipt_photo_id) VALUES (?, ?, ?)",
            (telegram_id, product_id, receipt_photo_id)
        )
        await db.commit()
        return cursor.lastrowid

async def get_order(order_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cursor:
            return await cursor.fetchone()

async def get_user_orders(telegram_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT orders.id, orders.status, orders.created_at, orders.account_details, products.name as product_name
            FROM orders
            JOIN products ON orders.product_id = products.id
            WHERE orders.telegram_id = ?
            ORDER BY orders.created_at DESC
        """
        async with db.execute(query, (telegram_id,)) as cursor:
            return await cursor.fetchall()

async def approve_order_manual(order_id: int, account_details: str = None):
    async with aiosqlite.connect(DB_NAME) as db:
        if account_details:
            await db.execute("UPDATE orders SET status = 'approved', account_details = ? WHERE id = ?", (account_details, order_id))
        else:
            await db.execute("UPDATE orders SET status = 'approved' WHERE id = ?", (order_id,))
        await db.commit()

async def reject_order(order_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE orders SET status = 'rejected' WHERE id = ?", (order_id,))
        await db.commit()
