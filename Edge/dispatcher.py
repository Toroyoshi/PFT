import sqlite3
import requests
import time
from datetime import datetime
import os

# Configurações de Arquitetura
# 1. Descobre a diretoria onde ESTE ficheiro Python (db_manager) está guardado
DIR_ATUAL = os.path.dirname(os.path.abspath(__file__))

# 2. Constrói o caminho absoluto chumbado para a base de dados
DB_PATH = os.path.join(DIR_ATUAL, "Alertas\database_manager.db")

API_URL = "http://localhost:8000/api/alertas/sincronizar"

def iniciar_dispatcher():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [DISPATCHER] Iniciado. A garantir Consistência Eventual...")
    
    # Ligação ao SQLite local
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Permite aceder às colunas por nome
    cursor = conn.cursor()

    while True:
        try:
            # 1. Procurar APENAS os alertas que ainda não foram para a Cloud
            cursor.execute("SELECT * FROM alertas WHERE sincronizado = 0")
            alertas_pendentes = cursor.fetchall()

            if alertas_pendentes:
                print(f"[DISPATCHER] {len(alertas_pendentes)} alertas pendentes na fila. A enviar para o cluster...")

                for alerta in alertas_pendentes:
                    # 2. Formatar o JSON
                    payload = {
                        "track_id": alerta['track_id'],
                        "tipo_alerta": alerta['tipo_alerta'],
                        "confianca": alerta['confianca'],
                        "timestamp": alerta['timestamp']
                    }

                    # 3. Enviar para a API via POST (Timeout curto para não bloquear)
                    resposta = requests.post(API_URL, json=payload, timeout=3)

                    # 4. Validar o ACK (Acknowledge) da Cloud
                    if resposta.status_code == 200:
                        # Se o Postgres gravou, atualizamos o SQLite local
                        cursor.execute("UPDATE alertas SET sincronizado = 1 WHERE id = ?", (alerta['id'],))
                        conn.commit()
                        print(f"[DISPATCHER] Sucesso: Alerta #{alerta['id']} promovido à Cloud.")
                    else:
                        print(f"[DISPATCHER] A API recusou o pacote (Status {resposta.status_code}). Abortando lote.")
                        break # Para o loop e tenta na próxima ronda

        except requests.exceptions.RequestException:
            print("[DISPATCHER] ⚠️ Falha na Rede ou Cluster offline. A reter os dados no cofre local...")
        except sqlite3.OperationalError:
            print("[DISPATCHER] A aguardar a criação da base de dados pelo detetor de vídeo...")
        except Exception as e:
            print(f"[DISPATCHER] Erro crítico isolado: {e}")

        # O Dispatcher "dorme" 5 segundos para não consumir CPU do Edge
        time.sleep(5)

if __name__ == "__main__":
    iniciar_dispatcher()