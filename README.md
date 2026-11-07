# Apontamento — Repasse Robô

Sistema web para registrar repasses de solda nos aparelhos e listá-los na tela.

## Banco de dados
- `aparelhos` — `codigo` (PK, formato `000AAA`), `nome`. 25 aparelhos pré-cadastrados.
- `soldadores` — `letra` (PK, até 2 caracteres), `nome`. 10 soldadores pré-cadastrados.
- `repasses` — `aparelho` (→ aparelhos), `hora_inicio`, `hora_termino`, `letra` (→ soldadores), `observacoes` (opcional).

Os dados iniciais ficam em `app/db.py`. Para recriar o banco do zero, apague `instance/repasse.sqlite` e inicie o sistema novamente.

## Stack
- Python 3 + Flask
- SQLite (arquivo criado automaticamente em `instance/repasse.sqlite`)

## Estrutura
```
app/
  __init__.py      # create_app (fábrica da aplicação)
  db.py            # conexão e schema SQLite
  routes.py        # rotas (formulário + listagem)
  templates/       # HTML (Jinja2)
  static/css/      # estilos
instance/          # banco de dados (não versionado)
run.py             # ponto de entrada
requirements.txt
```

## Como rodar (Windows / PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```
Acesse http://127.0.0.1:5000
