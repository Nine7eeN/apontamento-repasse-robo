import re
import sqlite3
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

from .db import get_db

bp = Blueprint("repasse", __name__)

CAMPOS = ("aparelho", "hora_inicio", "hora_termino", "letra", "observacoes")
OBRIGATORIOS = ("aparelho", "hora_inicio", "hora_termino", "letra")


FILTROS = ("f_aparelho", "f_data_inicio", "f_data_termino", "f_letra", "f_soldador")


def _data_valida(valor):
    try:
        datetime.strptime(valor, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _parse(valor):
    try:
        return datetime.fromisoformat(valor)
    except (TypeError, ValueError):
        return None


@bp.route("/", methods=["GET", "POST"])
def index():
    db = get_db()
    aparelhos = db.execute("SELECT codigo, nome FROM aparelhos ORDER BY codigo").fetchall()
    soldadores = db.execute("SELECT letra, nome FROM soldadores ORDER BY letra").fetchall()
    form = {}

    if request.method == "POST":
        form = {k: request.form.get(k, "").strip() for k in CAMPOS}
        inicio, termino = _parse(form["hora_inicio"]), _parse(form["hora_termino"])

        if not all(form[k] for k in OBRIGATORIOS):
            flash("Preencha Aparelho, Hora de início, Hora de término e Letra.", "erro")
        elif form["aparelho"] not in {a["codigo"] for a in aparelhos}:
            flash("Aparelho inválido.", "erro")
        elif form["letra"] not in {s["letra"] for s in soldadores}:
            flash("Letra de soldador inválida.", "erro")
        elif not inicio or not termino:
            flash("Hora inválida.", "erro")
        elif termino <= inicio:
            flash("A hora de término deve ser posterior à hora de início.", "erro")
        else:
            db.execute(
                "INSERT INTO repasses (aparelho, hora_inicio, hora_termino, letra, observacoes)"
                " VALUES (?, ?, ?, ?, ?)",
                (form["aparelho"], form["hora_inicio"], form["hora_termino"],
                 form["letra"], form["observacoes"] or None),
            )
            db.commit()
            flash("Repasse registrado.", "ok")
            return redirect(url_for("repasse.index"))

    filtros = {k: request.args.get(k, "").strip() for k in FILTROS}
    condicoes, params = [], []
    if filtros["f_aparelho"]:
        condicoes.append("r.aparelho = ?")
        params.append(filtros["f_aparelho"])
    if filtros["f_data_inicio"] and _data_valida(filtros["f_data_inicio"]):
        condicoes.append("substr(r.hora_inicio, 1, 10) = ?")
        params.append(filtros["f_data_inicio"])
    if filtros["f_data_termino"] and _data_valida(filtros["f_data_termino"]):
        condicoes.append("substr(r.hora_termino, 1, 10) = ?")
        params.append(filtros["f_data_termino"])
    if filtros["f_letra"]:
        condicoes.append("r.letra = ?")
        params.append(filtros["f_letra"])
    if filtros["f_soldador"]:
        termo = filtros["f_soldador"].replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        condicoes.append("s.nome LIKE ? ESCAPE '\\'")
        params.append(f"%{termo}%")

    where = ("WHERE " + " AND ".join(condicoes)) if condicoes else ""
    registros = db.execute(
        f"""
        SELECT r.id, r.aparelho, r.hora_inicio, r.hora_termino, r.letra,
               s.nome AS soldador, r.observacoes
        FROM repasses r
        LEFT JOIN soldadores s ON s.letra = r.letra
        {where}
        ORDER BY r.hora_inicio DESC, r.id DESC
        """,
        params,
    ).fetchall()
    total = db.execute("SELECT COUNT(*) FROM repasses").fetchone()[0]
    return render_template("index.html", registros=registros, aparelhos=aparelhos,
                           soldadores=soldadores, form=form, filtros=filtros,
                           filtros_ativos={k: v for k, v in filtros.items() if v},
                           filtrando=bool(condicoes), total=total)


@bp.post("/repasses/<int:repasse_id>/excluir")
def excluir_repasse(repasse_id):
    db = get_db()
    cur = db.execute("DELETE FROM repasses WHERE id = ?", (repasse_id,))
    db.commit()
    if cur.rowcount:
        flash(f"Repasse #{repasse_id} excluído.", "ok")
    else:
        flash("Repasse não encontrado.", "erro")
    # Mantém os filtros que estavam ativos na listagem.
    filtros = {k: v for k in FILTROS if (v := request.args.get(k, "").strip())}
    return redirect(url_for("repasse.index", **filtros))


CODIGO_RE = re.compile(r"^[0-9]{3}[A-Z]{3}$")
LETRA_RE = re.compile(r"^[A-Z0-9]{1,2}$")


@bp.route("/cadastros")
def cadastros():
    db = get_db()
    aparelhos = db.execute(
        """
        SELECT a.codigo, a.nome, COUNT(r.id) AS usos
        FROM aparelhos a LEFT JOIN repasses r ON r.aparelho = a.codigo
        GROUP BY a.codigo ORDER BY a.codigo
        """
    ).fetchall()
    soldadores = db.execute(
        """
        SELECT s.letra, s.nome, COUNT(r.id) AS usos
        FROM soldadores s LEFT JOIN repasses r ON r.letra = s.letra
        GROUP BY s.letra ORDER BY s.letra
        """
    ).fetchall()
    return render_template("cadastros.html", aparelhos=aparelhos, soldadores=soldadores)


@bp.post("/cadastros/aparelhos")
def criar_aparelho():
    codigo = request.form.get("codigo", "").strip().upper()
    nome = request.form.get("nome", "").strip()
    db = get_db()
    if not (codigo and nome):
        flash("Preencha Código e Nome do aparelho.", "erro")
    elif not CODIGO_RE.match(codigo):
        flash("Código inválido: use 3 números seguidos de 3 letras (ex.: 100ABC).", "erro")
    elif db.execute("SELECT 1 FROM aparelhos WHERE codigo = ?", (codigo,)).fetchone():
        flash(f"Já existe um aparelho com o código {codigo}.", "erro")
    else:
        db.execute("INSERT INTO aparelhos (codigo, nome) VALUES (?, ?)", (codigo, nome))
        db.commit()
        flash(f"Aparelho {codigo} cadastrado.", "ok")
    return redirect(url_for("repasse.cadastros"))


@bp.post("/cadastros/aparelhos/<codigo>/excluir")
def excluir_aparelho(codigo):
    db = get_db()
    try:
        cur = db.execute("DELETE FROM aparelhos WHERE codigo = ?", (codigo,))
        db.commit()
    except sqlite3.IntegrityError:
        flash(f"O aparelho {codigo} possui repasses registrados e não pode ser excluído.", "erro")
    else:
        flash(f"Aparelho {codigo} excluído." if cur.rowcount else "Aparelho não encontrado.",
              "ok" if cur.rowcount else "erro")
    return redirect(url_for("repasse.cadastros"))


@bp.post("/cadastros/soldadores")
def criar_soldador():
    letra = request.form.get("letra", "").strip().upper()
    nome = request.form.get("nome", "").strip()
    db = get_db()
    if not (letra and nome):
        flash("Preencha Letra e Nome do soldador.", "erro")
    elif not LETRA_RE.match(letra):
        flash("Letra inválida: use 1 ou 2 caracteres (letras ou números).", "erro")
    elif db.execute("SELECT 1 FROM soldadores WHERE letra = ?", (letra,)).fetchone():
        flash(f"Já existe um soldador com a letra {letra}.", "erro")
    else:
        db.execute("INSERT INTO soldadores (letra, nome) VALUES (?, ?)", (letra, nome))
        db.commit()
        flash(f"Soldador {letra} cadastrado.", "ok")
    return redirect(url_for("repasse.cadastros"))


@bp.post("/cadastros/soldadores/<letra>/excluir")
def excluir_soldador(letra):
    db = get_db()
    try:
        cur = db.execute("DELETE FROM soldadores WHERE letra = ?", (letra,))
        db.commit()
    except sqlite3.IntegrityError:
        flash(f"O soldador {letra} possui repasses registrados e não pode ser excluído.", "erro")
    else:
        flash(f"Soldador {letra} excluído." if cur.rowcount else "Soldador não encontrado.",
              "ok" if cur.rowcount else "erro")
    return redirect(url_for("repasse.cadastros"))


DURACAO = "(julianday(r.hora_termino) - julianday(r.hora_inicio)) * 1440"
# Rampa sequencial (azul, claro -> escuro) em 6 faixas; texto branco a partir da 4ª.
FAIXAS_CORES = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95"]


@bp.route("/analise")
def analise():
    db = get_db()
    de = request.args.get("de", "").strip()
    ate = request.args.get("ate", "").strip()
    de = de if _data_valida(de) else ""
    ate = ate if _data_valida(ate) else ""

    cond, params = [], []
    if de:
        cond.append("substr(r.hora_inicio, 1, 10) >= ?")
        params.append(de)
    if ate:
        cond.append("substr(r.hora_inicio, 1, 10) <= ?")
        params.append(ate)
    on_extra = "".join(f" AND {c}" for c in cond)
    where = ("WHERE " + " AND ".join(cond)) if cond else ""

    geral = db.execute(
        f"SELECT COUNT(*) AS n, AVG({DURACAO}) AS media FROM repasses r {where}", params
    ).fetchone()

    por_aparelho = db.execute(
        f"""
        SELECT a.codigo, a.nome, COUNT(r.id) AS n, AVG({DURACAO}) AS media,
               MIN({DURACAO}) AS minimo, MAX({DURACAO}) AS maximo
        FROM aparelhos a
        LEFT JOIN repasses r ON r.aparelho = a.codigo{on_extra}
        GROUP BY a.codigo
        ORDER BY media DESC NULLS LAST, a.codigo
        """,
        params,
    ).fetchall()

    soldadores = db.execute(
        f"""
        SELECT s.letra, s.nome, COUNT(r.id) AS n, AVG({DURACAO}) AS media
        FROM soldadores s
        LEFT JOIN repasses r ON r.letra = s.letra{on_extra}
        GROUP BY s.letra
        ORDER BY s.letra
        """,
        params,
    ).fetchall()

    pares = {
        (p["aparelho"], p["letra"]): p
        for p in db.execute(
            f"""
            SELECT r.aparelho, r.letra, COUNT(*) AS n, AVG({DURACAO}) AS media
            FROM repasses r {where}
            GROUP BY r.aparelho, r.letra
            """,
            params,
        )
    }

    # Faixas de cor do mapa de calor, calculadas sobre as médias das combinações.
    medias = [p["media"] for p in pares.values()]
    lo, hi = (min(medias), max(medias)) if medias else (0, 0)
    passo = (hi - lo) / len(FAIXAS_CORES) or 1
    faixas = [
        {"cor": cor, "de": lo + i * passo, "ate": lo + (i + 1) * passo, "escuro": i >= 3}
        for i, cor in enumerate(FAIXAS_CORES)
    ]

    def faixa(valor):
        return faixas[min(int((valor - lo) / passo), len(faixas) - 1)]

    com_dados = [a for a in por_aparelho if a["n"]]
    sold_com_dados = [s for s in soldadores if s["n"]]
    destaques = {
        "aparelho_lento": com_dados[0] if com_dados else None,
        "aparelho_rapido": com_dados[-1] if com_dados else None,
        "soldador_rapido": min(sold_com_dados, key=lambda s: s["media"]) if sold_com_dados else None,
    }
    maior_media = max((a["media"] for a in com_dados), default=0)
    heat_aparelhos = sorted(por_aparelho, key=lambda a: a["codigo"])

    return render_template(
        "analise.html", geral=geral, por_aparelho=por_aparelho, heat_aparelhos=heat_aparelhos,
        soldadores=soldadores, pares=pares, faixas=faixas, faixa=faixa,
        destaques=destaques, maior_media=maior_media, de=de, ate=ate,
    )


@bp.app_template_filter("minutos")
def formatar_minutos(valor):
    if valor is None:
        return "—"
    total = round(valor)
    if total < 60:
        return f"{total} min"
    return f"{total // 60}h {total % 60:02d}min"


@bp.app_template_filter("datahora")
def formatar_datahora(valor):
    dt = _parse(valor)
    return dt.strftime("%d/%m/%Y %H:%M") if dt else valor
