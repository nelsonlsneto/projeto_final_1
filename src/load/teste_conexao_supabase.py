from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from pathlib import Path
from urllib.parse import urlparse
import os

BASE_DIR = Path(__file__).resolve().parents[2]

load_dotenv(BASE_DIR / ".env", override=True)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL não encontrada no arquivo .env")

# Mostra sem revelar senha
parsed = urlparse(DATABASE_URL)
print("Usuário:", parsed.username)
print("Host:", parsed.hostname)
print("Porta:", parsed.port)
print("Banco:", parsed.path)

engine = create_engine(DATABASE_URL)

with engine.connect() as connection:
    resultado = connection.execute(text("SELECT NOW();"))
    print("Conexão feita com sucesso!")
    print(resultado.fetchone())