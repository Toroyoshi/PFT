# import psycopg2
# import time

# class DatabaseHandler:
#     def __init__(self, host="localhost", db_name="antifurto_db", user="admin", password="123"):
#         """Inicializa as credenciais de rede e garante que a tabela existe no PostgreSQL."""
#         self.host = host
#         self.db_name = db_name
#         self.user = user
#         self.password = password
        
#         self._create_table()

#     def _get_connection(self):
#         """Cria uma nova ligação TCP/IP de forma dinâmica (Resiliência para Edge Computing)."""
#         return psycopg2.connect(
#             host=self.host,
#             database=self.db_name,
#             user=self.user,
#             password=self.password
#         )

#     def _create_table(self):
#         """Cria a tabela de alertas com a sintaxe nativa do PostgreSQL."""
#         conn = None
#         try:
#             conn = self._get_connection()
#             cursor = conn.cursor()
#             # ALTERAÇÃO 1: AUTOINCREMENT passa a SERIAL.
#             # ALTERAÇÃO 2: Timestamp com geração automática delegada ao motor.
#             cursor.execute('''
#                 CREATE TABLE IF NOT EXISTS alertas (
#                     id SERIAL PRIMARY KEY,
#                     timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                     track_id INTEGER,
#                     tipo_alerta VARCHAR(50),
#                     confianca REAL
#                 )
#             ''')
#             conn.commit()
#             cursor.close()
#         except Exception as e:
#             print(f"[ERRO POSTGRES] Falha na inicialização da tabela: {e}")
#         finally:
#             if conn:
#                 conn.close()

#     def salvar_alerta(self, track_id, tipo_alerta, confianca):
#         """Insere um novo alerta na base de dados distribuída."""
#         conn = None
#         try:
#             conn = self._get_connection()
#             cursor = conn.cursor()
            
#             # ALTERAÇÃO 3: Marcadores passam de '?' para '%s'. 
#             # Ocultámos o timestamp, o Postgres trata disso sozinho.
#             cursor.execute('''
#                 INSERT INTO alertas (track_id, tipo_alerta, confianca)
#                 VALUES (%s, %s, %s)
#             ''', (int(track_id), tipo_alerta, round(confianca, 2)))
            
#             conn.commit()
#             cursor.close()
#             return True
#         except Exception as e:
#             print(f"[ERRO POSTGRES] Falha ao salvar (Câmara isolada?): {e}")
#             return False
#         finally:
#             if conn:
#                 conn.close()

import sqlite3
import os

# Força o caminho absoluto para o SQLite
DIR_ATUAL = os.path.dirname(os.path.abspath(__file__))
# Recua uma pasta se o db_manager estiver dentro da pasta Alertas
PASTA_EDGE = os.path.dirname(DIR_ATUAL) 
DB_PATH = os.path.join(PASTA_EDGE, "alertas_oficial.db")

class DatabaseHandler:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.cursor = self.conn.cursor()
        # Garante que a tabela tem a flag de sincronização
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS alertas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_id INTEGER,
                tipo_alerta TEXT,
                confianca REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                sincronizado INTEGER DEFAULT 0
            )
        """)
        self.conn.commit()

    def inserir_alerta(self, track_id, tipo_alerta, confianca):
        self.cursor.execute("""
            INSERT INTO alertas (track_id, tipo_alerta, confianca, sincronizado) 
            VALUES (?, ?, ?, 0)
        """, (track_id, tipo_alerta, confianca))
        self.conn.commit()
    def _create_table(self):
        """Cria a tabela de alertas com a sintaxe nativa do PostgreSQL."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            # ALTERAÇÃO 1: AUTOINCREMENT passa a SERIAL.
            # ALTERAÇÃO 2: Timestamp com geração automática delegada ao motor.
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alertas (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    track_id INTEGER,
                    tipo_alerta VARCHAR(50),
                    confianca REAL
                )
            ''')
            conn.commit()
            cursor.close()
        except Exception as e:
            print(f"[ERRO POSTGRES] Falha na inicialização da tabela: {e}")
        finally:
            if conn:
                conn.close()

    def salvar_alerta(self, track_id, tipo_alerta, confianca):
        """Insere um novo alerta na base de dados distribuída."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # ALTERAÇÃO 3: Marcadores passam de '?' para '%s'. 
            # Ocultámos o timestamp, o Postgres trata disso sozinho.
            cursor.execute('''
                INSERT INTO alertas (track_id, tipo_alerta, confianca)
                VALUES (%s, %s, %s)
            ''', (int(track_id), tipo_alerta, round(confianca, 2)))
            
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            print(f"[ERRO POSTGRES] Falha ao salvar (Câmara isolada?): {e}")
            return False
        finally:
            if conn:
                conn.close()