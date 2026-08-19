import asyncio
import aiosqlite
import sys

DB_NAME = "bot_database.db"

async def add_product(name: str, price: int, description: str):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT INTO products (name, price, description) VALUES (?, ?, ?)",
            (name, price, description)
        )
        await db.commit()
        print(f"✅ Product added with ID: {cursor.lastrowid}")

async def add_account(product_id: int, credentials: str):
    async with aiosqlite.connect(DB_NAME) as db:
        # Check if product exists
        async with db.execute("SELECT id FROM products WHERE id = ?", (product_id,)) as c:
            if not await c.fetchone():
                print("❌ Product not found!")
                return

        cursor = await db.execute(
            "INSERT INTO accounts (product_id, credentials) VALUES (?, ?)",
            (product_id, credentials)
        )
        await db.commit()
        print(f"✅ Account added to product {product_id} with ID: {cursor.lastrowid}")

async def list_products():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM products") as cursor:
            products = await cursor.fetchall()
            print("\n--- Products ---")
            for p in products:
                # p = (id, name, price, desc)
                print(f"[{p[0]}] {p[1]} - {p[2]} Toman")
            print("----------------\n")

async def main():
    await aiosqlite.connect(DB_NAME) # Just to ensure the file can be created/opened
    
    while True:
        print("1. Add Product")
        print("2. Add Account to Product")
        print("3. List Products")
        print("4. Exit")
        choice = input("Select an option: ")
        
        if choice == '1':
            name = input("Product Name (e.g. ChatGPT Plus 1 Month): ")
            price = int(input("Price in Toman (e.g. 1500000): "))
            desc = input("Description: ")
            await add_product(name, price, desc)
        elif choice == '2':
            await list_products()
            pid = int(input("Enter Product ID: "))
            cred = input("Enter Credentials (e.g. email:pass): ")
            await add_account(pid, cred)
        elif choice == '3':
            await list_products()
        elif choice == '4':
            break
        else:
            print("Invalid option")

if __name__ == "__main__":
    asyncio.run(main())
