import sqlite3

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS aparelhos (
    codigo  TEXT PRIMARY KEY CHECK (codigo GLOB '[0-9][0-9][0-9][A-Z][A-Z][A-Z]'),
    nome    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS soldadores (
    letra   TEXT PRIMARY KEY CHECK (length(letra) BETWEEN 1 AND 2),
    nome    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS repasses (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    aparelho      TEXT NOT NULL REFERENCES aparelhos(codigo),
    hora_inicio   TEXT NOT NULL,
    hora_termino  TEXT NOT NULL,
    letra         TEXT NOT NULL REFERENCES soldadores(letra),
    observacoes   TEXT,
    criado_em     TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

APARELHOS = [
    ("100LEG", "Leg Press 45°"),
    ("110HAC", "Hack Squat"),
    ("120CAD", "Cadeira Extensora"),
    ("130MES", "Mesa Flexora"),
    ("140CFX", "Cadeira Flexora"),
    ("150ABD", "Cadeira Abdutora"),
    ("160ADU", "Cadeira Adutora"),
    ("170PAN", "Panturrilha em Pé"),
    ("180GLU", "Glúteo Máquina"),
    ("200SUP", "Supino Reto Articulado"),
    ("210SIN", "Supino Inclinado Articulado"),
    ("220CRU", "Crucifixo Máquina (Peck Deck)"),
    ("230CRO", "Crossover"),
    ("240PUX", "Puxador Frontal (Pulldown)"),
    ("250REM", "Remada Baixa"),
    ("260RCV", "Remada Cavalinho"),
    ("270DES", "Desenvolvimento Articulado"),
    ("280ELV", "Elevação Lateral Máquina"),
    ("290BIC", "Rosca Bíceps Máquina"),
    ("300TRI", "Tríceps Máquina"),
    ("310PAR", "Paralela Assistida"),
    ("320SMI", "Smith Machine"),
    ("330BCA", "Banco Abdominal"),
    ("340LOM", "Banco Lombar (Hiperextensão)"),
    ("350GAI", "Gaiola de Agachamento (Power Rack)"),
]

SOLDADORES = [
    ("A", "João Silva"),
    ("B", "Carlos Souza"),
    ("C", "Marcos Oliveira"),
    ("D", "Pedro Santos"),
    ("E", "Lucas Pereira"),
    ("F", "Rafael Costa"),
    ("G", "André Rodrigues"),
    ("H", "Fernando Almeida"),
    ("JL", "José Lima"),
    ("PR", "Paulo Ribeiro"),
]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(SCHEMA)
    db.executemany("INSERT OR IGNORE INTO aparelhos (codigo, nome) VALUES (?, ?)", APARELHOS)
    db.executemany("INSERT OR IGNORE INTO soldadores (letra, nome) VALUES (?, ?)", SOLDADORES)
    db.commit()


def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()
