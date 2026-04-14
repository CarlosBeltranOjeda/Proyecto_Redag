"""
Sistema REDAG Web - Inscripciones, Pagos, Torneos
Flask + Supabase
"""
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import os, json, base64
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = "redag2026secret"

SUPABASE_URL = "https://ongleupjxdbffjjjwjri.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9uZ2xldXBqeGRiZmZqamp3anJpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njg0MDA5MjUsImV4cCI6MjA4Mzk3NjkyNX0.IH1df8XAMxmFhx9kL9iKk-bYWp7yQWKaEYgSoiynjIU"

CATEGORIAS_TORNEO = ["Sub-6","Sub-8","Sub-10","Sub-12","Sub-14","Sub-16","Sub-18","Sub-20"]
CATEGORIAS_CLUB   = ["Infantil (5-11 anos)","Juvenil (12-20 anos)","Damas"]
MESES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
         "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

# ── Supabase helper ──────────────────────────────────────────────────
import urllib.request
import urllib.parse

def sb_request(method, table, data=None, params=None, row_id=None):
    """Hace peticiones a Supabase REST API"""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if row_id: url += f"?id=eq.{row_id}"
    elif params: url += "?" + urllib.parse.urlencode(params)

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            result = r.read().decode()
            return json.loads(result) if result else []
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"Supabase error {e.code}: {err}")
        return []
    except Exception as e:
        print(f"Request error: {e}")
        return []

def sb_get(table, params=None):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if params: url += "?" + urllib.parse.urlencode(params)
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"GET error: {e}")
        return []

def sb_post(table, data):
    return sb_request("POST", table, data)

def sb_patch(table, row_id, data):
    return sb_request("PATCH", table, data, row_id=row_id)

def sb_delete(table, row_id):
    return sb_request("DELETE", table, row_id=row_id)

# ══════════════════════════════════════════════════════
# RUTAS PRINCIPALES
# ══════════════════════════════════════════════════════

@app.route("/")
def index():
    return redirect(url_for("dashboard"))

@app.route("/dashboard")
def dashboard():
    jugadores = sb_get("redag_jugadores", {"select": "id,estado,categoria,sede_id"})
    pagos_mes  = sb_get("redag_pagos", {
        "select": "id,mensualidad",
        "mes": f"eq.{MESES[datetime.now().month-1]}",
        "anio": f"eq.{datetime.now().year}"
    })
    torneos = sb_get("redag_torneos", {"select": "id,nombre,estado"})
    stats = {
        "total_jugadores": len(jugadores),
        "nuevos": sum(1 for j in jugadores if j.get("estado")=="Nuevo"),
        "antiguos": sum(1 for j in jugadores if j.get("estado")=="Antiguo"),
        "pagos_mes": len(pagos_mes),
        "pendientes": len(jugadores) - len(pagos_mes),
        "torneos": len(torneos),
    }
    return render_template("dashboard.html", stats=stats,
                           mes_actual=MESES[datetime.now().month-1],
                           anio=datetime.now().year)

# ── JUGADORES ────────────────────────────────────────
@app.route("/jugadores")
def jugadores():
    filtro = request.args.get("q","")
    cat    = request.args.get("cat","Todas")
    params = {"select": "*,redag_sedes(nombre)", "order": "apellidos.asc"}
    rows   = sb_get("redag_jugadores", params)
    if filtro:
        filtro_l = filtro.lower()
        rows = [r for r in rows if filtro_l in r.get("nombres","").lower()
                or filtro_l in r.get("apellidos","").lower()]
    if cat != "Todas":
        rows = [r for r in rows if r.get("categoria") == cat]
    return render_template("jugadores.html", jugadores=rows,
                           categorias=CATEGORIAS_CLUB, filtro=filtro, cat=cat)

@app.route("/jugadores/nuevo", methods=["GET","POST"])
def nuevo_jugador():
    sedes = sb_get("redag_sedes", {"select": "id,nombre"})
    if request.method == "POST":
        d = request.form
        data = {
            "nombres":   d.get("nombres","").strip(),
            "apellidos": d.get("apellidos","").strip(),
            "edad":      int(d.get("edad",0)),
            "categoria": d.get("categoria"),
            "estado":    d.get("estado","Nuevo"),
            "celular":   d.get("celular","").strip(),
            "sede_id":   int(d.get("sede_id",1)),
            "fecha_reg": datetime.now().strftime("%d/%m/%Y")
        }
        sb_post("redag_jugadores", data)
        return redirect(url_for("jugadores"))
    return render_template("form_jugador.html", jugador=None,
                           categorias=CATEGORIAS_CLUB, sedes=sedes, titulo="Nuevo Jugador")

