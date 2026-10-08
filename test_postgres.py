import psycopg

conn = psycopg.connect(
    host="localhost",
    port=5432,
    dbname="postgres",
    user="postgres",
    password="banco123",
)

print("CONNECTED")

conn.close()