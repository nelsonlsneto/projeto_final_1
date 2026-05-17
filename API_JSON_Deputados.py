# IMPORTS

import requests
import pandas as pd

# Requisitando os dados de Deputados

url = 'https://dadosabertos.camara.leg.br/api/v2/deputados'

response = requests.get(url, timeout = 15)

if response.status_code == 200:
    print("A requisição deu certo!")
    df = pd.DataFrame([response])

    df

else:
    print("A requisição não deu certo  :(")