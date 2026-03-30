import requests
from bs4 import BeautifulSoup
import json
import os
import re

# ==============================================================================
# CONFIGURAÇÕES
# ==============================================================================
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# A URL exata que você estava inspecionando no print!
URL_TJMA = "https://www.tjma.jus.br/primeiro-grau/cgj/serventias"
ARQUIVO_JSON = "memoria_tjma.json"

def enviar_alerta_telegram(mensagem):
    """Envia uma notificação direta para o seu celular via Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Aviso: Credenciais do Telegram ausentes. Alerta não enviado.")
        return
    
    url_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
        "parse_mode": "HTML"
    }
    try:
        resposta = requests.post(url_api, json=payload)
        resposta.raise_for_status()
        print("📲 Alerta enviado com sucesso para o Telegram!")
    except Exception as e:
        print(f"Erro ao enviar alerta no Telegram: {e}")

def extrair_dados_tjma():
    """Acessa o site do TJMA e raspa as informações dos cartórios."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        print("Conectando ao portal do TJMA...")
        response = requests.get(URL_TJMA, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Erro de conexão com o site do TJMA: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    cartorios_extraidos = {}

    # Baseado no seu print: O TJMA usa ul com a classe 'general-link-list'
    # Vamos buscar todas as listas de cartórios na página
    listas_cartorios = soup.find_all('ul', class_='general-link-list')
    
    if not listas_cartorios:
        print("Aviso: A estrutura do site do TJMA mudou ou não carregou corretamente.")
        return None

    # Varre cada item (<li>) dentro dessas listas
    for lista in listas_cartorios:
        itens = lista.find_all('li')
        
        for item in itens:
            texto_bruto = item.get_text(separator=" | ", strip=True)
            
            # Filtro básico: Só queremos blocos que mencionem São Luís e sejam cartórios/zonas
            if "SÃO LUÍS" in texto_bruto.upper() and ("OFÍCIO" in texto_bruto.upper() or "ZONA" in texto_bruto.upper() or "TABELIONATO" in texto_bruto.upper()):
                
                # Pegamos o primeiro pedaço de texto forte (geralmente é o nome do cartório)
                # Como o HTML deles é uma mistureba, usamos o texto bruto como "assinatura" digital
                # Se qualquer vírgula desse texto mudar no TJMA, o robô vai apitar!
                
                assinatura_digital = texto_bruto[:100] # Usa os primeiros 100 caracteres como chave
                cartorios_extraidos[assinatura_digital] = texto_bruto

    print(f"✅ Extração concluída: {len(cartorios_extraidos)} registros de São Luís encontrados.")            
    return cartorios_extraidos

def executar_monitoramento():
    print("Iniciando varredura...")
    
    dados_atuais_site = extrair_dados_tjma()
    
    if not dados_atuais_site:
        print("Falha ao extrair dados de hoje. Encerrando execução.")
        return

    dados_antigos = {}
    if os.path.exists(ARQUIVO_JSON):
        with open(ARQUIVO_JSON, 'r', encoding='utf-8') as arquivo:
            dados_antigos = json.load(arquivo)

    # Compara se houve alguma alteração (nova adição, exclusão ou mudança de telefone/endereço)
    if dados_atuais_site != dados_antigos:
        print("🚨 Divergência encontrada! Os dados oficiais mudaram.")
        
        mensagem_alerta = (
            "🚨 <b>Atualização no TJMA Detectada!</b>\n\n"
            "O robô de monitoramento detectou uma mudança nos dados da página oficial de serventias (endereço, telefone ou titular mudou).\n\n"
            "Acesse o repositório do Guia para conferir o que mudou e atualizar o HTML."
        )
        enviar_alerta_telegram(mensagem_alerta)
        
        # Atualiza a memória do robô
        with open(ARQUIVO_JSON, 'w', encoding='utf-8') as arquivo:
            json.dump(dados_atuais_site, arquivo, ensure_ascii=False, indent=4)
    else:
        print("✅ Dados verificados. Nenhuma alteração nos cartórios hoje.")

if __name__ == "__main__":
    executar_monitoramento()