@app.route("/jugadores/editar/<int:jid>", methods=["GET","POST"])
def editar_jugador(jid):
    sedes = sb_get("redag_sedes", {"select": "id,nombre"})
    rows  = sb_get("redag_jugadores", {"select": "*", "id": f"eq.{jid}"})
    if not rows: return redirect(url_for("jugadores"))
    jugador = rows[0]
    if request.method == "POST":
        d = request.form
        data = {
            "nombres":   d.get("nombres","").strip(),
            "apellidos": d.get("apellidos","").strip(),
            "edad":      int(d.get("edad",0)),
            "categoria": d.get("categoria"),
            "estado":    d.get("estado"),
            "celular":   d.get("celular","").strip(),
            "sede_id":   int(d.get("sede_id",1)),
        }
        sb_patch("redag_jugadores", jid, data)
        return redirect(url_for("jugadores"))
    return render_template("form_jugador.html", jugador=jugador,
                           categorias=CATEGORIAS_CLUB, sedes=sedes, titulo="Editar Jugador")

@app.route("/jugadores/eliminar/<int:jid>", methods=["POST"])
def eliminar_jugador(jid):
    sb_delete("redag_jugadores", jid)
    return redirect(url_for("jugadores"))

@app.route("/jugadores/<int:jid>/historial")
def historial_jugador(jid):
    rows = sb_get("redag_jugadores", {"select": "*", "id": f"eq.{jid}"})
    if not rows: return redirect(url_for("jugadores"))
    jugador = rows[0]
    pagos   = sb_get("redag_pagos", {"select": "*", "jugador_id": f"eq.{jid}", "order": "anio.desc"})
    total   = sum(p.get("matricula",0)+p.get("mensualidad",0) for p in pagos)
    return render_template("historial.html", jugador=jugador, pagos=pagos, total=total)

# ── PAGOS ────────────────────────────────────────────
@app.route("/pagos")
def pagos():
    mes  = request.args.get("mes",  MESES[datetime.now().month-1])
    anio = request.args.get("anio", str(datetime.now().year))
    cat  = request.args.get("cat",  "Todas")
    params = {
        "select": "*,redag_jugadores(nombres,apellidos,categoria,estado)",
        "mes": f"eq.{mes}", "anio": f"eq.{anio}"
    }
    pagos_rows = sb_get("redag_pagos", params)
    jugadores  = sb_get("redag_jugadores", {"select": "id,nombres,apellidos,categoria,estado"})
    if cat != "Todas":
        jugadores = [j for j in jugadores if j.get("categoria")==cat]
    pagados_ids = {p["jugador_id"] for p in pagos_rows}
    total_mat = sum(p.get("matricula",0) for p in pagos_rows)
    total_men = sum(p.get("mensualidad",0) for p in pagos_rows)
    return render_template("pagos.html",
        jugadores=jugadores, pagos=pagos_rows, pagados_ids=pagados_ids,
        meses=MESES, mes=mes, anio=anio, cat=cat,
        categorias=CATEGORIAS_CLUB,
        total_mat=total_mat, total_men=total_men,
        pendientes=len(jugadores)-len(pagados_ids))

@app.route("/pagos/registrar", methods=["POST"])
def registrar_pago():
    d = request.form
    jid  = int(d.get("jugador_id"))
    mes  = d.get("mes")
    anio = int(d.get("anio"))
    mat  = float(d.get("matricula",0))
    men  = float(d.get("mensualidad",0))
    dia  = int(d.get("dia_pago", datetime.now().day))
    # Verificar si ya existe
    ex = sb_get("redag_pagos", {
        "select": "id",
        "jugador_id": f"eq.{jid}",
        "mes": f"eq.{mes}",
        "anio": f"eq.{anio}"
    })
    data = {
        "jugador_id": jid, "mes": mes, "anio": anio,
        "matricula": mat, "mensualidad": men,
        "dia_pago": dia,
        "fecha_pago": datetime.now().strftime("%d/%m/%Y")
    }
    if ex:
        sb_patch("redag_pagos", ex[0]["id"], data)
    else:
        sb_post("redag_pagos", data)
    return redirect(url_for("pagos", mes=mes, anio=anio))

