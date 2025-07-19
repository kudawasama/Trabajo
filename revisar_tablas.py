import sqlite3

conn = sqlite3.connect("facturas.db")
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(facturas)")
columnas = cursor.fetchall()

print("Columnas en 'facturas':")
for col in columnas:
    print(col)

conn.close()

