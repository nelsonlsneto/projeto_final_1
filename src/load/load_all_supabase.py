from load_deputados_supabase import main as carregar_deputados
from load_despesas_supabase import main as carregar_despesas


def main():
    print("Iniciando carga de deputados...")
    carregar_deputados()

    print("Iniciando carga de despesas...")
    carregar_despesas()

    print("Carga finalizada com sucesso.")


if __name__ == "__main__":
    main()