@app.route("/pagos/eliminar/<int:pid>", methods=["POST"])
def eliminar_pago(pid):
    mes  = request.form.get("mes")
    anio = request.form.get("anio")
    sb_delete("redag_pagos", pid)
    return redirect(url_for("pagos", mes=mes, anio=anio))

# ── TORNEOS ──────────────────────────────────────────
@app.route("/torneos")
def torneos():
    rows = sb_get("redag_torneos", {"select": "*", "order": "fecha_inicio.desc"})
    return render_template("torneos.html", torneos=rows)

@app.route("/torneos/nuevo", methods=["GET","POST"])
def nuevo_torneo():
    if request.method == "POST":
        d = request.form
        data = {
            "nombre":       d.get("nombre","").strip(),
            "fecha_inicio": d.get("fecha_inicio",""),
            "fecha_fin":    d.get("fecha_fin",""),
            "sede":         d.get("sede","").strip(),
            "descripcion":  d.get("descripcion","").strip(),
            "estado":       d.get("estado","Planificado")
        }
        sb_post("redag_torneos", data)
        return redirect(url_for("torneos"))
    return render_template("form_torneo.html", torneo=None, titulo="Nuevo Torneo")

@app.route("/torneos/editar/<int:tid>", methods=["GET","POST"])
def editar_torneo(tid):
    rows = sb_get("redag_torneos", {"select": "*", "id": f"eq.{tid}"})
    if not rows: return redirect(url_for("torneos"))
    torneo = rows[0]
    if request.method == "POST":
        d = request.form
        data = {
            "nombre":       d.get("nombre","").strip(),
            "fecha_inicio": d.get("fecha_inicio",""),
            "fecha_fin":    d.get("fecha_fin",""),
            "sede":         d.get("sede","").strip(),
            "descripcion":  d.get("descripcion","").strip(),
            "estado":       d.get("estado")
        }
        sb_patch("redag_torneos", tid, data)
        return redirect(url_for("torneos"))
    return render_template("form_torneo.html", torneo=torneo, titulo="Editar Torneo")

@app.route("/torneos/eliminar/<int:tid>", methods=["POST"])
def eliminar_torneo(tid):
    sb_delete("redag_torneos", tid)
    return redirect(url_for("torneos"))

@app.route("/torneos/<int:tid>/jugadores")
def torneo_jugadores(tid):
    rows = sb_get("redag_torneos", {"select": "*", "id": f"eq.{tid}"})
    if not rows: return redirect(url_for("torneos"))
    torneo = rows[0]
    q = request.args.get("q","")
    cat_sel = request.args.get("cat","")
    # Jugadores inscritos en este torneo
    inscritos = sb_get("redag_torneo_jugadores", {
        "select": "*,redag_jugadores(id,nombres,apellidos,edad,ci,foto_url)",
        "torneo_id": f"eq.{tid}",
        "order": "categoria_torneo.asc"
    })
    inscritos_ids = {i["jugador_id"] for i in inscritos}
    # Todos los jugadores para buscar
    todos = sb_get("redag_jugadores", {"select": "id,nombres,apellidos,edad,categoria,estado"})
    if q:
        ql = q.lower()
        todos = [j for j in todos if ql in j.get("nombres","").lower()
                 or ql in j.get("apellidos","").lower()]
    return render_template("torneo_jugadores.html",
        torneo=torneo, inscritos=inscritos, inscritos_ids=inscritos_ids,
        todos=todos, categorias_torneo=CATEGORIAS_TORNEO,
        q=q, cat_sel=cat_sel)

@app.route("/torneos/<int:tid>/inscribir", methods=["POST"])
def inscribir_jugador(tid):
    d = request.form
    jid = int(d.get("jugador_id"))
    cat = d.get("categoria_torneo")
    # Verificar si ya está inscrito en esta categoría
    ex = sb_get("redag_torneo_jugadores", {
        "select": "id",
        "torneo_id": f"eq.{tid}",
        "jugador_id": f"eq.{jid}"
    })
    if not ex:
        sb_post("redag_torneo_jugadores", {
            "torneo_id": tid,
            "jugador_id": jid,
            "categoria_torneo": cat,
            "fecha_inscripcion": datetime.now().strftime("%Y-%m-%d")
        })
    return redirect(url_for("torneo_jugadores", tid=tid))

