import os
import sqlite3
from pathlib import Path


def db_path():
    # путь к базе: из env для тестов, иначе рядом с кодом
    env = os.environ.get("SHOP_DB")
    if env:
        return Path(env)
    return Path(__file__).with_name("shop.db")


def connect():
    con = sqlite3.connect(db_path())
    con.row_factory = sqlite3.Row
    return con


def init_db():
    # схема + сид, идемпотентно
    con = connect()
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users(login TEXT PRIMARY KEY, password TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, price REAL)")
    cur.execute("CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT, login TEXT, total REAL, items TEXT, created TEXT)")
    cur.execute("INSERT OR IGNORE INTO users VALUES('admin','1234')")
    if cur.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO products(title,price) VALUES(?,?)",
            [("Мышь", 1490), ("Клавиатура", 3990), ("Коврик", 890)],
        )
    con.commit()
    con.close()
