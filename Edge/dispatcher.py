import sqlite3
import requests
import time
from datetime import datetime
import os

# ==============================================================================
# CONFIGURAÇÃO DE ARQUITETURA: OFFLINE-FIRST
# ==============================================================================

# 1. Caminho absoluto imutável. Garante que o Python nunca se perde nas pastas
DIR_ATUAL = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DIR_ATUAL, "Alertas", "alertas_oficial.db")

# 2. A API do teu cluster local (para onde enviamos os JSONs)
API_URL = "http://localhost:8000/api/alertas/sincronizar"

API_METRICAS_URL = "http://localhost:8000/api/metricas/registar"

def iniciar_dispatcher():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [DISPATCHER] Iniciado. A garantir Consistência Eventual...")
    print(f"[DISPATCHER] A escutar a base de dados local em: {DB_PATH}")

    while True:
        try:
            # Ligação feita DENTRO do loop. Se a câmara criar o ficheiro agora, ele deteta.
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row  
            cursor = conn.cursor()

            # 1. Procurar APENAS os alertas que ainda não foram para a Cloud
            cursor.execute("SELECT * FROM alertas WHERE sincronizado = 0")
            alertas_pendentes = cursor.fetchall()

            if alertas_pendentes:
                print(f"[DISPATCHER] {len(alertas_pendentes)} alertas pendentes na fila. A enviar para o cluster...")

                for alerta in alertas_pendentes:
                    # 2. Formatar o JSON para a API
                    payload = {
                        "track_id": alerta['track_id'],
                        "tipo_alerta": alerta['tipo_alerta'],
                        "confianca": alerta['confianca'],
                        "timestamp": alerta['timestamp']
                    }

                    # 3. Enviar para a API via POST (Timeout curto de 3s para não bloquear o script)
                    resposta = requests.post(API_URL, json=payload, timeout=3)

                    # 4. Validar o ACK (Acknowledge) da Cloud
                    if resposta.status_code == 200:
                        # Se o Postgres no Swarm gravou, atualizamos o SQLite local
                        cursor.execute("UPDATE alertas SET sincronizado = 1 WHERE id = ?", (alerta['id'],))
                        conn.commit()
                        print(f"[DISPATCHER] Sucesso: Alerta #{alerta['id']} promovido à Cloud.")
                    else:
                        print(f"[DISPATCHER] A API recusou o pacote (Status {resposta.status_code}). Abortando lote atual.")
                        break # Para o envio deste lote e tenta de novo na próxima ronda
            
            # --- PROCESSAMENTO DE MÉTRICAS ---
            cursor.execute("SELECT * FROM metricas WHERE sincronizado = 0")
            metricas_pendentes = cursor.fetchall()
            
            if metricas_pendentes:
                for metrica in metricas_pendentes:
                    payload_metrica = {
                        "node_id": metrica['node_id'],
                        "timestamp": metrica['timestamp'],
                        "fps": metrica['fps'],
                        "frame_count": metrica['frame_count'],
                        "detection_count": metrica['detection_count'],
                        "inference_calls": metrica['inference_calls'],
                        "average_inference_ms": metrica['average_inference_ms'],
                        "success_rate": metrica['success_rate'],
                        "uptime_seconds": metrica['uptime_seconds'],
                        "pessoas_detetadas": metrica['pessoas_detetadas']
                    }
                    
                    resp_metrica = requests.post(API_METRICAS_URL, json=payload_metrica, timeout=3)
                    
                    if resp_metrica.status_code == 200:
                        cursor.execute("UPDATE metricas SET sincronizado = 1 WHERE id = ?", (metrica['id'],))
                        conn.commit()
                        print(f"[DISPATCHER] Sucesso: Métrica #{metrica['id']} promovida à Cloud.")
                    else:
                        print(f"[DISPATCHER] API recusou métrica (Status {resp_metrica.status_code}).")
                        break # Para o envio deste lote de métricas e tenta de novo na próxima ronda
                    
            # Fechar a ligação para libertar o ficheiro
            conn.close()

        except requests.exceptions.RequestException:
            print("[DISPATCHER] ⚠️ Falha na Rede ou Cluster offline. A reter os dados no cofre local...")
        except sqlite3.OperationalError:
            print("[DISPATCHER] A aguardar a criação da tabela de alertas pela câmara...")
        except Exception as e:
            print(f"[DISPATCHER] Erro crítico isolado: {e}")

        # O Dispatcher "dorme" 5 segundos. Não consome CPU praticamente nenhum no Edge.
        time.sleep(5)

if __name__ == "__main__":
    iniciar_dispatcher()