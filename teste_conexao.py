import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()  # lê as variáveis do arquivo .env

conexao = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
)

cursor = conexao.cursor()
cursor.execute("SELECT nome, sla_horas FROM prioridades ORDER BY sla_horas;")

for linha in cursor.fetchall():
    print(linha)

cursor.close()
conexao.close()