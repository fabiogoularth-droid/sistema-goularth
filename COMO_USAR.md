# Site do Clube — Inscrições e Resultados

## Como testar no seu notebook

1. Instale as dependências (uma vez só):
   ```
   pip install flask
   ```

2. Entre na pasta `site_clube` e rode:
   ```
   python app.py
   ```

3. Abra no navegador: `http://localhost:5000`

O programa cria automaticamente um arquivo `clube.db` na mesma pasta —
é o banco de dados com sócios, pássaros, torneios e inscrições. Não
precisa instalar nenhum banco de dados separado.

## Como usar

### Como sócio
1. Clique em **"Criar conta"**, preencha nome, CPF, email e senha.
2. Em **"Minha área"**, clique em **"+ Cadastrar pássaro"** e informe
   nome, anilha (ex: `2026-001`) e modalidade (Fibra ou Canto Livre).
   A categoria (Filhote/Adulto) é calculada automaticamente pelo ano
   da anilha — não precisa escolher.
3. Nos torneios com inscrições abertas, clique em **"Inscrever
   pássaro"** — só aparecem os pássaros compatíveis com aquele
   torneio.

### Como administrador (você)
1. Acesse `http://localhost:5000/admin/login`
2. Senha padrão: `admin123` (**troque isso** antes de usar de verdade
   — veja abaixo).
3. Em **"Gerenciar torneios"**, crie torneios informando nome, data,
   modalidade, categoria, e o limite de pássaros por CPF (deixe vazio
   para "sem limite").
4. Clique em **"Ver inscritos"** em qualquer torneio para ver a lista
   completa (com CPF) de quem se inscreveu.

## Trocar a senha de administrador

Antes de usar de verdade, troque a senha padrão. Você pode:
- Editar diretamente em `app.py`, a linha:
  ```python
  SENHA_ADMIN = os.environ.get("CLUBE_ADMIN_SENHA", "admin123")
  ```
  troque `"admin123"` pela senha que quiser.

## Estrutura dos arquivos

- `regras.py` — as regras de negócio (cálculo de categoria pela
  anilha, validações, limite por CPF). Testado isoladamente.
- `banco.py` — guarda tudo no arquivo `clube.db` (sócios, pássaros,
  torneios, inscrições).
- `app.py` — as páginas web (Flask) que usam os dois módulos acima.
- `templates/` — os arquivos HTML de cada página.

## Próximos passos (quando quiser evoluir)

Isso é a Versão 1, pensada para uso interno do seu clube. Algumas
evoluções naturais para o futuro, quando fizer sentido:
- Hospedar isso na internet de verdade (hoje só funciona no seu
  notebook/rede local) — posso te ajudar a escolher um serviço quando
  chegar a hora.
- Pagamento de inscrição direto no site (hoje é "fora do site", entre
  você e o sócio).
- Upload de fotos/vídeos dos pássaros e do evento.
- Resultados de prova vindos direto do Marcador Digital.
- Múltiplos clubes com seu próprio admin (hoje é só para o seu).
