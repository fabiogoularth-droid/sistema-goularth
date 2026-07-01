# -*- coding: utf-8 -*-
"""
BANCO DE DADOS — Sistema Goularth de Torneios
=================================================
"""

import sqlite3
import hashlib
import secrets
import datetime
import random
import os
import shutil
from contextlib import contextmanager

import regras

CAMINHO_BANCO_PADRAO = "clube.db"

# Tenta importar psycopg2 para PostgreSQL
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
    print("✅ psycopg2 disponível para PostgreSQL")
except Exception as e:
    PSYCOPG2_AVAILABLE = False
    print("=" * 60)
    print("ERRO AO IMPORTAR psycopg2")
    print(type(e).__name__)
    print(str(e))
    print("=" * 60)


def _hash_senha(senha, sal=None):
    if sal is None:
        sal = secrets.token_hex(16)
    hash_resultado = hashlib.pbkdf2_hmac(
        "sha256", senha.encode("utf-8"), sal.encode("utf-8"), 200_000
    )
    return f"{sal}${hash_resultado.hex()}"


def _verificar_senha(senha, hash_armazenado):
    try:
        sal, _ = hash_armazenado.split("$")
    except ValueError:
        return False
    return _hash_senha(senha, sal) == hash_armazenado


class BancoClube:
    def __init__(self, caminho_banco=CAMINHO_BANCO_PADRAO):
        self.caminho_banco = caminho_banco
        
        # Verifica se deve usar PostgreSQL
        self.db_url = os.environ.get("DATABASE_URL")
        self.usar_postgres = self.db_url is not None and PSYCOPG2_AVAILABLE
        
        if self.usar_postgres:
            print("🐘 Conectando ao PostgreSQL...")
            self._criar_tabelas_postgres()
            self._criar_admin_inicial_postgres()
            self._migrar_sqlite_para_postgres()
        else:
            print("💾 Usando SQLite...")
            self._criar_tabelas()
            self._criar_admin_inicial()
            self._migrar_banco()

    @contextmanager
    def _conexao(self):
        if self.usar_postgres:
            try:
                conn = psycopg2.connect(self.db_url)
                try:
                    yield conn
                    conn.commit()
                finally:
                    conn.close()
            except Exception as e:
                print(f"❌ Erro PostgreSQL: {e}")
                raise
        else:
            conn = sqlite3.connect(self.caminho_banco)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()

    def _criar_tabelas_postgres(self):
        """Cria tabelas no PostgreSQL."""
        with self._conexao() as conn:
            cur = conn.cursor()
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS socios (
                    id SERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    cpf TEXT NOT NULL UNIQUE,
                    nascimento TEXT,
                    sexo TEXT,
                    criatorio TEXT,
                    sigla_clube TEXT NOT NULL,
                    numero_socio TEXT NOT NULL,
                    codigo_socio TEXT NOT NULL UNIQUE,
                    cep TEXT,
                    endereco TEXT,
                    numero TEXT,
                    complemento TEXT,
                    bairro TEXT,
                    cidade TEXT,
                    uf TEXT,
                    pais TEXT,
                    ddi TEXT,
                    ddd TEXT,
                    celular TEXT,
                    whatsapp TEXT,
                    email TEXT,
                    facebook TEXT,
                    instagram TEXT,
                    youtube TEXT,
                    exibir_dados INTEGER DEFAULT 0,
                    senha_hash TEXT NOT NULL,
                    criado_em TEXT NOT NULL
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS passaros (
                    id SERIAL PRIMARY KEY,
                    socio_id INTEGER NOT NULL REFERENCES socios(id),
                    nome TEXT NOT NULL,
                    sigla_criador TEXT NOT NULL,
                    numero_anilha TEXT NOT NULL,
                    ano_anilha TEXT NOT NULL,
                    codigo_ave TEXT NOT NULL UNIQUE,
                    criado_em TEXT NOT NULL
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS passaros_edicoes (
                    id SERIAL PRIMARY KEY,
                    passaro_id INTEGER NOT NULL REFERENCES passaros(id),
                    socio_id INTEGER NOT NULL REFERENCES socios(id),
                    nome TEXT NOT NULL,
                    sigla_criador TEXT NOT NULL,
                    numero_anilha TEXT NOT NULL,
                    ano_anilha TEXT NOT NULL,
                    status TEXT DEFAULT 'pendente',
                    criado_em TEXT NOT NULL
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS torneios (
                    id SERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    endereco TEXT,
                    mapa_url TEXT,
                    criado_em TEXT NOT NULL
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS etapas (
                    id SERIAL PRIMARY KEY,
                    torneio_id INTEGER REFERENCES torneios(id),
                    nome TEXT NOT NULL,
                    modalidade TEXT NOT NULL,
                    categoria TEXT NOT NULL,
                    data_etapa TEXT NOT NULL,
                    prazo_inscricao TEXT,
                    limite_por_cpf INTEGER,
                    limite_inscricoes INTEGER,
                    inscricoes_abertas INTEGER DEFAULT 1,
                    ordem_sorteada INTEGER DEFAULT 0,
                    info_pagamento TEXT,
                    prazo_pagamento TEXT,
                    criado_em TEXT NOT NULL
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS inscricoes (
                    id SERIAL PRIMARY KEY,
                    etapa_id INTEGER NOT NULL REFERENCES etapas(id),
                    passaro_id INTEGER NOT NULL REFERENCES passaros(id),
                    ordem INTEGER,
                    liberada_manual INTEGER DEFAULT 0,
                    pagamento_confirmado INTEGER DEFAULT 0,
                    criado_em TEXT NOT NULL,
                    UNIQUE (etapa_id, passaro_id)
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS resultados (
                    id SERIAL PRIMARY KEY,
                    inscricao_id INTEGER NOT NULL REFERENCES inscricoes(id),
                    nota1 REAL,
                    nota2 REAL,
                    nota3 REAL,
                    nota4 REAL,
                    nota5 REAL,
                    media REAL,
                    classificacao INTEGER,
                    criado_em TEXT NOT NULL,
                    UNIQUE (inscricao_id)
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ranking_geral (
                    id SERIAL PRIMARY KEY,
                    socio_id INTEGER NOT NULL REFERENCES socios(id),
                    passaro_id INTEGER NOT NULL REFERENCES passaros(id),
                    etapa_id INTEGER NOT NULL REFERENCES etapas(id),
                    pontos INTEGER DEFAULT 0,
                    classificacao INTEGER,
                    criado_em TEXT NOT NULL
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS pagamentos (
                    id SERIAL PRIMARY KEY,
                    inscricao_id INTEGER NOT NULL REFERENCES inscricoes(id),
                    comprovante TEXT,
                    status TEXT DEFAULT 'pendente',
                    data_pagamento TEXT,
                    criado_em TEXT NOT NULL
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS admin (
                    id SERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    senha_hash TEXT NOT NULL,
                    nivel INTEGER DEFAULT 2,
                    criado_em TEXT NOT NULL
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS resultados_importados (
                    id SERIAL PRIMARY KEY,
                    torneio_nome TEXT NOT NULL,
                    categoria TEXT NOT NULL,
                    data_etapa TEXT NOT NULL,
                    posicao INTEGER NOT NULL,
                    passaro_nome TEXT NOT NULL,
                    anilha TEXT NOT NULL,
                    proprietario TEXT NOT NULL,
                    tempo TEXT,
                    pontos INTEGER DEFAULT 0,
                    criado_em TEXT NOT NULL
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS transferencias (
                    id SERIAL PRIMARY KEY,
                    passaro_id INTEGER NOT NULL REFERENCES passaros(id),
                    socio_origem_id INTEGER NOT NULL REFERENCES socios(id),
                    socio_destino_id INTEGER NOT NULL REFERENCES socios(id),
                    cpf_destino TEXT NOT NULL,
                    status TEXT DEFAULT 'pendente',
                    criado_em TEXT NOT NULL
                )
            """)
            
            print("✅ Tabelas PostgreSQL criadas/verificadas")

    def _criar_admin_inicial_postgres(self):
        """Cria admin inicial no PostgreSQL."""
        with self._conexao() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM admin LIMIT 1")
            existe = cur.fetchone()
            
            if not existe:
                senha_hash = _hash_senha("admin123")
                cur.execute(
                    "INSERT INTO admin (nome, email, senha_hash, nivel, criado_em) VALUES (%s, %s, %s, %s, %s)",
                    ("Administrador", "admin@clube.com", senha_hash, 1, datetime.datetime.now().isoformat())
                )
                print("✅ Admin inicial criado no PostgreSQL")

    def _migrar_sqlite_para_postgres(self):
        """Migra dados do SQLite para PostgreSQL se existir."""
        if not os.path.exists(self.caminho_banco):
            print("ℹ️ Nenhum banco SQLite para migrar")
            return
        
        with self._conexao() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM socios")
            total = cur.fetchone()
            
            if total and total[0] > 0:
                print(f"ℹ️ PostgreSQL já tem {total[0]} sócios. Pulando migração.")
                return
        
        print("🔄 Iniciando migração do SQLite para PostgreSQL...")
        
        try:
            sqlite_conn = sqlite3.connect(self.caminho_banco)
            sqlite_conn.row_factory = sqlite3.Row
            
            tabelas = [
                'socios', 'passaros', 'passaros_edicoes', 'torneios', 
                'etapas', 'inscricoes', 'resultados', 'ranking_geral',
                'pagamentos', 'admin', 'resultados_importados', 'transferencias'
            ]
            
            with self._conexao() as pg_conn:
                cur = pg_conn.cursor()
                cur.execute("SET session_replication_role = replica;")
                
                for tabela in tabelas:
                    sqlite_cur = sqlite_conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                        (tabela,)
                    )
                    if not sqlite_cur.fetchone():
                        print(f"⚠️ Tabela {tabela} não existe no SQLite. Pulando.")
                        continue
                    
                    rows = sqlite_conn.execute(f"SELECT * FROM {tabela}").fetchall()
                    if not rows:
                        print(f"ℹ️ Tabela {tabela} vazia. Pulando.")
                        continue
                    
                    colunas = [desc[0] for desc in sqlite_conn.execute(f"SELECT * FROM {tabela}").description]
                    placeholders = ','.join(['%s'] * len(colunas))
                    colunas_str = ','.join(colunas)
                    
                    for row in rows:
                        valores = [row[col] for col in colunas]
                        cur.execute(
                            f"INSERT INTO {tabela} ({colunas_str}) VALUES ({placeholders})",
                            valores
                        )
                    
                    print(f"✅ {len(rows)} registros migrados da tabela {tabela}")
                
                cur.execute("SET session_replication_role = DEFAULT;")
            
            sqlite_conn.close()
            print("🎉 Migração concluída com sucesso!")
            
        except Exception as e:
            print(f"❌ Erro na migração: {e}")
            raise

    def _criar_tabelas(self):
        """Cria tabelas no SQLite."""
        with self._conexao() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS socios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    cpf TEXT NOT NULL UNIQUE,
                    nascimento TEXT,
                    sexo TEXT,
                    criatorio TEXT,
                    sigla_clube TEXT NOT NULL,
                    numero_socio TEXT NOT NULL,
                    codigo_socio TEXT NOT NULL UNIQUE,
                    cep TEXT,
                    endereco TEXT,
                    numero TEXT,
                    complemento TEXT,
                    bairro TEXT,
                    cidade TEXT,
                    uf TEXT,
                    pais TEXT,
                    ddi TEXT,
                    ddd TEXT,
                    celular TEXT,
                    whatsapp TEXT,
                    email TEXT,
                    facebook TEXT,
                    instagram TEXT,
                    youtube TEXT,
                    exibir_dados INTEGER DEFAULT 0,
                    senha_hash TEXT NOT NULL,
                    criado_em TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS passaros (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    socio_id INTEGER NOT NULL,
                    nome TEXT NOT NULL,
                    sigla_criador TEXT NOT NULL,
                    numero_anilha TEXT NOT NULL,
                    ano_anilha TEXT NOT NULL,
                    codigo_ave TEXT NOT NULL UNIQUE,
                    criado_em TEXT NOT NULL,
                    FOREIGN KEY (socio_id) REFERENCES socios(id)
                );

                CREATE TABLE IF NOT EXISTS passaros_edicoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    passaro_id INTEGER NOT NULL,
                    socio_id INTEGER NOT NULL,
                    nome TEXT NOT NULL,
                    sigla_criador TEXT NOT NULL,
                    numero_anilha TEXT NOT NULL,
                    ano_anilha TEXT NOT NULL,
                    status TEXT DEFAULT 'pendente',
                    criado_em TEXT NOT NULL,
                    FOREIGN KEY (passaro_id) REFERENCES passaros(id),
                    FOREIGN KEY (socio_id) REFERENCES socios(id)
                );

                CREATE TABLE IF NOT EXISTS torneios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    endereco TEXT,
                    mapa_url TEXT,
                    criado_em TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS etapas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    torneio_id INTEGER,
                    nome TEXT NOT NULL,
                    modalidade TEXT NOT NULL,
                    categoria TEXT NOT NULL,
                    data_etapa TEXT NOT NULL,
                    prazo_inscricao TEXT,
                    limite_por_cpf INTEGER,
                    limite_inscricoes INTEGER,
                    inscricoes_abertas INTEGER DEFAULT 1,
                    ordem_sorteada INTEGER DEFAULT 0,
                    info_pagamento TEXT,
                    prazo_pagamento TEXT,
                    criado_em TEXT NOT NULL,
                    FOREIGN KEY (torneio_id) REFERENCES torneios(id)
                );

                CREATE TABLE IF NOT EXISTS inscricoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    etapa_id INTEGER NOT NULL,
                    passaro_id INTEGER NOT NULL,
                    ordem INTEGER,
                    liberada_manual INTEGER DEFAULT 0,
                    pagamento_confirmado INTEGER DEFAULT 0,
                    criado_em TEXT NOT NULL,
                    FOREIGN KEY (etapa_id) REFERENCES etapas(id),
                    FOREIGN KEY (passaro_id) REFERENCES passaros(id),
                    UNIQUE (etapa_id, passaro_id)
                );

                CREATE TABLE IF NOT EXISTS resultados (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    inscricao_id INTEGER NOT NULL,
                    nota1 REAL,
                    nota2 REAL,
                    nota3 REAL,
                    nota4 REAL,
                    nota5 REAL,
                    media REAL,
                    classificacao INTEGER,
                    criado_em TEXT NOT NULL,
                    FOREIGN KEY (inscricao_id) REFERENCES inscricoes(id),
                    UNIQUE (inscricao_id)
                );

                CREATE TABLE IF NOT EXISTS ranking_geral (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    socio_id INTEGER NOT NULL,
                    passaro_id INTEGER NOT NULL,
                    etapa_id INTEGER NOT NULL,
                    pontos INTEGER DEFAULT 0,
                    classificacao INTEGER,
                    criado_em TEXT NOT NULL,
                    FOREIGN KEY (socio_id) REFERENCES socios(id),
                    FOREIGN KEY (passaro_id) REFERENCES passaros(id),
                    FOREIGN KEY (etapa_id) REFERENCES etapas(id)
                );

                CREATE TABLE IF NOT EXISTS pagamentos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    inscricao_id INTEGER NOT NULL,
                    comprovante TEXT,
                    status TEXT DEFAULT 'pendente',
                    data_pagamento TEXT,
                    criado_em TEXT NOT NULL,
                    FOREIGN KEY (inscricao_id) REFERENCES inscricoes(id)
                );

                CREATE TABLE IF NOT EXISTS admin (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    senha_hash TEXT NOT NULL,
                    nivel INTEGER DEFAULT 2,
                    criado_em TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS resultados_importados (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    torneio_nome TEXT NOT NULL,
                    categoria TEXT NOT NULL,
                    data_etapa TEXT NOT NULL,
                    posicao INTEGER NOT NULL,
                    passaro_nome TEXT NOT NULL,
                    anilha TEXT NOT NULL,
                    proprietario TEXT NOT NULL,
                    tempo TEXT,
                    pontos INTEGER DEFAULT 0,
                    criado_em TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS transferencias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    passaro_id INTEGER NOT NULL,
                    socio_origem_id INTEGER NOT NULL,
                    socio_destino_id INTEGER NOT NULL,
                    cpf_destino TEXT NOT NULL,
                    status TEXT DEFAULT 'pendente',
                    criado_em TEXT NOT NULL,
                    FOREIGN KEY (passaro_id) REFERENCES passaros(id),
                    FOREIGN KEY (socio_origem_id) REFERENCES socios(id),
                    FOREIGN KEY (socio_destino_id) REFERENCES socios(id)
                );
            """)

    def _criar_admin_inicial(self):
        """Cria admin inicial no SQLite."""
        with self._conexao() as conn:
            existe = conn.execute("SELECT id FROM admin LIMIT 1").fetchone()
            if not existe:
                senha_hash = _hash_senha("admin123")
                conn.execute(
                    "INSERT INTO admin (nome, email, senha_hash, nivel, criado_em) VALUES (?, ?, ?, 1, ?)",
                    ("Administrador", "admin@clube.com", senha_hash, datetime.datetime.now().isoformat())
                )

    def _migrar_banco(self):
        """Migração para SQLite - adiciona colunas faltantes."""
        try:
            with self._conexao() as conn:
                colunas = conn.execute("PRAGMA table_info(socios)").fetchall()
                colunas_existentes = [c["name"] for c in colunas]
                
                if "criatorio" not in colunas_existentes:
                    conn.execute("ALTER TABLE socios ADD COLUMN criatorio TEXT")
                    print("✅ Coluna 'criatorio' adicionada com sucesso!")
                
                if "youtube" not in colunas_existentes:
                    conn.execute("ALTER TABLE socios ADD COLUMN youtube TEXT")
                    print("✅ Coluna 'youtube' adicionada com sucesso!")
                
                if "facebook" not in colunas_existentes:
                    conn.execute("ALTER TABLE socios ADD COLUMN facebook TEXT")
                    print("✅ Coluna 'facebook' adicionada com sucesso!")
                
                if "instagram" not in colunas_existentes:
                    conn.execute("ALTER TABLE socios ADD COLUMN instagram TEXT")
                    print("✅ Coluna 'instagram' adicionada com sucesso!")
        except Exception as e:
            print(f"❌ Erro na migração: {e}")

    # ================================================================
    # BACKUP
    # ================================================================
    def fazer_backup(self):
        try:
            import base64
            if not os.path.exists(self.caminho_banco):
                return False
            with open(self.caminho_banco, 'rb') as f:
                dados = f.read()
            dados_codificados = base64.b64encode(dados).decode('utf-8')
            with open("backup_database.txt", 'w') as f:
                f.write(dados_codificados)
            print("✅ Backup criado")
            return True
        except Exception as e:
            print(f"❌ Erro no backup: {e}")
            return False

    def restaurar_backup(self):
        try:
            import base64
            if not os.path.exists("backup_database.txt"):
                return False
            with open("backup_database.txt", 'r') as f:
                dados_codificados = f.read()
            dados = base64.b64decode(dados_codificados)
            with open(self.caminho_banco, 'wb') as f:
                f.write(dados)
            print("✅ Backup restaurado")
            return True
        except Exception as e:
            print(f"❌ Erro ao restaurar: {e}")
            return False

    # ================================================================
    # ADMIN
    # ================================================================
    def obter_admin(self, admin_id):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("SELECT * FROM admin WHERE id = %s", (admin_id,))
                linha = cur.fetchone()
            else:
                linha = conn.execute("SELECT * FROM admin WHERE id = ?", (admin_id,)).fetchone()
            return dict(linha) if linha else None

    def autenticar_admin(self, email, senha):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("SELECT * FROM admin WHERE email = %s", (email,))
                linha = cur.fetchone()
            else:
                linha = conn.execute("SELECT * FROM admin WHERE email = ?", (email,)).fetchone()
            
            if linha is None:
                return None
            if not _verificar_senha(senha, linha["senha_hash"]):
                return None
            return dict(linha)

    def trocar_senha_admin(self, admin_id, nova_senha):
        if len(nova_senha) < 6:
            raise regras.ErroValidacao("Senha deve ter pelo menos 6 caracteres.")
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute(
                    "UPDATE admin SET senha_hash = %s WHERE id = %s",
                    (_hash_senha(nova_senha), admin_id)
                )
            else:
                conn.execute(
                    "UPDATE admin SET senha_hash = ? WHERE id = ?",
                    (_hash_senha(nova_senha), admin_id)
                )

    def criar_admin(self, nome, email, senha, nivel=2):
        if not nome or not email or not senha:
            raise regras.ErroValidacao("Todos os campos são obrigatórios.")
        if len(senha) < 6:
            raise regras.ErroValidacao("Senha deve ter pelo menos 6 caracteres.")
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute("SELECT id FROM admin WHERE email = %s", (email,))
                existe = cur.fetchone()
                if existe:
                    raise ValueError("Já existe um administrador com este email.")
                cur.execute(
                    "INSERT INTO admin (nome, email, senha_hash, nivel, criado_em) VALUES (%s, %s, %s, %s, %s)",
                    (nome, email, _hash_senha(senha), nivel, datetime.datetime.now().isoformat())
                )
            else:
                existe = conn.execute("SELECT id FROM admin WHERE email = ?", (email,)).fetchone()
                if existe:
                    raise ValueError("Já existe um administrador com este email.")
                conn.execute(
                    "INSERT INTO admin (nome, email, senha_hash, nivel, criado_em) VALUES (?, ?, ?, ?, ?)",
                    (nome, email, _hash_senha(senha), nivel, datetime.datetime.now().isoformat())
                )

    def listar_admins(self):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("SELECT id, nome, email, nivel, criado_em FROM admin ORDER BY nivel")
                linhas = cur.fetchall()
            else:
                linhas = conn.execute("SELECT id, nome, email, nivel, criado_em FROM admin ORDER BY nivel").fetchall()
            return [dict(l) for l in linhas]

    def excluir_admin(self, admin_id):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute("SELECT nivel FROM admin WHERE id = %s", (admin_id,))
                admin = cur.fetchone()
                if admin and admin["nivel"] == 1:
                    raise ValueError("Não é possível excluir o Super Administrador.")
                cur.execute("DELETE FROM admin WHERE id = %s", (admin_id,))
            else:
                admin = conn.execute("SELECT nivel FROM admin WHERE id = ?", (admin_id,)).fetchone()
                if admin and admin["nivel"] == 1:
                    raise ValueError("Não é possível excluir o Super Administrador.")
                conn.execute("DELETE FROM admin WHERE id = ?", (admin_id,))

    def alterar_nivel_admin(self, admin_id, novo_nivel, admin_requisitante_id):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute("SELECT nivel FROM admin WHERE id = %s", (admin_requisitante_id,))
                requisitante = cur.fetchone()
                if not requisitante or requisitante["nivel"] != 1:
                    raise ValueError("Apenas Super Administradores podem alterar níveis.")
                
                if admin_id == admin_requisitante_id:
                    raise ValueError("Não é possível alterar seu próprio nível.")
                
                cur.execute("SELECT nivel FROM admin WHERE id = %s", (admin_id,))
                admin = cur.fetchone()
                if not admin:
                    raise ValueError("Administrador não encontrado.")
                if admin["nivel"] == 1:
                    raise ValueError("Não é possível alterar o nível do Super Administrador.")
                
                cur.execute("UPDATE admin SET nivel = %s WHERE id = %s", (novo_nivel, admin_id))
            else:
                requisitante = conn.execute("SELECT nivel FROM admin WHERE id = ?", (admin_requisitante_id,)).fetchone()
                if not requisitante or requisitante["nivel"] != 1:
                    raise ValueError("Apenas Super Administradores podem alterar níveis.")
                
                if admin_id == admin_requisitante_id:
                    raise ValueError("Não é possível alterar seu próprio nível.")
                
                admin = conn.execute("SELECT nivel FROM admin WHERE id = ?", (admin_id,)).fetchone()
                if not admin:
                    raise ValueError("Administrador não encontrado.")
                if admin["nivel"] == 1:
                    raise ValueError("Não é possível alterar o nível do Super Administrador.")
                
                conn.execute("UPDATE admin SET nivel = ? WHERE id = ?", (novo_nivel, admin_id))

    # ================================================================
    # TORNEIOS
    # ================================================================
    def criar_torneio(self, nome, endereco=None, mapa_url=None):
        if not nome:
            raise regras.ErroValidacao("Nome do torneio é obrigatório.")
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO torneios (nome, endereco, mapa_url, criado_em) VALUES (%s, %s, %s, %s) RETURNING id",
                    (nome.strip(), endereco, mapa_url, datetime.datetime.now().isoformat())
                )
                return cur.fetchone()[0]
            else:
                cursor = conn.execute(
                    "INSERT INTO torneios (nome, endereco, mapa_url, criado_em) VALUES (?, ?, ?, ?)",
                    (nome.strip(), endereco, mapa_url, datetime.datetime.now().isoformat())
                )
                return cursor.lastrowid

    def editar_torneio(self, torneio_id, nome, endereco=None, mapa_url=None):
        if not nome:
            raise regras.ErroValidacao("Nome do torneio é obrigatório.")
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute(
                    "UPDATE torneios SET nome = %s, endereco = %s, mapa_url = %s WHERE id = %s",
                    (nome.strip(), endereco, mapa_url, torneio_id)
                )
            else:
                conn.execute(
                    "UPDATE torneios SET nome = ?, endereco = ?, mapa_url = ? WHERE id = ?",
                    (nome.strip(), endereco, mapa_url, torneio_id)
                )

    def listar_torneios(self):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("SELECT * FROM torneios ORDER BY criado_em DESC")
                linhas = cur.fetchall()
            else:
                linhas = conn.execute("SELECT * FROM torneios ORDER BY criado_em DESC").fetchall()
            return [dict(l) for l in linhas]

    def obter_torneio(self, torneio_id):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("SELECT * FROM torneios WHERE id = %s", (torneio_id,))
                linha = cur.fetchone()
            else:
                linha = conn.execute("SELECT * FROM torneios WHERE id = ?", (torneio_id,)).fetchone()
            return dict(linha) if linha else None

    # ================================================================
    # ETAPAS
    # ================================================================
    def criar_etapa(self, torneio_id, nome, modalidade, categoria, data_etapa,
                     prazo_inscricao=None, limite_por_cpf=None, limite_inscricoes=None,
                     info_pagamento=None, prazo_pagamento=None):
        if not nome:
            raise regras.ErroValidacao("Nome da etapa é obrigatório.")
        
        modalidade_norm = regras.normalizar_modalidade(modalidade)
        categoria_norm = regras.normalizar_categoria(categoria)

        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO etapas (
                        torneio_id, nome, modalidade, categoria, data_etapa,
                        prazo_inscricao, limite_por_cpf, limite_inscricoes,
                        info_pagamento, prazo_pagamento,
                        inscricoes_abertas, criado_em
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s) RETURNING id
                """, (
                    torneio_id, nome.strip(), modalidade_norm, categoria_norm,
                    data_etapa, prazo_inscricao, limite_por_cpf, limite_inscricoes,
                    info_pagamento, prazo_pagamento,
                    datetime.datetime.now().isoformat()
                ))
                return cur.fetchone()[0]
            else:
                cursor = conn.execute("""
                    INSERT INTO etapas (
                        torneio_id, nome, modalidade, categoria, data_etapa,
                        prazo_inscricao, limite_por_cpf, limite_inscricoes,
                        info_pagamento, prazo_pagamento,
                        inscricoes_abertas, criado_em
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """, (
                    torneio_id, nome.strip(), modalidade_norm, categoria_norm,
                    data_etapa, prazo_inscricao, limite_por_cpf, limite_inscricoes,
                    info_pagamento, prazo_pagamento,
                    datetime.datetime.now().isoformat()
                ))
                return cursor.lastrowid

    def criar_festivo(self, nome, modalidade, categoria, data_etapa,
                        prazo_inscricao=None, limite_por_cpf=None, limite_inscricoes=None,
                        info_pagamento=None, prazo_pagamento=None):
        return self.criar_etapa(None, nome, modalidade, categoria, data_etapa,
                                prazo_inscricao, limite_por_cpf, limite_inscricoes,
                                info_pagamento, prazo_pagamento)

    def editar_etapa(self, etapa_id, nome, modalidade, categoria, data_etapa, 
                     prazo_inscricao, limite_por_cpf, limite_inscricoes,
                     info_pagamento=None, prazo_pagamento=None):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE etapas SET 
                        nome = %s, modalidade = %s, categoria = %s, 
                        data_etapa = %s, prazo_inscricao = %s, 
                        limite_por_cpf = %s, limite_inscricoes = %s,
                        info_pagamento = %s, prazo_pagamento = %s
                    WHERE id = %s
                """, (nome, modalidade, categoria, data_etapa, prazo_inscricao, 
                      limite_por_cpf, limite_inscricoes, info_pagamento, prazo_pagamento, etapa_id))
            else:
                conn.execute("""
                    UPDATE etapas SET 
                        nome = ?, modalidade = ?, categoria = ?, 
                        data_etapa = ?, prazo_inscricao = ?, 
                        limite_por_cpf = ?, limite_inscricoes = ?,
                        info_pagamento = ?, prazo_pagamento = ?
                    WHERE id = ?
                """, (nome, modalidade, categoria, data_etapa, prazo_inscricao, 
                      limite_por_cpf, limite_inscricoes, info_pagamento, prazo_pagamento, etapa_id))

    def listar_etapas_do_torneio(self, torneio_id):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("""
                    SELECT e.*, 
                           (SELECT COUNT(*) FROM inscricoes WHERE etapa_id = e.id) AS inscricoes_count
                    FROM etapas e 
                    WHERE e.torneio_id = %s 
                    ORDER BY e.data_etapa
                """, (torneio_id,))
                linhas = cur.fetchall()
            else:
                linhas = conn.execute("""
                    SELECT e.*, 
                           (SELECT COUNT(*) FROM inscricoes WHERE etapa_id = e.id) AS inscricoes_count
                    FROM etapas e 
                    WHERE e.torneio_id = ? 
                    ORDER BY e.data_etapa
                """, (torneio_id,)).fetchall()
            return [dict(l) for l in linhas]

    def listar_festivos(self):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("""
                    SELECT e.*, 
                           (SELECT COUNT(*) FROM inscricoes WHERE etapa_id = e.id) AS inscricoes_count
                    FROM etapas e 
                    WHERE e.torneio_id IS NULL 
                    ORDER BY e.data_etapa                """)
                linhas = cur.fetchall()
            else:
                linhas = conn.execute("""
                    SELECT e.*, 
                           (SELECT COUNT(*) FROM inscricoes WHERE etapa_id = e.id) AS inscricoes_count
                    FROM etapas e 
                    WHERE e.torneio_id IS NULL 
                    ORDER BY e.data_etapa
                """).fetchall()
            return [dict(l) for l in linhas]

    def obter_etapa(self, etapa_id):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("SELECT * FROM etapas WHERE id = %s", (etapa_id,))
                linha = cur.fetchone()
            else:
                linha = conn.execute("SELECT * FROM etapas WHERE id = ?", (etapa_id,)).fetchone()
            return dict(linha) if linha else None

    def atualizar_abertura_inscricoes(self, etapa_id, aberta):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute(
                    "UPDATE etapas SET inscricoes_abertas = %s WHERE id = %s",
                    (1 if aberta else 0, etapa_id)
                )
            else:
                conn.execute(
                    "UPDATE etapas SET inscricoes_abertas = ? WHERE id = ?",
                    (1 if aberta else 0, etapa_id)
                )

    def atualizar_limite_inscricoes_etapa(self, etapa_id, novo_limite):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute(
                    "UPDATE etapas SET limite_inscricoes = %s WHERE id = %s",
                    (novo_limite, etapa_id)
                )
            else:
                conn.execute(
                    "UPDATE etapas SET limite_inscricoes = ? WHERE id = ?",
                    (novo_limite, etapa_id)
                )

    def contar_inscricoes_na_etapa(self, etapa_id):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("SELECT COUNT(*) AS total FROM inscricoes WHERE etapa_id = %s", (etapa_id,))
                linha = cur.fetchone()
                return linha["total"] if linha else 0
            else:
                linha = conn.execute(
                    "SELECT COUNT(*) AS total FROM inscricoes WHERE etapa_id = ?",
                    (etapa_id,)
                ).fetchone()
                return linha["total"] if linha else 0

    def contar_inscricoes_do_cpf_na_etapa(self, etapa_id, cpf):
        cpf = regras.validar_cpf_formato(cpf)
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("""
                    SELECT COUNT(*) AS total
                    FROM inscricoes i
                    JOIN passaros p ON p.id = i.passaro_id
                    JOIN socios s ON s.id = p.socio_id
                    WHERE i.etapa_id = %s AND s.cpf = %s
                """, (etapa_id, cpf))
                linha = cur.fetchone()
                return linha["total"] if linha else 0
            else:
                linha = conn.execute("""
                    SELECT COUNT(*) AS total
                    FROM inscricoes i
                    JOIN passaros p ON p.id = i.passaro_id
                    JOIN socios s ON s.id = p.socio_id
                    WHERE i.etapa_id = ? AND s.cpf = ?
                """, (etapa_id, cpf)).fetchone()
                return linha["total"] if linha else 0

    # ================================================================
    # SÓCIOS
    # ================================================================
    def criar_socio(self, **dados):
        nome = dados.get("nome", "").strip()
        cpf = regras.validar_cpf_formato(dados.get("cpf", ""))
        senha = dados.get("senha", "")
        
        if not nome:
            raise regras.ErroValidacao("Nome é obrigatório.")
        if not senha or len(senha) < 6:
            raise regras.ErroValidacao("Senha deve ter pelo menos 6 caracteres.")
        
        sigla_clube = dados.get("sigla_clube", "").strip().upper()
        numero_socio = dados.get("numero_socio", "").strip()
        
        if not sigla_clube:
            raise regras.ErroValidacao("Sigla do clube é obrigatória.")
        if not numero_socio:
            raise regras.ErroValidacao("Número de sócio é obrigatório.")
        
        codigo_socio = f"FOB-{sigla_clube}-{numero_socio}"

        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute("SELECT id FROM socios WHERE cpf = %s OR codigo_socio = %s", (cpf, codigo_socio))
                existente = cur.fetchone()
                if existente:
                    raise ValueError("Já existe um sócio com este CPF ou código de sócio.")
                
                cur.execute("""
                    INSERT INTO socios (
                        nome, cpf, nascimento, sexo, criatorio,
                        sigla_clube, numero_socio, codigo_socio,
                        cep, endereco, numero, complemento, bairro, cidade, uf, pais,
                        ddi, ddd, celular, whatsapp, email,
                        facebook, instagram, youtube, exibir_dados,
                        senha_hash, criado_em
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    nome, cpf, dados.get("nascimento"), dados.get("sexo"), dados.get("criatorio"),
                    sigla_clube, numero_socio, codigo_socio,
                    dados.get("cep"), dados.get("endereco"), dados.get("numero"),
                    dados.get("complemento"), dados.get("bairro"), dados.get("cidade"),
                    dados.get("uf"), dados.get("pais"),
                    dados.get("ddi"), dados.get("ddd"), dados.get("celular"), dados.get("whatsapp"),
                    dados.get("email"), dados.get("facebook"), dados.get("instagram"),
                    dados.get("youtube"), 1 if dados.get("exibir_dados") else 0,
                    _hash_senha(senha), datetime.datetime.now().isoformat()
                ))
                return cur.fetchone()[0]
            else:
                existente = conn.execute(
                    "SELECT id FROM socios WHERE cpf = ? OR codigo_socio = ?",
                    (cpf, codigo_socio)
                ).fetchone()
                if existente:
                    raise ValueError("Já existe um sócio com este CPF ou código de sócio.")

                cursor = conn.execute("""
                    INSERT INTO socios (
                        nome, cpf, nascimento, sexo, criatorio,
                        sigla_clube, numero_socio, codigo_socio,
                        cep, endereco, numero, complemento, bairro, cidade, uf, pais,
                        ddi, ddd, celular, whatsapp, email,
                        facebook, instagram, youtube, exibir_dados,
                        senha_hash, criado_em
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    nome, cpf, dados.get("nascimento"), dados.get("sexo"), dados.get("criatorio"),
                    sigla_clube, numero_socio, codigo_socio,
                    dados.get("cep"), dados.get("endereco"), dados.get("numero"),
                    dados.get("complemento"), dados.get("bairro"), dados.get("cidade"),
                    dados.get("uf"), dados.get("pais"),
                    dados.get("ddi"), dados.get("ddd"), dados.get("celular"), dados.get("whatsapp"),
                    dados.get("email"), dados.get("facebook"), dados.get("instagram"),
                    dados.get("youtube"), 1 if dados.get("exibir_dados") else 0,
                    _hash_senha(senha), datetime.datetime.now().isoformat()
                ))
                return cursor.lastrowid

    def autenticar_socio(self, cpf, senha):
        cpf = regras.validar_cpf_formato(cpf)
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("SELECT * FROM socios WHERE cpf = %s", (cpf,))
                linha = cur.fetchone()
            else:
                linha = conn.execute("SELECT * FROM socios WHERE cpf = ?", (cpf,)).fetchone()
            
            if linha is None:
                return None
            if not _verificar_senha(senha, linha["senha_hash"]):
                return None
            return dict(linha)

    def obter_socio(self, socio_id):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("SELECT * FROM socios WHERE id = %s", (socio_id,))
                linha = cur.fetchone()
            else:
                linha = conn.execute("SELECT * FROM socios WHERE id = ?", (socio_id,)).fetchone()
            return dict(linha) if linha else None

    # ================================================================
    # PÁSSAROS
    # ================================================================
    def cadastrar_passaro(self, socio_id, nome, sigla_criador, numero_anilha, ano_anilha):
        if not nome:
            raise regras.ErroValidacao("Nome do pássaro é obrigatório.")
        if not sigla_criador:
            raise regras.ErroValidacao("Sigla do criador é obrigatória.")
        if not numero_anilha:
            raise regras.ErroValidacao("Número da anilha é obrigatório.")
        if not ano_anilha:
            raise regras.ErroValidacao("Ano da anilha é obrigatório.")

        socio = self.obter_socio(socio_id)
        if not socio:
            raise ValueError("Sócio não encontrado.")
        
        partes = socio["codigo_socio"].split("-")
        sigla_clube = partes[1] if len(partes) > 1 else ""
        numero_socio = partes[2] if len(partes) > 2 else ""

        codigo_ave = f"FOB-{sigla_criador}-{numero_socio}-{numero_anilha}-{ano_anilha}"
        regras.validar_codigo_ave(codigo_ave)

        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute("SELECT id FROM passaros WHERE codigo_ave = %s", (codigo_ave,))
                existente = cur.fetchone()
                if existente:
                    raise ValueError(f"Este código de ave já está cadastrado: {codigo_ave}")
                
                cur.execute("""
                    INSERT INTO passaros (
                        socio_id, nome, sigla_criador, numero_anilha, ano_anilha,
                        codigo_ave, criado_em
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
                """, (
                    socio_id, nome, sigla_criador, numero_anilha, ano_anilha,
                    codigo_ave, datetime.datetime.now().isoformat()
                ))
                return cur.fetchone()[0]
            else:
                existente = conn.execute(
                    "SELECT id FROM passaros WHERE codigo_ave = ?", (codigo_ave,)
                ).fetchone()
                if existente:
                    raise ValueError(f"Este código de ave já está cadastrado: {codigo_ave}")

                cursor = conn.execute("""
                    INSERT INTO passaros (
                        socio_id, nome, sigla_criador, numero_anilha, ano_anilha,
                        codigo_ave, criado_em
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    socio_id, nome, sigla_criador, numero_anilha, ano_anilha,
                    codigo_ave, datetime.datetime.now().isoformat()
                ))
                return cursor.lastrowid

    def listar_passaros_do_socio(self, socio_id):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("SELECT * FROM passaros WHERE socio_id = %s ORDER BY nome", (socio_id,))
                linhas = cur.fetchall()
            else:
                linhas = conn.execute(
                    "SELECT * FROM passaros WHERE socio_id = ? ORDER BY nome", (socio_id,)
                ).fetchall()
            return [dict(l) for l in linhas]

    def obter_passaro(self, passaro_id):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("SELECT * FROM passaros WHERE id = %s", (passaro_id,))
                linha = cur.fetchone()
            else:
                linha = conn.execute("SELECT * FROM passaros WHERE id = ?", (passaro_id,)).fetchone()
            return dict(linha) if linha else None

    # ================================================================
    # EDIÇÃO DE PÁSSAROS COM APROVAÇÃO
    # ================================================================
    def editar_passaro(self, socio_id, passaro_id, nome, sigla_criador, numero_anilha, ano_anilha):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute("SELECT * FROM passaros WHERE id = %s AND socio_id = %s", (passaro_id, socio_id))
                passaro = cur.fetchone()
                if not passaro:
                    raise ValueError("Pássaro não encontrado ou não pertence a você.")
                
                cur.execute("SELECT id FROM passaros_edicoes WHERE passaro_id = %s AND status = 'pendente'", (passaro_id,))
                pendente = cur.fetchone()
                if pendente:
                    raise regras.ErroValidacao("Já existe uma edição pendente para este pássaro.")
                
                cur.execute("""
                    INSERT INTO passaros_edicoes (
                        passaro_id, socio_id, nome, sigla_criador, numero_anilha, 
                        ano_anilha, status, criado_em
                    ) VALUES (%s, %s, %s, %s, %s, %s, 'pendente', %s)
                """, (
                    passaro_id, socio_id, nome, sigla_criador, numero_anilha,
                    ano_anilha, datetime.datetime.now().isoformat()
                ))
            else:
                passaro = conn.execute(
                    "SELECT * FROM passaros WHERE id = ? AND socio_id = ?",
                    (passaro_id, socio_id)
                ).fetchone()
                if not passaro:
                    raise ValueError("Pássaro não encontrado ou não pertence a você.")
                
                pendente = conn.execute(
                    "SELECT id FROM passaros_edicoes WHERE passaro_id = ? AND status = 'pendente'",
                    (passaro_id,)
                ).fetchone()
                if pendente:
                    raise regras.ErroValidacao("Já existe uma edição pendente para este pássaro.")
                
                conn.execute("""
                    INSERT INTO passaros_edicoes (
                        passaro_id, socio_id, nome, sigla_criador, numero_anilha, 
                        ano_anilha, status, criado_em
                    ) VALUES (?, ?, ?, ?, ?, ?, 'pendente', ?)
                """, (
                    passaro_id, socio_id, nome, sigla_criador, numero_anilha,
                    ano_anilha, datetime.datetime.now().isoformat()
                ))

    def listar_edicoes_pendentes(self):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("""
                    SELECT 
                        e.id AS edicao_id,
                        e.passaro_id,
                        e.nome AS nome_novo,
                        e.sigla_criador AS sigla_criador_novo,
                        e.numero_anilha AS numero_anilha_novo,
                        e.ano_anilha AS ano_anilha_novo,
                        e.criado_em,
                        p.nome AS nome_atual,
                        p.codigo_ave,
                        s.nome AS socio_nome,
                        s.id AS socio_id
                    FROM passaros_edicoes e
                    JOIN passaros p ON p.id = e.passaro_id
                    JOIN socios s ON s.id = e.socio_id
                    WHERE e.status = 'pendente'
                    ORDER BY e.criado_em DESC
                """)
                linhas = cur.fetchall()
            else:
                linhas = conn.execute("""
                    SELECT 
                        e.id AS edicao_id,
                        e.passaro_id,
                        e.nome AS nome_novo,
                        e.sigla_criador AS sigla_criador_novo,
                        e.numero_anilha AS numero_anilha_novo,
                        e.ano_anilha AS ano_anilha_novo,
                        e.criado_em,
                        p.nome AS nome_atual,
                        p.codigo_ave,
                        s.nome AS socio_nome,
                        s.id AS socio_id
                    FROM passaros_edicoes e
                    JOIN passaros p ON p.id = e.passaro_id
                    JOIN socios s ON s.id = e.socio_id
                    WHERE e.status = 'pendente'
                    ORDER BY e.criado_em DESC
                """).fetchall()
            return [dict(l) for l in linhas]

    def aprovar_edicao_passaro(self, edicao_id):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute("SELECT * FROM passaros_edicoes WHERE id = %s AND status = 'pendente'", (edicao_id,))
                edicao = cur.fetchone()
                if not edicao:
                    raise ValueError("Edição não encontrada ou já processada.")
                
                cur.execute("""
                    UPDATE passaros SET 
                        nome = %s, sigla_criador = %s, numero_anilha = %s,
                        ano_anilha = %s
                    WHERE id = %s
                """, (
                    edicao["nome"], edicao["sigla_criador"], edicao["numero_anilha"],
                    edicao["ano_anilha"], edicao["passaro_id"]
                ))
                
                cur.execute("UPDATE passaros_edicoes SET status = 'aprovado' WHERE id = %s", (edicao_id,))
            else:
                edicao = conn.execute(
                    "SELECT * FROM passaros_edicoes WHERE id = ? AND status = 'pendente'",
                    (edicao_id,)
                ).fetchone()
                if not edicao:
                    raise ValueError("Edição não encontrada ou já processada.")
                
                conn.execute("""
                    UPDATE passaros SET 
                        nome = ?, sigla_criador = ?, numero_anilha = ?,
                        ano_anilha = ?
                    WHERE id = ?
                """, (
                    edicao["nome"], edicao["sigla_criador"], edicao["numero_anilha"],
                    edicao["ano_anilha"], edicao["passaro_id"]
                ))
                
                conn.execute(
                    "UPDATE passaros_edicoes SET status = 'aprovado' WHERE id = ?",
                    (edicao_id,)
                )

    def rejeitar_edicao_passaro(self, edicao_id):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute("UPDATE passaros_edicoes SET status = 'rejeitado' WHERE id = %s AND status = 'pendente'", (edicao_id,))
            else:
                conn.execute(
                    "UPDATE passaros_edicoes SET status = 'rejeitado' WHERE id = ? AND status = 'pendente'",
                    (edicao_id,)
                )

    # ================================================================
    # RESULTADOS
    # ================================================================
    def salvar_resultado_inscricao(self, inscricao_id, notas, classificacao=None):
        with self._conexao() as conn:
            media = sum(notas) / len(notas) if notas else 0
            
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute("SELECT id FROM resultados WHERE inscricao_id = %s", (inscricao_id,))
                existe = cur.fetchone()
                
                if existe:
                    cur.execute("""
                        UPDATE resultados SET 
                            nota1 = %s, nota2 = %s, nota3 = %s, nota4 = %s, nota5 = %s,
                            media = %s, classificacao = %s
                        WHERE inscricao_id = %s
                    """, (*notas, media, classificacao, inscricao_id))
                else:
                    cur.execute("""
                        INSERT INTO resultados 
                        (inscricao_id, nota1, nota2, nota3, nota4, nota5, media, classificacao, criado_em)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (inscricao_id, *notas, media, classificacao, datetime.datetime.now().isoformat()))
            else:
                existe = conn.execute(
                    "SELECT id FROM resultados WHERE inscricao_id = ?",
                    (inscricao_id,)
                ).fetchone()
                
                if existe:
                    conn.execute("""
                        UPDATE resultados SET 
                            nota1 = ?, nota2 = ?, nota3 = ?, nota4 = ?, nota5 = ?,
                            media = ?, classificacao = ?
                        WHERE inscricao_id = ?
                    """, (*notas, media, classificacao, inscricao_id))
                else:
                    conn.execute("""
                        INSERT INTO resultados 
                        (inscricao_id, nota1, nota2, nota3, nota4, nota5, media, classificacao, criado_em)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (inscricao_id, *notas, media, classificacao, datetime.datetime.now().isoformat()))
            
            self._atualizar_ranking(inscricao_id)

    def _calcular_pontos(self, classificacao):
        if classificacao <= 0:
            return 0
        if classificacao > 30:
            return 0
        return 31 - classificacao

    def _atualizar_ranking(self, inscricao_id):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("""
                    SELECT i.id, i.etapa_id, i.passaro_id, p.socio_id,
                           r.media, r.classificacao
                    FROM inscricoes i
                    JOIN passaros p ON p.id = i.passaro_id
                    JOIN resultados r ON r.inscricao_id = i.id
                    WHERE i.id = %s
                """, (inscricao_id,))
                insc = cur.fetchone()
            else:
                insc = conn.execute("""
                    SELECT i.id, i.etapa_id, i.passaro_id, p.socio_id,
                           r.media, r.classificacao
                    FROM inscricoes i
                    JOIN passaros p ON p.id = i.passaro_id
                    JOIN resultados r ON r.inscricao_id = i.id
                    WHERE i.id = ?
                """, (inscricao_id,)).fetchone()
            
            if not insc:
                return
            
            classificacao = insc["classificacao"]
            if classificacao <= 0 or classificacao > 30:
                pontos = 0
            else:
                pontos = 31 - classificacao
            
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO ranking_geral 
                    (socio_id, passaro_id, etapa_id, pontos, classificacao, criado_em)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (socio_id, passaro_id, etapa_id) DO UPDATE SET
                        pontos = EXCLUDED.pontos,
                        classificacao = EXCLUDED.classificacao,
                        criado_em = EXCLUDED.criado_em
                """, (
                    insc["socio_id"], 
                    insc["passaro_id"], 
                    insc["etapa_id"], 
                    pontos,
                    classificacao,
                    datetime.datetime.now().isoformat()
                ))
            else:
                conn.execute("""
                    INSERT OR REPLACE INTO ranking_geral 
                    (socio_id, passaro_id, etapa_id, pontos, classificacao, criado_em)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    insc["socio_id"], 
                    insc["passaro_id"], 
                    insc["etapa_id"], 
                    pontos,
                    classificacao,
                    datetime.datetime.now().isoformat()
                ))

    def obter_resultados_etapa(self, etapa_id):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("""
                    SELECT 
                        r.id AS resultado_id,
                        r.nota1, r.nota2, r.nota3, r.nota4, r.nota5,
                        r.media,
                        r.classificacao,
                        i.id AS inscricao_id,
                        i.ordem,
                        p.id AS passaro_id,
                        p.nome AS passaro_nome,
                        p.codigo_ave,
                        s.id AS socio_id,
                        s.nome AS socio_nome
                    FROM resultados r
                    JOIN inscricoes i ON i.id = r.inscricao_id
                    JOIN passaros p ON p.id = i.passaro_id
                    JOIN socios s ON s.id = p.socio_id
                    WHERE i.etapa_id = %s
                    ORDER BY r.classificacao ASC
                """, (etapa_id,))
                linhas = cur.fetchall()
            else:
                linhas = conn.execute("""
                    SELECT 
                        r.id AS resultado_id,
                        r.nota1, r.nota2, r.nota3, r.nota4, r.nota5,
                        r.media,
                        r.classificacao,
                        i.id AS inscricao_id,
                        i.ordem,
                        p.id AS passaro_id,
                        p.nome AS passaro_nome,
                        p.codigo_ave,
                        s.id AS socio_id,
                        s.nome AS socio_nome
                    FROM resultados r
                    JOIN inscricoes i ON i.id = r.inscricao_id
                    JOIN passaros p ON p.id = i.passaro_id
                    JOIN socios s ON s.id = p.socio_id
                    WHERE i.etapa_id = ?
                    ORDER BY r.classificacao ASC
                """, (etapa_id,)).fetchall()
            return [dict(l) for l in linhas]

    def obter_ranking_geral(self, limite=None):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                if limite:
                    query = """
                        SELECT 
                            s.id AS socio_id,
                            s.nome AS socio_nome,
                            s.codigo_socio,
                            SUM(rg.pontos) AS total_pontos,
                            COUNT(DISTINCT rg.etapa_id) AS etapas_participadas,
                            COUNT(rg.id) AS total_inscricoes,
                            MAX(rg.classificacao) AS melhor_classificacao
                        FROM ranking_geral rg
                        JOIN socios s ON s.id = rg.socio_id
                        GROUP BY s.id
                        ORDER BY total_pontos DESC, etapas_participadas DESC
                        LIMIT %s
                    """
                    cur.execute(query, (limite,))
                else:
                    query = """
                        SELECT 
                            s.id AS socio_id,
                            s.nome AS socio_nome,
                            s.codigo_socio,
                            SUM(rg.pontos) AS total_pontos,
                            COUNT(DISTINCT rg.etapa_id) AS etapas_participadas,
                            COUNT(rg.id) AS total_inscricoes,
                            MAX(rg.classificacao) AS melhor_classificacao
                        FROM ranking_geral rg
                        JOIN socios s ON s.id = rg.socio_id
                        GROUP BY s.id
                        ORDER BY total_pontos DESC, etapas_participadas DESC
                    """
                    cur.execute(query)
                linhas = cur.fetchall()
            else:
                if limite:
                    query = """
                        SELECT 
                            s.id AS socio_id,
                            s.nome AS socio_nome,
                            s.codigo_socio,
                            SUM(rg.pontos) AS total_pontos,
                            COUNT(DISTINCT rg.etapa_id) AS etapas_participadas,
                            COUNT(rg.id) AS total_inscricoes,
                            MAX(rg.classificacao) AS melhor_classificacao
                        FROM ranking_geral rg
                        JOIN socios s ON s.id = rg.socio_id
                        GROUP BY s.id
                        ORDER BY total_pontos DESC, etapas_participadas DESC
                        LIMIT ?
                    """
                    linhas = conn.execute(query, (limite,)).fetchall()
                else:
                    query = """
                        SELECT 
                            s.id AS socio_id,
                            s.nome AS socio_nome,
                            s.codigo_socio,
                            SUM(rg.pontos) AS total_pontos,
                            COUNT(DISTINCT rg.etapa_id) AS etapas_participadas,
                            COUNT(rg.id) AS total_inscricoes,
                            MAX(rg.classificacao) AS melhor_classificacao
                        FROM ranking_geral rg
                        JOIN socios s ON s.id = rg.socio_id
                        GROUP BY s.id
                        ORDER BY total_pontos DESC, etapas_participadas DESC
                    """
                    linhas = conn.execute(query).fetchall()
            return [dict(l) for l in linhas]

    def obter_ranking_por_modalidade(self, modalidade, limite=None):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                if limite:
                    query = """
                        SELECT 
                            s.id AS socio_id,
                            s.nome AS socio_nome,
                            s.codigo_socio,
                            SUM(rg.pontos) AS total_pontos,
                            COUNT(DISTINCT rg.etapa_id) AS etapas_participadas,
                            COUNT(rg.id) AS total_inscricoes,
                            MAX(rg.classificacao) AS melhor_classificacao
                        FROM ranking_geral rg
                        JOIN socios s ON s.id = rg.socio_id
                        JOIN etapas e ON e.id = rg.etapa_id
                        WHERE e.modalidade = %s
                        GROUP BY s.id
                        ORDER BY total_pontos DESC, etapas_participadas DESC
                        LIMIT %s
                    """
                    cur.execute(query, (modalidade, limite))
                else:
                    query = """
                        SELECT 
                            s.id AS socio_id,
                            s.nome AS socio_nome,
                            s.codigo_socio,
                            SUM(rg.pontos) AS total_pontos,
                            COUNT(DISTINCT rg.etapa_id) AS etapas_participadas,
                            COUNT(rg.id) AS total_inscricoes,
                            MAX(rg.classificacao) AS melhor_classificacao
                        FROM ranking_geral rg
                        JOIN socios s ON s.id = rg.socio_id
                        JOIN etapas e ON e.id = rg.etapa_id
                        WHERE e.modalidade = %s
                        GROUP BY s.id
                        ORDER BY total_pontos DESC, etapas_participadas DESC
                    """
                    cur.execute(query, (modalidade,))
                linhas = cur.fetchall()
            else:
                if limite:
                    query = """
                        SELECT 
                            s.id AS socio_id,
                            s.nome AS socio_nome,
                            s.codigo_socio,
                            SUM(rg.pontos) AS total_pontos,
                            COUNT(DISTINCT rg.etapa_id) AS etapas_participadas,
                            COUNT(rg.id) AS total_inscricoes,
                            MAX(rg.classificacao) AS melhor_classificacao
                        FROM ranking_geral rg
                        JOIN socios s ON s.id = rg.socio_id
                        JOIN etapas e ON e.id = rg.etapa_id
                        WHERE e.modalidade = ?
                        GROUP BY s.id
                        ORDER BY total_pontos DESC, etapas_participadas DESC
                        LIMIT ?
                    """
                    linhas = conn.execute(query, (modalidade, limite)).fetchall()
                else:
                    query = """
                        SELECT 
                            s.id AS socio_id,
                            s.nome AS socio_nome,
                            s.codigo_socio,
                            SUM(rg.pontos) AS total_pontos,
                            COUNT(DISTINCT rg.etapa_id) AS etapas_participadas,
                            COUNT(rg.id) AS total_inscricoes,
                            MAX(rg.classificacao) AS melhor_classificacao
                        FROM ranking_geral rg
                        JOIN socios s ON s.id = rg.socio_id
                        JOIN etapas e ON e.id = rg.etapa_id
                        WHERE e.modalidade = ?
                        GROUP BY s.id
                        ORDER BY total_pontos DESC, etapas_participadas DESC
                    """
                    linhas = conn.execute(query, (modalidade,)).fetchall()
            return [dict(l) for l in linhas]

    def obter_ranking_passaros(self, limite=None):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                if limite:
                    query = """
                        SELECT 
                            p.id AS passaro_id,
                            p.nome AS passaro_nome,
                            p.codigo_ave,
                            s.nome AS socio_nome,
                            SUM(rg.pontos) AS total_pontos,
                            COUNT(rg.etapa_id) AS etapas_participadas,
                            MAX(rg.classificacao) AS melhor_classificacao
                        FROM ranking_geral rg
                        JOIN passaros p ON p.id = rg.passaro_id
                        JOIN socios s ON s.id = rg.socio_id
                        GROUP BY p.id
                        ORDER BY total_pontos DESC, etapas_participadas DESC
                        LIMIT %s
                    """
                    cur.execute(query, (limite,))
                else:
                    query = """
                        SELECT 
                            p.id AS passaro_id,
                            p.nome AS passaro_nome,
                            p.codigo_ave,
                            s.nome AS socio_nome,
                            SUM(rg.pontos) AS total_pontos,
                            COUNT(rg.etapa_id) AS etapas_participadas,
                            MAX(rg.classificacao) AS melhor_classificacao
                        FROM ranking_geral rg
                        JOIN passaros p ON p.id = rg.passaro_id
                        JOIN socios s ON s.id = rg.socio_id
                        GROUP BY p.id
                        ORDER BY total_pontos DESC, etapas_participadas DESC
                    """
                    cur.execute(query)
                linhas = cur.fetchall()
            else:
                if limite:
                    query = """
                        SELECT 
                            p.id AS passaro_id,
                            p.nome AS passaro_nome,
                            p.codigo_ave,
                            s.nome AS socio_nome,
                            SUM(rg.pontos) AS total_pontos,
                            COUNT(rg.etapa_id) AS etapas_participadas,
                            MAX(rg.classificacao) AS melhor_classificacao
                        FROM ranking_geral rg
                        JOIN passaros p ON p.id = rg.passaro_id
                        JOIN socios s ON s.id = rg.socio_id
                        GROUP BY p.id
                        ORDER BY total_pontos DESC, etapas_participadas DESC
                        LIMIT ?
                    """
                    linhas = conn.execute(query, (limite,)).fetchall()
                else:
                    query = """
                        SELECT 
                            p.id AS passaro_id,
                            p.nome AS passaro_nome,
                            p.codigo_ave,
                            s.nome AS socio_nome,
                            SUM(rg.pontos) AS total_pontos,
                            COUNT(rg.etapa_id) AS etapas_participadas,
                            MAX(rg.classificacao) AS melhor_classificacao
                        FROM ranking_geral rg
                        JOIN passaros p ON p.id = rg.passaro_id
                        JOIN socios s ON s.id = rg.socio_id
                        GROUP BY p.id
                        ORDER BY total_pontos DESC, etapas_participadas DESC
                    """
                    linhas = conn.execute(query).fetchall()
            return [dict(l) for l in linhas]

    # ================================================================
    # RESULTADOS IMPORTADOS
    # ================================================================
    def importar_resultado_etapa(self, torneio_nome, categoria, data_etapa, resultados):
        """Importa um resultado de etapa completo."""
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute(
                    "SELECT id FROM resultados_importados WHERE torneio_nome = %s AND data_etapa = %s AND categoria = %s LIMIT 1",
                    (torneio_nome, data_etapa, categoria)
                )
                existente = cur.fetchone()
                
                if existente:
                    cur.execute(
                        "DELETE FROM resultados_importados WHERE torneio_nome = %s AND data_etapa = %s AND categoria = %s",
                        (torneio_nome, data_etapa, categoria)
                    )
                
                for r in resultados:
                    cur.execute("""
                        INSERT INTO resultados_importados 
                        (torneio_nome, categoria, data_etapa, posicao, passaro_nome, anilha, proprietario, tempo, pontos, criado_em)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        torneio_nome, categoria, data_etapa, r["posicao"], 
                        r["passaro_nome"], r["anilha"], r["proprietario"], 
                        r.get("tempo", ""), r["pontos"], datetime.datetime.now().isoformat()
                    ))
            else:
                existente = conn.execute(
                    "SELECT id FROM resultados_importados WHERE torneio_nome = ? AND data_etapa = ? AND categoria = ? LIMIT 1",
                    (torneio_nome, data_etapa, categoria)
                ).fetchone()
                
                if existente:
                    conn.execute(
                        "DELETE FROM resultados_importados WHERE torneio_nome = ? AND data_etapa = ? AND categoria = ?",
                        (torneio_nome, data_etapa, categoria)
                    )
                
                for r in resultados:
                    conn.execute("""
                        INSERT INTO resultados_importados 
                        (torneio_nome, categoria, data_etapa, posicao, passaro_nome, anilha, proprietario, tempo, pontos, criado_em)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        torneio_nome, categoria, data_etapa, r["posicao"], 
                        r["passaro_nome"], r["anilha"], r["proprietario"], 
                        r.get("tempo", ""), r["pontos"], datetime.datetime.now().isoformat()
                    ))
            
            return True

    def importar_csv_resultado(self, arquivo_csv, torneio_nome, categoria, data_etapa):
        """Importa um arquivo CSV gerado pelo Marcador Digital."""
        import csv
        import re
        
        resultados = []
        
        with open(arquivo_csv, 'r', encoding='utf-8-sig') as f:
            linhas = f.readlines()
        
        linhas = [l.strip() for l in linhas if l.strip()]
        
        inicio = 0
        for i, linha in enumerate(linhas):
            if 'Posição' in linha or 'Posicao' in linha:
                inicio = i + 1
                break
        
        if inicio == 0:
            inicio = 3
        
        for linha in linhas[inicio:]:
            if not linha:
                continue
            
            partes = [p.strip() for p in linha.split(';')]
            if len(partes) < 5:
                continue
            
            pos_str = re.sub(r'[°º]', '', partes[0])
            try:
                posicao = int(pos_str)
            except:
                continue
            
            passaro_nome = partes[2] if len(partes) > 2 else ""
            if not passaro_nome:
                continue
            
            anilha = partes[3] if len(partes) > 3 and partes[3] else "SEM ANILHA"
            proprietario = partes[1] if len(partes) > 1 and partes[1] else "SEM PROPRIETÁRIO"
            tempo = partes[4] if len(partes) > 4 and partes[4] else "00:00:000"
            
            pontos = 0
            if len(partes) > 5:
                try:
                    pontos = int(partes[5])
                except:
                    pontos = 0
            
            resultados.append({
                "posicao": posicao,
                "passaro_nome": passaro_nome,
                "anilha": anilha,
                "proprietario": proprietario,
                "tempo": tempo,
                "pontos": pontos
            })
        
        if not resultados:
            raise ValueError("Nenhum dado válido encontrado no arquivo.")
        
        return self.importar_resultado_etapa(torneio_nome, categoria, data_etapa, resultados)

    def listar_etapas_importadas(self, categoria=None):
        """Lista todas as etapas já importadas."""
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                if categoria:
                    cur.execute("""
                        SELECT 
                            torneio_nome, categoria, data_etapa, 
                            COUNT(*) as total_inscritos,
                            MIN(posicao) as primeiro,
                            MAX(pontos) as max_pontos,
                            GROUP_CONCAT(DISTINCT proprietario) as proprietarios
                        FROM resultados_importados
                        WHERE categoria = %s
                        GROUP BY torneio_nome, categoria, data_etapa
                        ORDER BY data_etapa DESC
                    """, (categoria,))
                else:
                    cur.execute("""
                        SELECT 
                            torneio_nome, categoria, data_etapa, 
                            COUNT(*) as total_inscritos,
                            MIN(posicao) as primeiro,
                            MAX(pontos) as max_pontos,
                            GROUP_CONCAT(DISTINCT proprietario) as proprietarios
                        FROM resultados_importados
                        GROUP BY torneio_nome, categoria, data_etapa
                        ORDER BY data_etapa DESC
                    """)
                linhas = cur.fetchall()
            else:
                if categoria:
                    linhas = conn.execute("""
                        SELECT 
                            torneio_nome, categoria, data_etapa, 
                            COUNT(*) as total_inscritos,
                            MIN(posicao) as primeiro,
                            MAX(pontos) as max_pontos,
                            GROUP_CONCAT(DISTINCT proprietario) as proprietarios
                        FROM resultados_importados
                        WHERE categoria = ?
                        GROUP BY torneio_nome, categoria, data_etapa
                        ORDER BY data_etapa DESC
                    """, (categoria,)).fetchall()
                else:
                    linhas = conn.execute("""
                        SELECT 
                            torneio_nome, categoria, data_etapa, 
                            COUNT(*) as total_inscritos,
                            MIN(posicao) as primeiro,
                            MAX(pontos) as max_pontos,
                            GROUP_CONCAT(DISTINCT proprietario) as proprietarios
                        FROM resultados_importados
                        GROUP BY torneio_nome, categoria, data_etapa
                        ORDER BY data_etapa DESC
                    """).fetchall()
            return [dict(l) for l in linhas]

    def obter_resultado_etapa_importado(self, torneio_nome, data_etapa, categoria):
        """Retorna os resultados de uma etapa específica."""
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("""
                    SELECT posicao, passaro_nome, anilha, proprietario, tempo, pontos
                    FROM resultados_importados
                    WHERE torneio_nome = %s AND data_etapa = %s AND categoria = %s
                    ORDER BY posicao ASC
                """, (torneio_nome, data_etapa, categoria))
                linhas = cur.fetchall()
            else:
                linhas = conn.execute("""
                    SELECT posicao, passaro_nome, anilha, proprietario, tempo, pontos
                    FROM resultados_importados
                    WHERE torneio_nome = ? AND data_etapa = ? AND categoria = ?
                    ORDER BY posicao ASC
                """, (torneio_nome, data_etapa, categoria)).fetchall()
            return [dict(l) for l in linhas]

    def obter_ranking_geral_importado(self, categoria=None):
        """Retorna o ranking geral acumulado de todas as etapas importadas."""
        try:
            with self._conexao() as conn:
                if self.usar_postgres:
                    cur = conn.cursor(cursor_factory=RealDictCursor)
                    cur.execute("SELECT COUNT(*) as total FROM resultados_importados")
                    total = cur.fetchone()
                else:
                    total = conn.execute("SELECT COUNT(*) as total FROM resultados_importados").fetchone()
                
                if total["total"] == 0:
                    return []
                
                if self.usar_postgres:
                    cur = conn.cursor(cursor_factory=RealDictCursor)
                    if categoria:
                        query = """
                            SELECT 
                                passaro_nome,
                                anilha,
                                proprietario,
                                SUM(pontos) as total_pontos,
                                COUNT(*) as etapas_participadas,
                                array_agg(pontos) as pontos_por_etapa,
                                array_agg(data_etapa) as etapas_datas
                            FROM resultados_importados
                            WHERE categoria = %s
                            GROUP BY passaro_nome, anilha, proprietario
                            ORDER BY total_pontos DESC
                        """
                        cur.execute(query, (categoria,))
                    else:
                        query = """
                            SELECT 
                                passaro_nome,
                                anilha,
                                proprietario,
                                SUM(pontos) as total_pontos,
                                COUNT(*) as etapas_participadas,
                                array_agg(pontos) as pontos_por_etapa,
                                array_agg(data_etapa) as etapas_datas
                            FROM resultados_importados
                            GROUP BY passaro_nome, anilha, proprietario
                            ORDER BY total_pontos DESC
                        """
                        cur.execute(query)
                    linhas = cur.fetchall()
                else:
                    if categoria:
                        query = """
                            SELECT 
                                passaro_nome,
                                anilha,
                                proprietario,
                                SUM(pontos) as total_pontos,
                                COUNT(*) as etapas_participadas,
                                GROUP_CONCAT(pontos) as pontos_por_etapa,
                                GROUP_CONCAT(data_etapa) as etapas_datas
                            FROM resultados_importados
                            WHERE categoria = ?
                            GROUP BY passaro_nome, anilha, proprietario
                            ORDER BY total_pontos DESC
                        """
                        linhas = conn.execute(query, (categoria,)).fetchall()
                    else:
                        query = """
                            SELECT 
                                passaro_nome,
                                anilha,
                                proprietario,
                                SUM(pontos) as total_pontos,
                                COUNT(*) as etapas_participadas,
                                GROUP_CONCAT(pontos) as pontos_por_etapa,
                                GROUP_CONCAT(data_etapa) as etapas_datas
                            FROM resultados_importados
                            GROUP BY passaro_nome, anilha, proprietario
                            ORDER BY total_pontos DESC
                        """
                        linhas = conn.execute(query).fetchall()
                
                resultado = []
                for l in linhas:
                    d = dict(l)
                    if self.usar_postgres:
                        d["pontos_por_etapa"] = [str(x) for x in d["pontos_por_etapa"]] if d["pontos_por_etapa"] else []
                        d["etapas_datas"] = d["etapas_datas"] if d["etapas_datas"] else []
                    else:
                        pontos_str = d["pontos_por_etapa"] or ""
                        datas_str = d["etapas_datas"] or ""
                        d["pontos_por_etapa"] = pontos_str.split(",") if pontos_str else []
                        d["etapas_datas"] = datas_str.split(",") if datas_str else []
                    resultado.append(d)
                
                return resultado
        except Exception as e:
            print(f"Erro no ranking: {e}")
            return []

    def obter_categorias_disponiveis(self):
        """Retorna todas as categorias disponíveis nos resultados."""
        try:
            with self._conexao() as conn:
                if self.usar_postgres:
                    cur = conn.cursor(cursor_factory=RealDictCursor)
                    cur.execute("SELECT DISTINCT categoria FROM resultados_importados ORDER BY categoria")
                    linhas = cur.fetchall()
                else:
                    linhas = conn.execute("""
                        SELECT DISTINCT categoria FROM resultados_importados ORDER BY categoria
                    """).fetchall()
                return [l["categoria"] for l in linhas]
        except:
            return []

    def exportar_inscritos_para_excel(self, torneio_nome, data_etapa, categoria):
        """Exporta a lista de inscritos para o formato do Marcador Digital."""
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("""
                    SELECT passaro_nome, anilha, proprietario
                    FROM resultados_importados
                    WHERE torneio_nome = %s AND data_etapa = %s AND categoria = %s
                    ORDER BY posicao ASC
                """, (torneio_nome, data_etapa, categoria))
                linhas = cur.fetchall()
            else:
                linhas = conn.execute("""
                    SELECT passaro_nome, anilha, proprietario
                    FROM resultados_importados
                    WHERE torneio_nome = ? AND data_etapa = ? AND categoria = ?
                    ORDER BY posicao ASC
                """, (torneio_nome, data_etapa, categoria)).fetchall()
            return [dict(l) for l in linhas]

    def excluir_etapa_importada(self, torneio_nome, data_etapa, categoria):
        """Exclui uma etapa importada."""
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute(
                    "DELETE FROM resultados_importados WHERE torneio_nome = %s AND data_etapa = %s AND categoria = %s",
                    (torneio_nome, data_etapa, categoria)
                )
            else:
                conn.execute(
                    "DELETE FROM resultados_importados WHERE torneio_nome = ? AND data_etapa = ? AND categoria = ?",
                    (torneio_nome, data_etapa, categoria)
                )
            return True

    def editar_resultado_etapa(self, torneio_nome, data_etapa, categoria, resultados):
        """Edita os resultados de uma etapa existente."""
        self.excluir_etapa_importada(torneio_nome, data_etapa, categoria)
        return self.importar_resultado_etapa(torneio_nome, categoria, data_etapa, resultados)

    def contar_resultados_importados(self):
        """Conta quantos resultados importados existem."""
        try:
            with self._conexao() as conn:
                if self.usar_postgres:
                    cur = conn.cursor(cursor_factory=RealDictCursor)
                    cur.execute("SELECT COUNT(*) as total FROM resultados_importados")
                    linha = cur.fetchone()
                else:
                    linha = conn.execute("SELECT COUNT(*) as total FROM resultados_importados").fetchone()
                return linha["total"]
        except:
            return 0

    # ================================================================
    # CRIADORES
    # ================================================================
    def listar_criadores(self, busca=None):
        """Lista todos os criadores com seus dados de contato."""
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                if busca:
                    query = """
                        SELECT 
                            id, nome, criatorio, ddi, ddd, celular, whatsapp, email,
                            facebook, instagram, youtube
                        FROM socios 
                        WHERE exibir_dados = 1
                        AND (nome ILIKE %s OR criatorio ILIKE %s)
                        ORDER BY nome ASC
                    """
                    busca_termo = f"%{busca}%"
                    cur.execute(query, (busca_termo, busca_termo))
                else:
                    query = """
                        SELECT 
                            id, nome, criatorio, ddi, ddd, celular, whatsapp, email,
                            facebook, instagram, youtube
                        FROM socios 
                        WHERE exibir_dados = 1
                        ORDER BY nome ASC
                    """
                    cur.execute(query)
                linhas = cur.fetchall()
            else:
                if busca:
                    query = """
                        SELECT 
                            id, nome, criatorio, ddi, ddd, celular, whatsapp, email,
                            facebook, instagram, youtube
                        FROM socios 
                        WHERE exibir_dados = 1
                        AND (nome LIKE ? OR criatorio LIKE ?)
                        ORDER BY nome ASC
                    """
                    busca_termo = f"%{busca}%"
                    linhas = conn.execute(query, (busca_termo, busca_termo)).fetchall()
                else:
                    query = """
                        SELECT 
                            id, nome, criatorio, ddi, ddd, celular, whatsapp, email,
                            facebook, instagram, youtube
                        FROM socios 
                        WHERE exibir_dados = 1
                        ORDER BY nome ASC
                    """
                    linhas = conn.execute(query).fetchall()
            return [dict(l) for l in linhas]

    def obter_criador(self, socio_id):
        """Retorna os dados públicos de um criador."""
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("""
                    SELECT 
                        id, nome, criatorio, ddi, ddd, celular, whatsapp, email,
                        facebook, instagram, youtube
                    FROM socios 
                    WHERE id = %s AND exibir_dados = 1
                """, (socio_id,))
                linha = cur.fetchone()
            else:
                linha = conn.execute("""
                    SELECT 
                        id, nome, criatorio, ddi, ddd, celular, whatsapp, email,
                        facebook, instagram, youtube
                    FROM socios 
                    WHERE id = ? AND exibir_dados = 1
                """, (socio_id,)).fetchone()
            return dict(linha) if linha else None

    # ================================================================
    # INSCRIÇÕES DO SÓCIO
    # ================================================================
    def listar_inscricoes_do_socio_por_categoria(self, socio_id):
        """Retorna as inscrições do sócio agrupadas por categoria."""
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("""
                    SELECT 
                        i.id AS inscricao_id,
                        i.etapa_id,
                        i.ordem,
                        i.liberada_manual,
                        i.pagamento_confirmado,
                        i.criado_em,
                        p.id AS passaro_id,
                        p.nome AS passaro_nome,
                        p.codigo_ave,
                        e.id AS etapa_id,
                        e.nome AS etapa_nome,
                        e.data_etapa,
                        e.modalidade,
                        e.categoria,
                        e.info_pagamento,
                        e.prazo_pagamento,
                        t.id AS torneio_id,
                        t.nome AS torneio_nome,
                        t.endereco,
                        t.mapa_url,
                        pg.status AS pagamento_status,
                        pg.comprovante
                    FROM inscricoes i
                    JOIN passaros p ON p.id = i.passaro_id
                    JOIN etapas e ON e.id = i.etapa_id
                    LEFT JOIN torneios t ON t.id = e.torneio_id
                    LEFT JOIN pagamentos pg ON pg.inscricao_id = i.id
                    WHERE p.socio_id = %s
                    ORDER BY e.categoria, e.modalidade, e.data_etapa DESC
                """, (socio_id,))
                linhas = cur.fetchall()
            else:
                linhas = conn.execute("""
                    SELECT 
                        i.id AS inscricao_id,
                        i.etapa_id,
                        i.ordem,
                        i.liberada_manual,
                        i.pagamento_confirmado,
                        i.criado_em,
                        p.id AS passaro_id,
                        p.nome AS passaro_nome,
                        p.codigo_ave,
                        e.id AS etapa_id,
                        e.nome AS etapa_nome,
                        e.data_etapa,
                        e.modalidade,
                        e.categoria,
                        e.info_pagamento,
                        e.prazo_pagamento,
                        t.id AS torneio_id,
                        t.nome AS torneio_nome,
                        t.endereco,
                        t.mapa_url,
                        pg.status AS pagamento_status,
                        pg.comprovante
                    FROM inscricoes i
                    JOIN passaros p ON p.id = i.passaro_id
                    JOIN etapas e ON e.id = i.etapa_id
                    LEFT JOIN torneios t ON t.id = e.torneio_id
                    LEFT JOIN pagamentos pg ON pg.inscricao_id = i.id
                    WHERE p.socio_id = ?
                    ORDER BY e.categoria, e.modalidade, e.data_etapa DESC
                """, (socio_id,)).fetchall()
            
            resultado = {}
            for l in linhas:
                d = dict(l)
                # Para MISTO, mostra "Misto" em vez de "FILHOTE" ou "ADULTO"
                if d['categoria'] == "MISTO":
                    chave = f"Misto - {d['modalidade']}"
                else:
                    chave = f"{d['categoria']} - {d['modalidade']}"
                
                if chave not in resultado:
                    resultado[chave] = []
                resultado[chave].append(d)
            
            return resultado

    def inscrever_multiplos_passaros(self, etapa_id, passaros_ids, socio_id):
        """Inscreve múltiplos pássaros em uma etapa de uma vez."""
        inscritos = []
        erros = []
        
        for passaro_id in passaros_ids:
            try:
                with self._conexao() as conn:
                    if self.usar_postgres:
                        cur = conn.cursor(cursor_factory=RealDictCursor)
                        cur.execute("SELECT * FROM passaros WHERE id = %s AND socio_id = %s", (passaro_id, socio_id))
                        passaro = cur.fetchone()
                    else:
                        passaro = conn.execute(
                            "SELECT * FROM passaros WHERE id = ? AND socio_id = ?",
                            (passaro_id, socio_id)
                        ).fetchone()
                    if not passaro:
                        erros.append(f"Pássaro não encontrado ou não pertence a você.")
                        continue
                
                inscricao_id = self.inscrever_passaro_na_etapa(etapa_id, passaro_id, socio_id)
                inscritos.append(inscricao_id)
            except regras.ErroValidacao as e:
                erros.append(str(e))
            except ValueError as e:
                erros.append(str(e))
            except Exception as e:
                erros.append(f"Erro ao inscrever: {str(e)}")
        
        return inscritos, erros

    # ================================================================
    # TRANSFERÊNCIA
    # ================================================================
    def solicitar_transferencia(self, passaro_id, socio_origem_id, cpf_destino):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("SELECT * FROM passaros WHERE id = %s AND socio_id = %s", (passaro_id, socio_origem_id))
                passaro = cur.fetchone()
                if not passaro:
                    raise ValueError("Pássaro não encontrado ou não pertence a você.")
                
                cur.execute("SELECT id, nome FROM socios WHERE cpf = %s", (cpf_destino,))
                socio_destino = cur.fetchone()
                if not socio_destino:
                    raise ValueError("CPF do novo proprietário não encontrado.")
                
                if socio_destino["id"] == socio_origem_id:
                    raise ValueError("Não é possível transferir para você mesmo.")
                
                cur.execute("SELECT id FROM transferencias WHERE passaro_id = %s AND status = 'pendente'", (passaro_id,))
                pendente = cur.fetchone()
                if pendente:
                    raise ValueError("Já existe uma solicitação de transferência pendente para este pássaro.")
                
                cur.execute("""
                    INSERT INTO transferencias 
                    (passaro_id, socio_origem_id, socio_destino_id, cpf_destino, status, criado_em)
                    VALUES (%s, %s, %s, %s, 'pendente', %s) RETURNING id
                """, (passaro_id, socio_origem_id, socio_destino["id"], cpf_destino, datetime.datetime.now().isoformat()))
                return cur.fetchone()[0]
            else:
                passaro = conn.execute(
                    "SELECT * FROM passaros WHERE id = ? AND socio_id = ?",
                    (passaro_id, socio_origem_id)
                ).fetchone()
                if not passaro:
                    raise ValueError("Pássaro não encontrado ou não pertence a você.")
                
                socio_destino = conn.execute(
                    "SELECT id, nome FROM socios WHERE cpf = ?",
                    (cpf_destino,)
                ).fetchone()
                if not socio_destino:
                    raise ValueError("CPF do novo proprietário não encontrado.")
                
                if socio_destino["id"] == socio_origem_id:
                    raise ValueError("Não é possível transferir para você mesmo.")
                
                pendente = conn.execute(
                    "SELECT id FROM transferencias WHERE passaro_id = ? AND status = 'pendente'",
                    (passaro_id,)
                ).fetchone()
                if pendente:
                    raise ValueError("Já existe uma solicitação de transferência pendente para este pássaro.")
                
                cursor = conn.execute("""
                    INSERT INTO transferencias 
                    (passaro_id, socio_origem_id, socio_destino_id, cpf_destino, status, criado_em)
                    VALUES (?, ?, ?, ?, 'pendente', ?)
                """, (passaro_id, socio_origem_id, socio_destino["id"], cpf_destino, datetime.datetime.now().isoformat()))
                return cursor.lastrowid

    def listar_transferencias_pendentes(self, socio_id=None):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                if socio_id:
                    cur.execute("""
                        SELECT 
                            t.id as transferencia_id,
                            t.cpf_destino,
                            t.status,
                            t.criado_em,
                            p.id as passaro_id,
                            p.nome as passaro_nome,
                            p.codigo_ave,
                            so.nome as socio_origem_nome,
                            sd.nome as socio_destino_nome
                        FROM transferencias t
                        JOIN passaros p ON p.id = t.passaro_id
                        JOIN socios so ON so.id = t.socio_origem_id
                        JOIN socios sd ON sd.id = t.socio_destino_id
                        WHERE t.socio_destino_id = %s AND t.status = 'pendente'
                        ORDER BY t.criado_em DESC
                    """, (socio_id,))
                else:
                    cur.execute("""
                        SELECT 
                            t.id as transferencia_id,
                            t.cpf_destino,
                            t.status,
                            t.criado_em,
                            p.id as passaro_id,
                            p.nome as passaro_nome,
                            p.codigo_ave,
                            so.nome as socio_origem_nome,
                            sd.nome as socio_destino_nome
                        FROM transferencias t
                        JOIN passaros p ON p.id = t.passaro_id
                        JOIN socios so ON so.id = t.socio_origem_id
                        JOIN socios sd ON sd.id = t.socio_destino_id
                        WHERE t.status = 'pendente'
                        ORDER BY t.criado_em DESC
                    """)
                linhas = cur.fetchall()
            else:
                if socio_id:
                    query = """
                        SELECT 
                            t.id as transferencia_id,
                            t.cpf_destino,
                            t.status,
                            t.criado_em,
                            p.id as passaro_id,
                            p.nome as passaro_nome,
                            p.codigo_ave,
                            so.nome as socio_origem_nome,
                            sd.nome as socio_destino_nome
                        FROM transferencias t
                        JOIN passaros p ON p.id = t.passaro_id
                        JOIN socios so ON so.id = t.socio_origem_id
                        JOIN socios sd ON sd.id = t.socio_destino_id
                        WHERE t.socio_destino_id = ? AND t.status = 'pendente'
                        ORDER BY t.criado_em DESC
                    """
                    linhas = conn.execute(query, (socio_id,)).fetchall()
                else:
                    query = """
                        SELECT 
                            t.id as transferencia_id,
                            t.cpf_destino,
                            t.status,
                            t.criado_em,
                            p.id as passaro_id,
                            p.nome as passaro_nome,
                            p.codigo_ave,
                            so.nome as socio_origem_nome,
                            sd.nome as socio_destino_nome
                        FROM transferencias t
                        JOIN passaros p ON p.id = t.passaro_id
                        JOIN socios so ON so.id = t.socio_origem_id
                        JOIN socios sd ON sd.id = t.socio_destino_id
                        WHERE t.status = 'pendente'
                        ORDER BY t.criado_em DESC
                    """
                    linhas = conn.execute(query).fetchall()
            return [dict(l) for l in linhas]

    def listar_transferencias_enviadas(self, socio_id):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("""
                    SELECT 
                        t.id as transferencia_id,
                        t.cpf_destino,
                        t.status,
                        t.criado_em,
                        p.id as passaro_id,
                        p.nome as passaro_nome,
                        p.codigo_ave,
                        sd.nome as socio_destino_nome
                    FROM transferencias t
                    JOIN passaros p ON p.id = t.passaro_id
                    JOIN socios sd ON sd.id = t.socio_destino_id
                    WHERE t.socio_origem_id = %s
                    ORDER BY t.criado_em DESC
                """, (socio_id,))
                linhas = cur.fetchall()
            else:
                linhas = conn.execute("""
                    SELECT 
                        t.id as transferencia_id,
                        t.cpf_destino,
                        t.status,
                        t.criado_em,
                        p.id as passaro_id,
                        p.nome as passaro_nome,
                        p.codigo_ave,
                        sd.nome as socio_destino_nome
                    FROM transferencias t
                    JOIN passaros p ON p.id = t.passaro_id
                    JOIN socios sd ON sd.id = t.socio_destino_id
                    WHERE t.socio_origem_id = ?
                    ORDER BY t.criado_em DESC
                """, (socio_id,)).fetchall()
            return [dict(l) for l in linhas]

    def aceitar_transferencia(self, transferencia_id, socio_destino_id):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute("SELECT * FROM transferencias WHERE id = %s AND socio_destino_id = %s AND status = 'pendente'", (transferencia_id, socio_destino_id))
                trans = cur.fetchone()
                if not trans:
                    raise ValueError("Transferência não encontrada ou já processada.")
                
                cur.execute("UPDATE passaros SET socio_id = %s WHERE id = %s", (socio_destino_id, trans["passaro_id"]))
                cur.execute("UPDATE transferencias SET status = 'aprovado' WHERE id = %s", (transferencia_id,))
            else:
                trans = conn.execute(
                    "SELECT * FROM transferencias WHERE id = ? AND socio_destino_id = ? AND status = 'pendente'",
                    (transferencia_id, socio_destino_id)
                ).fetchone()
                if not trans:
                    raise ValueError("Transferência não encontrada ou já processada.")
                
                conn.execute(
                    "UPDATE passaros SET socio_id = ? WHERE id = ?",
                    (socio_destino_id, trans["passaro_id"])
                )
                conn.execute(
                    "UPDATE transferencias SET status = 'aprovado' WHERE id = ?",
                    (transferencia_id,)
                )
            
            return True

    def recusar_transferencia(self, transferencia_id, socio_destino_id):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute("SELECT * FROM transferencias WHERE id = %s AND socio_destino_id = %s AND status = 'pendente'", (transferencia_id, socio_destino_id))
                trans = cur.fetchone()
                if not trans:
                    raise ValueError("Transferência não encontrada ou já processada.")
                
                cur.execute("UPDATE transferencias SET status = 'recusado' WHERE id = %s", (transferencia_id,))
            else:
                trans = conn.execute(
                    "SELECT * FROM transferencias WHERE id = ? AND socio_destino_id = ? AND status = 'pendente'",
                    (transferencia_id, socio_destino_id)
                ).fetchone()
                if not trans:
                    raise ValueError("Transferência não encontrada ou já processada.")
                
                conn.execute(
                    "UPDATE transferencias SET status = 'recusado' WHERE id = ?",
                    (transferencia_id,)
                )
            
            return True

    def aprovar_transferencia_admin(self, transferencia_id):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute("SELECT * FROM transferencias WHERE id = %s AND status = 'pendente'", (transferencia_id,))
                trans = cur.fetchone()
                if not trans:
                    raise ValueError("Transferência não encontrada.")
                
                cur.execute("SELECT id FROM ranking_geral WHERE passaro_id = %s LIMIT 1", (trans["passaro_id"],))
                tem_pontuacao = cur.fetchone()
                
                if tem_pontuacao:
                    cur.execute("UPDATE transferencias SET status = 'aprovado_admin' WHERE id = %s", (transferencia_id,))
                    cur.execute("UPDATE passaros SET socio_id = %s WHERE id = %s", (trans["socio_destino_id"], trans["passaro_id"]))
                else:
                    cur.execute("UPDATE passaros SET socio_id = %s WHERE id = %s", (trans["socio_destino_id"], trans["passaro_id"]))
                    cur.execute("UPDATE transferencias SET status = 'aprovado' WHERE id = %s", (transferencia_id,))
            else:
                trans = conn.execute(
                    "SELECT * FROM transferencias WHERE id = ? AND status = 'pendente'",
                    (transferencia_id,)
                ).fetchone()
                if not trans:
                    raise ValueError("Transferência não encontrada.")
                
                tem_pontuacao = conn.execute(
                    "SELECT id FROM ranking_geral WHERE passaro_id = ? LIMIT 1",
                    (trans["passaro_id"],)
                ).fetchone()
                
                if tem_pontuacao:
                    conn.execute(
                        "UPDATE transferencias SET status = 'aprovado_admin' WHERE id = ?",
                        (transferencia_id,)
                    )
                    conn.execute(
                        "UPDATE passaros SET socio_id = ? WHERE id = ?",
                        (trans["socio_destino_id"], trans["passaro_id"])
                    )
                else:
                    conn.execute(
                        "UPDATE passaros SET socio_id = ? WHERE id = ?",
                        (trans["socio_destino_id"], trans["passaro_id"])
                    )
                    conn.execute(
                        "UPDATE transferencias SET status = 'aprovado' WHERE id = ?",
                        (transferencia_id,)
                    )
            
            return True

    def recusar_transferencia_admin(self, transferencia_id):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute("UPDATE transferencias SET status = 'recusado_admin' WHERE id = %s AND status = 'pendente'", (transferencia_id,))
            else:
                conn.execute(
                    "UPDATE transferencias SET status = 'recusado_admin' WHERE id = ? AND status = 'pendente'",
                    (transferencia_id,)
                )
            return True

    # ================================================================
    # INSCRIÇÕES
    # ================================================================
    def inscrever_passaro_na_etapa(self, etapa_id, passaro_id, socio_id):
        etapa = self.obter_etapa(etapa_id)
        if etapa is None:
            raise ValueError("Etapa não encontrada.")
        
        if not etapa["inscricoes_abertas"]:
            raise regras.ErroValidacao("Inscrições para esta etapa estão encerradas.")

        total_inscritos = self.contar_inscricoes_na_etapa(etapa_id)
        if etapa.get("limite_inscricoes") is not None:
            if total_inscritos >= etapa["limite_inscricoes"]:
                raise regras.ErroValidacao(f"Limite de {etapa['limite_inscricoes']} inscrições atingido.")

        if etapa.get("prazo_pagamento"):
            try:
                prazo = datetime.datetime.fromisoformat(etapa["prazo_pagamento"])
                if datetime.datetime.now() > prazo:
                    raise regras.ErroValidacao("Prazo para pagamento já encerrou.")
            except:
                pass

        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("SELECT * FROM passaros WHERE id = %s", (passaro_id,))
                passaro = cur.fetchone()
            else:
                passaro = conn.execute(
                    "SELECT * FROM passaros WHERE id = ?", (passaro_id,)
                ).fetchone()
            
            if passaro is None:
                raise ValueError("Pássaro não encontrado.")
            if passaro["socio_id"] != socio_id:
                raise regras.ErroValidacao("Este pássaro não pertence a você.")

            # ================================================================
            # VERIFICAÇÃO DE CATEGORIA - CORRIGIDO PARA MISTO
            # ================================================================
            categoria_calculada = regras.calcular_categoria(passaro["codigo_ave"])
            categoria_etapa = etapa["categoria"]

            # Se a etapa for MISTO, aceita QUALQUER pássaro (filhote OU adulto)
            if categoria_etapa == "MISTO":
                # Aceita qualquer um, não faz verificação
                pass
            else:
                if categoria_calculada != categoria_etapa:
                    raise regras.ErroValidacao(
                        f"O pássaro é {categoria_calculada}, mas a etapa é {categoria_etapa}."
                    )

            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("SELECT * FROM socios WHERE id = %s", (socio_id,))
                socio = cur.fetchone()
            else:
                socio = conn.execute("SELECT * FROM socios WHERE id = ?", (socio_id,)).fetchone()
            
            if socio is None:
                raise ValueError("Sócio não encontrado.")

            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute("""
                    SELECT COUNT(*) AS total
                    FROM inscricoes i
                    JOIN passaros p ON p.id = i.passaro_id
                    JOIN socios s ON s.id = p.socio_id
                    WHERE i.etapa_id = %s AND s.cpf = %s
                """, (etapa_id, socio["cpf"]))
                ja_inscritos = cur.fetchone()["total"]
            else:
                ja_inscritos = conn.execute("""
                    SELECT COUNT(*) AS total
                    FROM inscricoes i
                    JOIN passaros p ON p.id = i.passaro_id
                    JOIN socios s ON s.id = p.socio_id
                    WHERE i.etapa_id = ? AND s.cpf = ?
                """, (etapa_id, socio["cpf"])).fetchone()["total"]
            
            regras.validar_limite_cpf(ja_inscritos, etapa["limite_por_cpf"])

            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute("SELECT id FROM inscricoes WHERE etapa_id = %s AND passaro_id = %s", (etapa_id, passaro_id))
                existente = cur.fetchone()
            else:
                existente = conn.execute(
                    "SELECT id FROM inscricoes WHERE etapa_id = ? AND passaro_id = ?",
                    (etapa_id, passaro_id)
                ).fetchone()
            
            if existente:
                raise ValueError("Este pássaro já está inscrito nesta etapa.")

            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute("SELECT ordem FROM inscricoes WHERE etapa_id = %s AND ordem IS NOT NULL", (etapa_id,))
                ordens_ocupadas = cur.fetchall()
            else:
                ordens_ocupadas = conn.execute(
                    "SELECT ordem FROM inscricoes WHERE etapa_id = ? AND ordem IS NOT NULL",
                    (etapa_id,)
                ).fetchall()
            
            ocupadas = {o["ordem"] for o in ordens_ocupadas}
            
            limite_inscricoes = etapa.get("limite_inscricoes")
            if limite_inscricoes is None:
                limite_inscricoes = total_inscritos + 10
            elif limite_inscricoes <= total_inscritos:
                raise regras.ErroValidacao("Limite de inscrições atingido.")
            
            disponiveis = []
            for i in range(1, limite_inscricoes + 1):
                if i not in ocupadas:
                    disponiveis.append(i)
            
            if not disponiveis:
                raise regras.ErroValidacao("Não há posições disponíveis para inscrição.")
            
            ordem_escolhida = random.choice(disponiveis)

            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO inscricoes (etapa_id, passaro_id, ordem, criado_em) VALUES (%s, %s, %s, %s) RETURNING id",
                    (etapa_id, passaro_id, ordem_escolhida, datetime.datetime.now().isoformat())
                )
                return cur.fetchone()[0]
            else:
                cursor = conn.execute(
                    "INSERT INTO inscricoes (etapa_id, passaro_id, ordem, criado_em) VALUES (?, ?, ?, ?)",
                    (etapa_id, passaro_id, ordem_escolhida, datetime.datetime.now().isoformat())
                )
                return cursor.lastrowid

    def cancelar_inscricao(self, inscricao_id, socio_id):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute("""
                    SELECT i.* FROM inscricoes i
                    JOIN passaros p ON p.id = i.passaro_id
                    WHERE i.id = %s AND p.socio_id = %s
                """, (inscricao_id, socio_id))
                inscricao = cur.fetchone()
            else:
                inscricao = conn.execute("""
                    SELECT i.* FROM inscricoes i
                    JOIN passaros p ON p.id = i.passaro_id
                    WHERE i.id = ? AND p.socio_id = ?
                """, (inscricao_id, socio_id)).fetchone()
            
            if not inscricao:
                if self.usar_postgres:
                    cur = conn.cursor()
                    cur.execute("SELECT * FROM inscricoes WHERE id = %s", (inscricao_id,))
                    inscricao = cur.fetchone()
                else:
                    inscricao = conn.execute(
                        "SELECT * FROM inscricoes WHERE id = ?",
                        (inscricao_id,)
                    ).fetchone()
                
                if not inscricao:
                    raise ValueError("Inscrição não encontrada.")
            
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute("DELETE FROM inscricoes WHERE id = %s", (inscricao_id,))
                cur.execute("DELETE FROM pagamentos WHERE inscricao_id = %s", (inscricao_id,))
                cur.execute("DELETE FROM resultados WHERE inscricao_id = %s", (inscricao_id,))
            else:
                conn.execute("DELETE FROM inscricoes WHERE id = ?", (inscricao_id,))
                conn.execute("DELETE FROM pagamentos WHERE inscricao_id = ?", (inscricao_id,))
                conn.execute("DELETE FROM resultados WHERE inscricao_id = ?", (inscricao_id,))
            
            return True

    def listar_inscricoes_do_socio(self, socio_id):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("""
                    SELECT 
                        i.id AS inscricao_id,
                        i.etapa_id,
                        i.ordem,
                        i.liberada_manual,
                        i.pagamento_confirmado,
                        i.criado_em,
                        p.id AS passaro_id,
                        p.nome AS passaro_nome,
                        p.codigo_ave,
                        e.nome AS etapa_nome,
                        e.data_etapa,
                        e.modalidade,
                        e.categoria,
                        e.info_pagamento,
                        e.prazo_pagamento,
                        t.nome AS torneio_nome,
                        t.endereco,
                        t.mapa_url,
                        pg.status AS pagamento_status,
                        pg.comprovante
                    FROM inscricoes i
                    JOIN passaros p ON p.id = i.passaro_id
                    JOIN etapas e ON e.id = i.etapa_id
                    LEFT JOIN torneios t ON t.id = e.torneio_id
                    LEFT JOIN pagamentos pg ON pg.inscricao_id = i.id
                    WHERE p.socio_id = %s
                    ORDER BY e.data_etapa DESC
                """, (socio_id,))
                linhas = cur.fetchall()
            else:
                linhas = conn.execute("""
                    SELECT 
                        i.id AS inscricao_id,
                        i.etapa_id,
                        i.ordem,
                        i.liberada_manual,
                        i.pagamento_confirmado,
                        i.criado_em,
                        p.id AS passaro_id,
                        p.nome AS passaro_nome,
                        p.codigo_ave,
                        e.nome AS etapa_nome,
                        e.data_etapa,
                        e.modalidade,
                        e.categoria,
                        e.info_pagamento,
                        e.prazo_pagamento,
                        t.nome AS torneio_nome,
                        t.endereco,
                        t.mapa_url,
                        pg.status AS pagamento_status,
                        pg.comprovante
                    FROM inscricoes i
                    JOIN passaros p ON p.id = i.passaro_id
                    JOIN etapas e ON e.id = i.etapa_id
                    LEFT JOIN torneios t ON t.id = e.torneio_id
                    LEFT JOIN pagamentos pg ON pg.inscricao_id = i.id
                    WHERE p.socio_id = ?
                    ORDER BY e.data_etapa DESC
                """, (socio_id,)).fetchall()
            return [dict(l) for l in linhas]

    def liberar_inscricao_manual(self, etapa_id, inscricao_id):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute(
                    "UPDATE inscricoes SET liberada_manual = 1 WHERE id = %s AND etapa_id = %s",
                    (inscricao_id, etapa_id)
                )
            else:
                conn.execute(
                    "UPDATE inscricoes SET liberada_manual = 1 WHERE id = ? AND etapa_id = ?",
                    (inscricao_id, etapa_id)
                )

    def listar_inscritos_na_etapa(self, etapa_id):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("""
                    SELECT 
                        i.id AS inscricao_id,
                        i.ordem,
                        i.liberada_manual,
                        i.pagamento_confirmado,
                        p.id AS passaro_id,
                        p.nome AS passaro_nome,
                        p.codigo_ave,
                        s.nome AS socio_nome,
                        s.cpf,
                        pg.status AS pagamento_status
                    FROM inscricoes i
                    JOIN passaros p ON p.id = i.passaro_id
                    JOIN socios s ON s.id = p.socio_id
                    LEFT JOIN pagamentos pg ON pg.inscricao_id = i.id
                    WHERE i.etapa_id = %s
                    ORDER BY i.ordem ASC NULLS LAST
                """, (etapa_id,))
                linhas = cur.fetchall()
            else:
                linhas = conn.execute("""
                    SELECT 
                        i.id AS inscricao_id,
                        i.ordem,
                        i.liberada_manual,
                        i.pagamento_confirmado,
                        p.id AS passaro_id,
                        p.nome AS passaro_nome,
                        p.codigo_ave,
                        s.nome AS socio_nome,
                        s.cpf,
                        pg.status AS pagamento_status
                    FROM inscricoes i
                    JOIN passaros p ON p.id = i.passaro_id
                    JOIN socios s ON s.id = p.socio_id
                    LEFT JOIN pagamentos pg ON pg.inscricao_id = i.id
                    WHERE i.etapa_id = ?
                    ORDER BY i.ordem ASC NULLS LAST
                """, (etapa_id,)).fetchall()
            return [dict(l) for l in linhas]

    # ================================================================
    # PAGAMENTOS
    # ================================================================
    def registrar_pagamento(self, inscricao_id, comprovante=None):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute("SELECT id FROM pagamentos WHERE inscricao_id = %s", (inscricao_id,))
                existe = cur.fetchone()
                
                if existe:
                    cur.execute("""
                        UPDATE pagamentos SET 
                            comprovante = %s, 
                            status = 'pendente',
                            data_pagamento = %s
                        WHERE inscricao_id = %s
                    """, (comprovante, datetime.datetime.now().isoformat(), inscricao_id))
                else:
                    cur.execute("""
                        INSERT INTO pagamentos (inscricao_id, comprovante, status, data_pagamento, criado_em)
                        VALUES (%s, %s, 'pendente', %s, %s)
                    """, (inscricao_id, comprovante, datetime.datetime.now().isoformat(), datetime.datetime.now().isoformat()))
            else:
                existe = conn.execute(
                    "SELECT id FROM pagamentos WHERE inscricao_id = ?",
                    (inscricao_id,)
                ).fetchone()
                
                if existe:
                    conn.execute("""
                        UPDATE pagamentos SET 
                            comprovante = ?, 
                            status = 'pendente',
                            data_pagamento = ?
                        WHERE inscricao_id = ?
                    """, (comprovante, datetime.datetime.now().isoformat(), inscricao_id))
                else:
                    conn.execute("""
                        INSERT INTO pagamentos (inscricao_id, comprovante, status, data_pagamento, criado_em)
                        VALUES (?, ?, 'pendente', ?, ?)
                    """, (inscricao_id, comprovante, datetime.datetime.now().isoformat(), datetime.datetime.now().isoformat()))

    def confirmar_pagamento(self, inscricao_id):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute("UPDATE pagamentos SET status = 'pago' WHERE inscricao_id = %s", (inscricao_id,))
                cur.execute("UPDATE inscricoes SET pagamento_confirmado = 1 WHERE id = %s", (inscricao_id,))
            else:
                conn.execute(
                    "UPDATE pagamentos SET status = 'pago' WHERE inscricao_id = ?",
                    (inscricao_id,)
                )
                conn.execute(
                    "UPDATE inscricoes SET pagamento_confirmado = 1 WHERE id = ?",
                    (inscricao_id,)
                )

    def recusar_pagamento(self, inscricao_id):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute("UPDATE pagamentos SET status = 'recusado' WHERE inscricao_id = %s", (inscricao_id,))
            else:
                conn.execute(
                    "UPDATE pagamentos SET status = 'recusado' WHERE inscricao_id = ?",
                    (inscricao_id,)
                )

    def verificar_pagamentos_pendentes(self):
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute("""
                    SELECT i.id, i.etapa_id
                    FROM inscricoes i
                    JOIN etapas e ON e.id = i.etapa_id
                    WHERE e.prazo_pagamento IS NOT NULL
                    AND e.prazo_pagamento < NOW()
                    AND i.pagamento_confirmado = 0
                    AND i.id NOT IN (
                        SELECT inscricao_id FROM pagamentos WHERE status = 'pago'
                    )
                """)
                expiradas = cur.fetchall()
            else:
                expiradas = conn.execute("""
                    SELECT i.id, i.etapa_id
                    FROM inscricoes i
                    JOIN etapas e ON e.id = i.etapa_id
                    WHERE e.prazo_pagamento IS NOT NULL
                    AND e.prazo_pagamento < datetime('now')
                    AND i.pagamento_confirmado = 0
                    AND i.id NOT IN (
                        SELECT inscricao_id FROM pagamentos WHERE status = 'pago'
                    )
                """).fetchall()
            
            for exp in expiradas:
                if self.usar_postgres:
                    cur = conn.cursor()
                    cur.execute("DELETE FROM inscricoes WHERE id = %s", (exp["id"],))
                    cur.execute("DELETE FROM pagamentos WHERE inscricao_id = %s", (exp["id"],))
                else:
                    conn.execute("DELETE FROM inscricoes WHERE id = ?", (exp["id"],))
                    conn.execute("DELETE FROM pagamentos WHERE inscricao_id = ?", (exp["id"],))
            
            return len(expiradas)

    # ================================================================
    # SORTEIO COM DISTÂNCIA MÍNIMA DE 5 POSIÇÕES
    # ================================================================
    def sortear_etapa(self, etapa_id):
        etapa = self.obter_etapa(etapa_id)
        if etapa is None:
            raise ValueError("Etapa não encontrada.")

        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) as total FROM inscricoes WHERE etapa_id = %s AND pagamento_confirmado = 0", (etapa_id,))
                nao_pagos = cur.fetchone()["total"]
            else:
                nao_pagos = conn.execute("""
                    SELECT COUNT(*) as total
                    FROM inscricoes i
                    WHERE i.etapa_id = ? AND i.pagamento_confirmado = 0
                """, (etapa_id,)).fetchone()["total"]
            
            if nao_pagos > 0:
                raise regras.ErroValidacao(f"Existem {nao_pagos} inscrições com pagamento pendente.")

        inscritos = self.listar_inscritos_na_etapa(etapa_id)
        if len(inscritos) < 2:
            raise regras.ErroValidacao("É necessário pelo menos 2 inscritos para sortear.")

        # Agrupa por CPF
        por_dono = {}
        for ins in inscritos:
            cpf = ins["cpf"]
            if cpf not in por_dono:
                por_dono[cpf] = []
            por_dono[cpf].append(ins)

        modalidade = etapa["modalidade"]

        # Busca etapas irmãs para Canto Livre
        etapas_irmas = []
        if etapa["torneio_id"]:
            todas_etapas = self.listar_etapas_do_torneio(etapa["torneio_id"])
            for e in todas_etapas:
                if e["id"] != etapa_id and e["modalidade"] == modalidade:
                    etapas_irmas.append(e)

        # Ordens ocupadas por CPF em etapas anteriores (Canto Livre)
        ordens_ocupadas_por_cpf = {}
        if modalidade == "CANTO_LIVRE":
            for e in etapas_irmas:
                inscritos_irma = self.listar_inscritos_na_etapa(e["id"])
                for ins in inscritos_irma:
                    if ins["ordem"] is not None:
                        cpf = ins["cpf"]
                        if cpf not in ordens_ocupadas_por_cpf:
                            ordens_ocupadas_por_cpf[cpf] = []
                        ordens_ocupadas_por_cpf[cpf].append(ins["ordem"])

        cpfs = list(por_dono.keys())
        num_passaros = len(inscritos)
        ordem_final = [None] * num_passaros

        # Quantos pássaros por dono
        quantos_por_dono = {cpf: len(por_dono[cpf]) for cpf in cpfs}
        
        # Ordena donos com mais pássaros primeiro
        donos_ordenados = sorted(cpfs, key=lambda x: quantos_por_dono[x], reverse=True)
        posicoes_disponiveis = list(range(1, num_passaros + 1))

        # ================================================================
        # DISTÂNCIA MÍNIMA = 5 POSIÇÕES
        # ================================================================
        DISTANCIA_MINIMA = 5

        def posicao_valida(pos, cpf, posicoes_ocupadas_por_dono):
            """Verifica se a posição é válida para o CPF - distância mínima de 5"""
            # Para Fibra: posições não podem ser próximas
            if modalidade == "FIBRA":
                for ocupada in posicoes_ocupadas_por_dono.get(cpf, []):
                    if abs(pos - ocupada) < DISTANCIA_MINIMA:
                        return False
            
            # Para Canto Livre: não pode repetir posição de etapas anteriores
            if modalidade == "CANTO_LIVRE":
                if cpf in ordens_ocupadas_por_cpf and pos in ordens_ocupadas_por_cpf[cpf]:
                    return False
                
                # Também verifica distância mínima para Canto Livre
                for ocupada in posicoes_ocupadas_por_dono.get(cpf, []):
                    if abs(pos - ocupada) < DISTANCIA_MINIMA:
                        return False
            
            return True

        # Distribui as posições garantindo distanciamento
        for cpf in donos_ordenados:
            qtd = quantos_por_dono[cpf]
            pos_ocupadas = []
            
            # Pega posições já ocupadas por este CPF
            for i, p in enumerate(ordem_final):
                if p == cpf:
                    pos_ocupadas.append(i + 1)
            
            for _ in range(qtd):
                # Filtra posições válidas (distância >= 5)
                validas = []
                for pos in posicoes_disponiveis:
                    if posicao_valida(pos, cpf, {cpf: pos_ocupadas}):
                        validas.append(pos)
                
                # Se não houver posições com distância 5, tenta com distância 3
                if not validas:
                    for pos in posicoes_disponiveis:
                        ok = True
                        for ocupada in pos_ocupadas:
                            if abs(pos - ocupada) < 3:
                                ok = False
                                break
                        if ok:
                            validas.append(pos)
                
                # Se ainda não tiver, usa distância 2
                if not validas:
                    for pos in posicoes_disponiveis:
                        ok = True
                        for ocupada in pos_ocupadas:
                            if abs(pos - ocupada) < 2:
                                ok = False
                                break
                        if ok:
                            validas.append(pos)
                
                # Se ainda não tiver, usa qualquer posição disponível
                if not validas:
                    validas = posicoes_disponiveis
                
                # Escolhe a posição que maximiza a distância das outras
                if len(validas) > 1 and pos_ocupadas:
                    melhor_pos = None
                    melhor_distancia = -1
                    for pos in validas:
                        min_dist = min(abs(pos - ocupada) for ocupada in pos_ocupadas)
                        if min_dist > melhor_distancia:
                            melhor_distancia = min_dist
                            melhor_pos = pos
                    if melhor_pos is not None:
                        pos_escolhida = melhor_pos
                    else:
                        pos_escolhida = random.choice(validas)
                else:
                    pos_escolhida = random.choice(validas)
                
                # Remove a posição escolhida e atualiza
                posicoes_disponiveis.remove(pos_escolhida)
                ordem_final[pos_escolhida - 1] = cpf
                pos_ocupadas.append(pos_escolhida)

        # Verifica se todos receberam posição
        for i, cpf in enumerate(ordem_final):
            if cpf is None:
                # Se algum ficou sem posição, coloca na primeira disponível
                for pos in posicoes_disponiveis:
                    if ordem_final[pos - 1] is None:
                        ordem_final[pos - 1] = cpfs[0] if cpfs else None
                        break

        # Monta resultado final
        resultado = []
        for pos, cpf in enumerate(ordem_final, 1):
            if cpf and cpf in por_dono and por_dono[cpf]:
                passaro = por_dono[cpf].pop(0)
                resultado.append({
                    "ordem": pos,
                    "passaro_id": passaro["passaro_id"],
                    "passaro_nome": passaro["passaro_nome"],
                    "codigo_ave": passaro["codigo_ave"],
                    "socio_nome": passaro["socio_nome"],
                    "cpf": passaro["cpf"],
                    "inscricao_id": passaro["inscricao_id"]
                })

        # Salva no banco
        with self._conexao() as conn:
            if self.usar_postgres:
                cur = conn.cursor()
                for item in resultado:
                    cur.execute(
                        "UPDATE inscricoes SET ordem = %s WHERE id = %s",
                        (item["ordem"], item["inscricao_id"])
                    )
                cur.execute(
                    "UPDATE etapas SET ordem_sorteada = 1 WHERE id = %s",
                    (etapa_id,)
                )
            else:
                for item in resultado:
                    conn.execute(
                        "UPDATE inscricoes SET ordem = ? WHERE id = ?",
                        (item["ordem"], item["inscricao_id"])
                    )
                conn.execute(
                    "UPDATE etapas SET ordem_sorteada = 1 WHERE id = ?",
                    (etapa_id,)
                )

        return resultado
