# -*- coding: utf-8 -*-
"""
CONFIGURAÇÃO DO BANCO DE DADOS
================================
Força o uso do PostgreSQL no Render.
"""

import os

def configurar_database():
    """
    Garante que a DATABASE_URL esteja configurada.
    - Se já existir, usa a existente
    - Se não existir, usa a URL do PostgreSQL no Render
    """
    
    # Se a variável já existe, mantém
    if os.environ.get("DATABASE_URL"):
        print("🐘 Usando DATABASE_URL existente")
        return
    
    # ================================================================
    # FORÇAR POSTGRESQL NO RENDER
    # ================================================================
    
    # Verifica se está no Render
    is_render = os.environ.get("RENDER") or "onrender.com" in os.environ.get("RENDER_EXTERNAL_URL", "")
    
    if is_render:
        # URL do seu banco PostgreSQL no Render
        DATABASE_URL = "postgresql://sistema_goularth_db_user:62O0R8crJ7qGOiQy8DWAgjValTrBXYc5@dpg-d92nvi3tqb8s73chfn70-a.oregon-postgres.render.com/sistema_goularth_db"
        
        os.environ["DATABASE_URL"] = DATABASE_URL
        print("🔧 DATABASE_URL configurada FORÇADAMENTE para PostgreSQL no Render")
    else:
        # Se não estiver no Render, tenta usar SQLite local
        print("💾 Executando localmente - usando SQLite")

# Executa a configuração quando o arquivo é importado
configurar_database()