@app.route("/torneos/<int:tid>/desinscribir/<int:jid>", methods=["POST"])
def desinscribir_jugador(tid, jid):
    rows = sb_get("redag_torneo_jugadores", {
        "select": "id",
        "torneo_id": f"eq.{tid}",
        "jugador_id": f"eq.{jid}"
    })
    if rows:
        sb_delete("redag_torneo_jugadores", rows[0]["id"])
    return redirect(url_for("torneo_jugadores", tid=tid))

@app.route("/torneos/<int:tid>/jugador/<int:jid>/editar", methods=["POST"])
def editar_inscripcion(tid, jid):
    cat = request.form.get("categoria_torneo")
    rows = sb_get("redag_torneo_jugadores", {
        "select": "id",
        "torneo_id": f"eq.{tid}",
        "jugador_id": f"eq.{jid}"
    })
    if rows:
        sb_patch("redag_torneo_jugadores", rows[0]["id"], {"categoria_torneo": cat})
    return redirect(url_for("torneo_jugadores", tid=tid))

# ── CARNET / CARDEX ──────────────────────────────────
@app.route("/torneos/<int:tid>/jugador/<int:jid>/cardex")
def cardex_jugador(tid, jid):
    torneo_rows  = sb_get("redag_torneos", {"select": "*", "id": f"eq.{tid}"})
    jugador_rows = sb_get("redag_jugadores", {"select": "*", "id": f"eq.{jid}"})
    insc_rows    = sb_get("redag_torneo_jugadores", {
        "select": "*",
        "torneo_id": f"eq.{tid}",
        "jugador_id": f"eq.{jid}"
    })
    if not torneo_rows or not jugador_rows: return redirect(url_for("torneos"))
    torneo  = torneo_rows[0]
    jugador = jugador_rows[0]
    insc    = insc_rows[0] if insc_rows else {}
    return render_template("cardex.html", torneo=torneo, jugador=jugador, insc=insc)

