import requests
from bs4 import BeautifulSoup
import json
import os
import unicodedata

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

URL_TJMA = "https://www.tjma.jus.br/primeiro-grau/cgj/serventias"
ARQUIVO_JSON = "memoria_tjma.json"

def enviar_alerta_telegram(mensagem):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Aviso: Credenciais do Telegram ausentes.")
        return
    
    url_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "HTML"}
    try:
        requests.post(url_api, json=payload)
    except Exception as e:
        print(f"Erro no Telegram: {e}")

def remover_acentos(txt):
    return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')

def extrair_dados_tjma():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    try:
        response = requests.get(URL_TJMA, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Erro de conexão: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    cartorios_extraidos = {}

    # TÁTICA DA REDE DE ARRASTO: Procura em todas as tags que costumam ter texto
    for bloco in soup.find_all(['li', 'div', 'p', 'td']):
        texto_bruto = bloco.get_text(separator=" | ", strip=True)
        texto_limpo = remover_acentos(texto_bruto.upper())
        
        # Filtro: Tem que mencionar a cidade e um tipo de serventia
        if "SAO LUIS" in texto_limpo and ("ZONA" in texto_limpo or "TABELIONATO" in texto_limpo or "OFICIO" in texto_limpo or "REGISTRO" in texto_limpo):
            # Limite para não pegar o texto da página inteira se for uma div gigante
            if 20 < len(texto_bruto) < 1500:
                chave = texto_limpo[:40] # Usa os primeiros caracteres como chave
                cartorios_extraidos[chave] = texto_bruto

    print(f"✅ Extração concluída: {len(cartorios_extraidos)} registros encontrados.")            
    
    # SISTEMA DE DIAGNÓSTICO: Se der 0, mostra o que o robô está "vendo"
    if len(cartorios_extraidos) == 0:
        print("\n--- 🚨 ALERTA: O ROBÔ NÃO ENCONTROU OS TEXTOS ---")
        print("Veja as primeiras 500 letras do HTML que o robô recebeu do TJMA:")
        texto_da_pagina = soup.get_text(separator=" ", strip=True)
        print(texto_da_pagina[:500])
        print("---------------------------------------------------\n")

    return cartorios_extraidos

def executar_monitoramento():
    print("Iniciando varredura no portal do TJMA...")
    dados_atuais_site = extrair_dados_tjma()
    
    if not dados_atuais_site:
        print("Falha na extração ou site vazio. Encerrando execução.")
        return

    dados_antigos = {}
    if os.path.exists(ARQUIVO_JSON):
        with open(ARQUIVO_JSON, 'r', encoding='utf-8') as arquivo:
            dados_antigos = json.load(arquivo)

    if dados_atuais_site != dados_antigos:
        print("🚨 Divergência encontrada! Os dados oficiais mudaram.")
        mensagem_alerta = "🚨 <b>Atualização no TJMA Detectada!</b>\n\nO robô detectou uma mudança na lista oficial de serventias. Acesse o GitHub para verificar."
        enviar_alerta_telegram(mensagem_alerta)
        
        with open(ARQUIVO_JSON, 'w', encoding='utf-8') as arquivo:
            json.dump(dados_atuais_site, arquivo, ensure_ascii=False, indent=4)
    else:
        print("✅ Tudo atualizado. Nenhuma alteração nos cartórios hoje.")

if __name__ == "__main__":
    executar_monitoramento()
