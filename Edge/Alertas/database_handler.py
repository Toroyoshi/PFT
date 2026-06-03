import sqlite3
import os
from datetime import datetime

# ==============================================================================
# CONFIGURAÇÃO DE ARQUITETURA: OFFLINE-FIRST
# ==============================================================================

# 1. Descobre a diretoria onde ESTE ficheiro Python (database_handler.py) está guardado
DIR_ATUAL = os.path.dirname(os.path.abspath(__file__))

# 2. Constrói o caminho absoluto para o cofre local
# Tem de ser EXATAMENTE o mesmo ficheiro lido pelo dispatcher.py
DB_PATH = os.path.join(DIR_ATUAL, "alertas_oficial.db")

class DatabaseHandler:
    def __init__(self):
        """Inicializa a ligação e garante que a tabela base existe no arranque da câmara."""
        # Print silencioso para saberes exatamente onde o ficheiro está a ser criado
        print(f"[SQLITE] A montar o cofre local no Edge em: {DB_PATH}")
        self._criar_tabela_se_nao_existir()

    def _criar_tabela_se_nao_existir(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Tabela de Alertas (Furtos)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alertas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    track_id INTEGER,
                    tipo_alerta TEXT,
                    confianca REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    sincronizado INTEGER DEFAULT 0 
                )
            """)
            
            # NOVA Tabela de Métricas (FPS, Pessoas, etc)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metricas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id TEXT,
                    timestamp REAL,
                    fps REAL,
                    frame_count INTEGER,
                    detection_count INTEGER,
                    inference_calls INTEGER,
                    average_inference_ms REAL,
                    success_rate REAL,
                    uptime_seconds REAL,
                    pessoas_detetadas INTEGER,
                    sincronizado INTEGER DEFAULT 0
                )
            """)
            conn.commit()
        except Exception as e:
            print(f"[ERRO SQLITE] Falha na montagem da infraestrutura local: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

    # ADICIONA ESTA NOVA FUNÇÃO ABAIXO DE "salvar_alerta"
    def salvar_metrica(self, metrica_data):
        try:
            conn = sqlite3.connect(DB_PATH, timeout=5.0)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO metricas (
                    node_id, timestamp, fps, frame_count, detection_count, 
                    inference_calls, average_inference_ms, success_rate, 
                    uptime_seconds, pessoas_detetadas, sincronizado
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                metrica_data['node_id'], metrica_data['timestamp'], metrica_data['fps'],
                metrica_data['frame_count'], metrica_data['detection_count'],
                metrica_data['inference_calls'], metrica_data['average_inference_ms'],
                metrica_data['success_rate'], metrica_data['uptime_seconds'],
                metrica_data['pessoas_detetadas']
            ))
            conn.commit()
        except Exception as e:
            print(f"[ERRO SQLITE] Falha ao escrever métrica no disco: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

    def salvar_alerta(self, track_id, tipo_alerta, confianca):
        """
        Invocado pelo orchestrator.py quando ocorre um furto.
        Guarda no disco instantaneamente e liberta o ficheiro para o Dispatcher.
        """
        try:
            # Ligação "Fire and Forget": Abre, escreve e fecha no milissegundo seguinte
            conn = sqlite3.connect(DB_PATH, timeout=5.0) # Espera até 5s se o Dispatcher estiver a ler
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO alertas (track_id, tipo_alerta, confianca, sincronizado) 
                VALUES (?, ?, ?, 0)
            """, (track_id, tipo_alerta, confianca))
            
            conn.commit()
            
            # Avisa no terminal que a gravação local foi um sucesso (sem erros vermelhos do Postgres)
            print(f"[SQLITE] Alerta guardado localmente: {tipo_alerta} (ID: {track_id}) -> Na fila do Dispatcher.")
            
        except sqlite3.OperationalError as e:
            print(f"[ERRO SQLITE] Ficheiro trancado ou inacessível: {e}")
        except Exception as e:
            print(f"[ERRO SQLITE CRÍTICO] Falha ao escrever alerta no disco: {e}")
        finally:
            if 'conn' in locals():
                conn.close()