@app.route("/torneos/<int:tid>/jugador/<int:jid>/cardex/pdf")
def cardex_pdf(tid, jid):
    from reportlab.lib.pagesizes import A5
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage, HRFlowable
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    import tempfile, urllib.request as ur

    torneo_rows  = sb_get("redag_torneos", {"select": "*", "id": f"eq.{tid}"})
    jugador_rows = sb_get("redag_jugadores", {"select": "*", "id": f"eq.{jid}"})
    insc_rows    = sb_get("redag_torneo_jugadores", {
        "select": "*", "torneo_id": f"eq.{tid}", "jugador_id": f"eq.{jid}"
    })
    if not torneo_rows or not jugador_rows:
        return "No encontrado", 404

    torneo  = torneo_rows[0]
    jugador = jugador_rows[0]
    insc    = insc_rows[0] if insc_rows else {}

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(tmp.name, pagesize=A5,
                            leftMargin=1.2*cm, rightMargin=1.2*cm,
                            topMargin=1*cm, bottomMargin=1*cm)
    elems = []
    az = colors.HexColor("#003399"); am = colors.HexColor("#FFD700")
    negro = colors.HexColor("#111"); gris = colors.HexColor("#555")
    gris_cl = colors.HexColor("#f5f5f5"); bl = colors.white

    # Header con logo
    LOGO = os.path.join(os.path.dirname(__file__), "static", "logo.jpg")
    logo_l = logo_r = None
    if os.path.exists(LOGO):
        try: logo_l = RLImage(LOGO, width=1.8*cm, height=1.8*cm)
        except: pass
    ps_hc = ParagraphStyle("hc", fontName="Helvetica", alignment=TA_CENTER, leading=14)
    centro = Paragraph(
        '<font color="#FFD700" size="12"><b>PROYECTO REDAG</b></font><br/>'
        '<font color="white" size="8">Escuela de Futbol de Salon - Villa Adela</font><br/>'
        '<font color="#aab4c8" size="7">CARDEX DE SELECCION</font>', ps_hc)
    hdr = [[logo_l or "", centro, logo_r or ""]]
    ht = Table(hdr, colWidths=[2*cm, None, 2*cm])
    ht.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),az),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
        ("LEFTPADDING",(0,0),(0,-1),6),("RIGHTPADDING",(2,0),(2,-1),6),
    ]))
    elems.append(ht)
    elems.append(HRFlowable(width="100%", thickness=2, color=am, spaceAfter=0.2*cm))
    elems.append(Spacer(1, 0.2*cm))

    # Mensaje de seleccion
    ps_msg = ParagraphStyle("msg", fontName="Helvetica-Bold", fontSize=9,
                            textColor=az, alignment=TA_CENTER)
    elems.append(Paragraph(
        "FELICITACIONES! Ha sido seleccionado para representar al", ps_msg))
    elems.append(Paragraph(
        "PROYECTO REDAG en el Torneo de la Asociacion de Futsal de El Alto",
        ParagraphStyle("msg2", fontName="Helvetica-Bold", fontSize=9,
                       textColor=az, alignment=TA_CENTER)))
    elems.append(Spacer(1, 0.3*cm))

    # Foto del jugador si existe
    foto_url = jugador.get("foto_url","")
    if foto_url:
        try:
            tmp_foto = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            ur.urlretrieve(foto_url, tmp_foto.name)
            foto = RLImage(tmp_foto.name, width=2.5*cm, height=3*cm)
        except: foto = None
    else: foto = None

    ps_lbl = ParagraphStyle("lbl", fontName="Helvetica-Bold", fontSize=8, textColor=az)
    ps_val = ParagraphStyle("val", fontName="Helvetica", fontSize=9, textColor=negro)
    ps_big = ParagraphStyle("big", fontName="Helvetica-Bold", fontSize=10, textColor=az)

    datos = [
        [Paragraph("N de Registro:", ps_lbl), Paragraph("REDAG-"+str(jid).zfill(4), ps_big)],
        [Paragraph("Nombre completo:", ps_lbl), Paragraph(jugador.get("nombres","")+" "+jugador.get("apellidos",""), ps_val)],
        [Paragraph("Carnet de Identidad:", ps_lbl), Paragraph(str(jugador.get("ci","—")), ps_val)],
        [Paragraph("Edad:", ps_lbl), Paragraph(str(jugador.get("edad",""))+" anos", ps_val)],
        [Paragraph("Categoria:", ps_lbl), Paragraph(insc.get("categoria_torneo","—"), ps_val)],
        [Paragraph("Torneo:", ps_lbl), Paragraph(torneo.get("nombre",""), ps_val)],
        [Paragraph("Fecha inscripcion:", ps_lbl), Paragraph(insc.get("fecha_inscripcion","—"), ps_val)],
    ]

    if foto:
        datos_tbl = Table([[foto, Table(datos, colWidths=[3*cm, None])]],
                          colWidths=[2.8*cm, None])
    else:
        datos_tbl = Table(datos, colWidths=[3.5*cm, None])

    datos_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),gris_cl),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("LEFTPADDING",(0,0),(-1,-1),6),
        ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#dde1e7")),
    ]))
    elems.append(datos_tbl)
    elems.append(Spacer(1, 0.4*cm))
    elems.append(HRFlowable(width="100%", thickness=0.5, color=am))
    elems.append(Spacer(1, 0.15*cm))

    ps_pie1 = ParagraphStyle("p1", fontName="Helvetica", fontSize=7, textColor=gris, alignment=TA_CENTER)
    ps_pie2 = ParagraphStyle("p2", fontName="Helvetica-BoldOblique", fontSize=8, textColor=az, alignment=TA_CENTER)
    elems.append(Paragraph("PROYECTO REDAG - MAS QUE UN EQUIPO, UNA FAMILIA", ps_pie2))
    elems.append(Paragraph("Villa Adela 'Paraiso'  |  Sistema REDAG  |  Generado: "+datetime.now().strftime("%d/%m/%Y"), ps_pie1))

    doc.build(elems)
    return send_file(tmp.name, as_attachment=True,
                     download_name=f"Cardex_{jugador.get('apellidos','')}_{jugador.get('nombres','')}.pdf",
                     mimetype="application/pdf")

@app.route("/torneos/<int:tid>/categoria/<cat>/lista/pdf")
def lista_categoria_pdf(tid, cat):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage, HRFlowable
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    import tempfile

    torneo_rows = sb_get("redag_torneos", {"select": "*", "id": f"eq.{tid}"})
    inscritos   = sb_get("redag_torneo_jugadores", {
        "select": "*,redag_jugadores(nombres,apellidos,edad,ci)",
        "torneo_id": f"eq.{tid}",
        "categoria_torneo": f"eq.{cat}",
        "order": "redag_jugadores(apellidos).asc"
    })
    if not torneo_rows: return "No encontrado", 404
    torneo = torneo_rows[0]

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(tmp.name, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=1.5*cm, bottomMargin=2*cm)
    elems = []
    az = colors.HexColor("#003399"); am = colors.HexColor("#FFD700")
    negro = colors.HexColor("#111"); gris = colors.HexColor("#555")
    gris_cl = colors.HexColor("#f5f7fa"); gris_md = colors.HexColor("#dde1e7")
    bl = colors.white

    LOGO = os.path.join(os.path.dirname(__file__), "static", "logo.jpg")
    logo_l = logo_r = None
    if os.path.exists(LOGO):
        try: logo_l = RLImage(LOGO, width=2*cm, height=2*cm)
        except: pass

    ps_hc = ParagraphStyle("hc", fontName="Helvetica", alignment=TA_CENTER, leading=16)
    centro = Paragraph(
        '<font color="#FFD700" size="14"><b>PROYECTO REDAG</b></font><br/>'
        '<font color="white" size="9">Torneo Asociacion de Futsal de El Alto</font><br/>'
        f'<font color="#aab4c8" size="9">LISTA OFICIAL - {cat.upper()}  |  {torneo.get("nombre","")}</font>',
        ps_hc)
    hdr = [[logo_l or "", centro, logo_r or ""]]
    ht = Table(hdr, colWidths=[2.4*cm, None, 2.4*cm])
    ht.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),az),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
        ("LEFTPADDING",(0,0),(0,-1),6),("RIGHTPADDING",(2,0),(2,-1),6),
    ]))
    elems.append(ht)
    elems.append(HRFlowable(width="100%", thickness=2, color=am, spaceAfter=0.3*cm))
    elems.append(Spacer(1, 0.2*cm))

    ps_hd = ParagraphStyle("hd", fontName="Helvetica-Bold", fontSize=9, textColor=bl, alignment=TA_CENTER)
    ps_td = ParagraphStyle("td", fontName="Helvetica", fontSize=9, textColor=negro, alignment=TA_CENTER)
    ps_tot = ParagraphStyle("tot", fontName="Helvetica-Bold", fontSize=10, textColor=az, alignment=TA_CENTER)

    heads = ["N","Nombres","Apellidos","Edad","Carnet de Identidad","Firma"]
    cw = [1*cm, 4.5*cm, 4.5*cm, 1.5*cm, 3.5*cm, 2.5*cm]
    data = [[Paragraph(h, ps_hd) for h in heads]]

    for i, ins in enumerate(inscritos, 1):
        jug = ins.get("redag_jugadores") or {}
        data.append([
            Paragraph(str(i), ps_td),
            Paragraph(jug.get("nombres","—"), ps_td),
            Paragraph(jug.get("apellidos","—"), ps_td),
            Paragraph(str(jug.get("edad","—")), ps_td),
            Paragraph(str(jug.get("ci","—")), ps_td),
            Paragraph("", ps_td),
        ])

    data.append([Paragraph("TOTAL",ps_tot),
                 Paragraph(str(len(inscritos))+" jugadores",ps_tot),
                 "","","",""])

    n = len(data)
    tbl = Table(data, colWidths=cw, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),az),
        ("ROWBACKGROUNDS",(0,1),(-1,n-2),[bl,gris_cl]),
        ("BACKGROUND",(0,n-1),(-1,n-1),colors.HexColor("#fff3cd")),
        ("GRID",(0,0),(-1,-1),0.4,gris_md),
        ("BOX",(0,0),(-1,-1),1,az),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
    ]))
    elems.append(tbl)
    elems.append(Spacer(1, 0.5*cm))
    elems.append(HRFlowable(width="100%", thickness=0.5, color=am))
    elems.append(Spacer(1, 0.15*cm))

    ps_pie1 = ParagraphStyle("p1", fontName="Helvetica", fontSize=7, textColor=gris, alignment=TA_CENTER)
    ps_pie2 = ParagraphStyle("p2", fontName="Helvetica-Bold", fontSize=7, textColor=az, alignment=TA_CENTER)
    elems.append(Paragraph(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}  |  PROYECTO REDAG - Torneo Asociacion Futsal El Alto", ps_pie1))
    elems.append(Paragraph("Sistema desarrollado por J.C. BELTRAN", ps_pie2))

    doc.build(elems)
    return send_file(tmp.name, as_attachment=True,
                     download_name=f"Lista_{cat}_{torneo.get('nombre','')}.pdf",
                     mimetype="application/pdf")

# ── API para sincronización offline ──────────────────
@app.route("/api/sync", methods=["GET"])
def api_sync():
    data = {
        "jugadores": sb_get("redag_jugadores", {"select": "*"}),
        "pagos": sb_get("redag_pagos", {"select": "*"}),
        "torneos": sb_get("redag_torneos", {"select": "*"}),
        "sedes": sb_get("redag_sedes", {"select": "*"}),
    }
    return jsonify(data)

@app.route("/api/jugador", methods=["POST"])
def api_nuevo_jugador():
    data = request.get_json()
    result = sb_post("redag_jugadores", data)
    return jsonify(result)

# ── SQL Setup ────────────────────────────────────────
@app.route("/setup")
def setup():
    """Muestra el SQL para crear las tablas en Supabase"""
    sql = """
-- Ejecuta esto en el SQL Editor de Supabase

CREATE TABLE IF NOT EXISTS redag_sedes (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    direccion TEXT DEFAULT '',
    activa BOOLEAN DEFAULT TRUE
);
INSERT INTO redag_sedes(nombre,direccion) VALUES
    ('Villa Adela','Villa Adela Paraiso'),
    ('Villa Bolivar','Villa Bolivar'),
    ('Amor de Dios','Amor de Dios')
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS redag_jugadores (
    id SERIAL PRIMARY KEY,
    nombres TEXT NOT NULL,
    apellidos TEXT NOT NULL,
    edad INTEGER,
    ci TEXT DEFAULT '',
    categoria TEXT,
    estado TEXT DEFAULT 'Nuevo',
    celular TEXT DEFAULT '',
    sede_id INTEGER REFERENCES redag_sedes(id),
    foto_url TEXT DEFAULT '',
    fecha_reg TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS redag_pagos (
    id SERIAL PRIMARY KEY,
    jugador_id INTEGER REFERENCES redag_jugadores(id) ON DELETE CASCADE,
    mes TEXT,
    anio INTEGER,
    matricula NUMERIC DEFAULT 0,
    mensualidad NUMERIC DEFAULT 0,
    dia_pago INTEGER,
    fecha_pago TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS redag_torneos (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    fecha_inicio TEXT,
    fecha_fin TEXT,
    sede TEXT DEFAULT '',
    descripcion TEXT DEFAULT '',
    estado TEXT DEFAULT 'Planificado',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS redag_torneo_jugadores (
    id SERIAL PRIMARY KEY,
    torneo_id INTEGER REFERENCES redag_torneos(id) ON DELETE CASCADE,
    jugador_id INTEGER REFERENCES redag_jugadores(id) ON DELETE CASCADE,
    categoria_torneo TEXT,
    fecha_inscripcion TEXT,
    UNIQUE(torneo_id, jugador_id)
);

-- Permisos para la API
ALTER TABLE redag_sedes ENABLE ROW LEVEL SECURITY;
ALTER TABLE redag_jugadores ENABLE ROW LEVEL SECURITY;
ALTER TABLE redag_pagos ENABLE ROW LEVEL SECURITY;
ALTER TABLE redag_torneos ENABLE ROW LEVEL SECURITY;
ALTER TABLE redag_torneo_jugadores ENABLE ROW LEVEL SECURITY;

CREATE POLICY "allow_all_sedes" ON redag_sedes FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "allow_all_jugadores" ON redag_jugadores FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "allow_all_pagos" ON redag_pagos FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "allow_all_torneos" ON redag_torneos FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "allow_all_torneo_jug" ON redag_torneo_jugadores FOR ALL USING (true) WITH CHECK (true);
    """
    return f"<pre style='background:#111;color:#0f0;padding:20px;font-size:12px'>{sql}</pre>"

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
