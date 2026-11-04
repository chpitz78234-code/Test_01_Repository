"""
Leuchtkugel mit Glitzerspur – Szenengenerator für Blender (EEVEE)
=================================================================

Erzeugt eine komplette Szene: eine leuchtende Weihnachtskugel fliegt entlang
eines frei editierbaren Bezier-Pfads und hinterlässt eine glitzernde, langsam
herabrieselnde Funkenspur – gerendert auf schwarzem Hintergrund.

Ausführen
---------
* In Blender:  Scripting-Tab → Skript öffnen → "Run Script"
* Headless:    blender -b -P create_scene.py -- [ausgabe.blend]

Getestet mit Blender 5.2 LTS (EEVEE). Gedacht für Blender 5.x; in älteren
Versionen fehlt u. a. die neue Compositor-API (dann wird der Glow übersprungen)
und einzelne Node-Sockets können anders heißen.

Alles Wichtige wird am Objekt "Glitzerspur" im Modifier-Panel
(Geometry Nodes) eingestellt – siehe README.md.
"""

import math
import sys

import bpy

# ---------------------------------------------------------------------------
# Grundeinstellungen
# ---------------------------------------------------------------------------
FPS = 30
FRAME_START = 1
FRAME_END = 180           # Gesamtlänge der Animation (6 s)
FLUG_START = 1            # Kugel startet
FLUG_ENDE = 120           # Kugel erreicht das Pfadende
AUFLOESUNG = (1920, 1080)

# Pfad (X = links/rechts, Z = oben/unten, Kamera blickt entlang +Y)
# angelehnt an die Referenz: unten rechts rein, links herum, oben drüber,
# rechts nach innen einkringelnd.
PFAD_PUNKTE = [
    (4.6, 0.0, -3.4),
    (1.2, 0.0, -2.7),
    (-2.4, 0.0, -1.6),
    (-3.1, 0.0, 0.9),
    (-1.3, 0.0, 2.6),
    (1.2, 0.0, 2.2),
    (1.9, 0.0, 0.2),
]


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------
def sock(sockets, name, nth=0):
    """Gibt den n-ten *aktiven* Socket mit diesem Namen zurück."""
    found = [s for s in sockets if s.name == name and s.enabled]
    if not found:
        found = [s for s in sockets if s.name == name]
    return found[nth]


class NB:
    """Kleiner Builder, damit Node-Bäume per Code lesbar bleiben."""

    def __init__(self, tree):
        self.t = tree
        self.x = 0

    def node(self, idname, loc=None, **props):
        n = self.t.nodes.new(idname)
        for k, v in props.items():
            setattr(n, k, v)
        if loc:
            n.location = loc
        else:
            n.location = (self.x, 0)
            self.x += 30
        return n

    def link(self, a, b):
        self.t.links.new(a, b)

    def _in(self, sockets, i, v):
        s = sockets[i] if isinstance(i, int) else sock(sockets, i)
        if hasattr(v, "is_output"):
            self.link(v, s)
        else:
            s.default_value = v

    # Mathe ------------------------------------------------------------------
    def math(self, op, a, b=None, c=None, clamp=False):
        n = self.node("ShaderNodeMath", operation=op, use_clamp=clamp)
        ins = [s for s in n.inputs if s.enabled]
        for i, v in enumerate((a, b, c)):
            if v is not None:
                self._in(ins, i, v)
        return n.outputs[0]

    def add(self, a, b): return self.math("ADD", a, b)
    def sub(self, a, b): return self.math("SUBTRACT", a, b)
    def mul(self, a, b): return self.math("MULTIPLY", a, b)
    def div(self, a, b): return self.math("DIVIDE", a, b)
    def pow(self, a, b): return self.math("POWER", a, b)
    def mx(self, a, b): return self.math("MAXIMUM", a, b)
    def mn(self, a, b): return self.math("MINIMUM", a, b)
    def clamp01(self, a): return self.math("ADD", a, 0.0, clamp=True)

    def vmath(self, op, a, b=None, scale=None):
        n = self.node("ShaderNodeVectorMath", operation=op)
        ins = [s for s in n.inputs if s.enabled]
        self._in(ins, 0, a)
        idx = 1
        if b is not None:
            self._in(ins, 1, b)
            idx = 2
        if scale is not None:
            sc = sock(n.inputs, "Scale")
            self._in([sc], 0, scale)
        out = sock(n.outputs, "Vector") if op != "LENGTH" else sock(n.outputs, "Value")
        return out

    def vadd(self, a, b): return self.vmath("ADD", a, b)
    def vscale(self, a, s): return self.vmath("SCALE", a, scale=s)

    def combine(self, x=0.0, y=0.0, z=0.0):
        n = self.node("ShaderNodeCombineXYZ")
        for i, v in enumerate((x, y, z)):
            self._in(n.inputs, i, v)
        return n.outputs[0]

    def rand_float(self, mn, mx_, idfield, seed):
        n = self.node("FunctionNodeRandomValue", data_type="FLOAT")
        self._in(n.inputs, "Min", mn)
        self._in(n.inputs, "Max", mx_)
        self._in(n.inputs, "ID", idfield)
        self._in(n.inputs, "Seed", seed)
        return sock(n.outputs, "Value")

    def rand_vec(self, mn, mx_, idfield, seed):
        n = self.node("FunctionNodeRandomValue", data_type="FLOAT_VECTOR")
        self._in(n.inputs, "Min", mn)
        self._in(n.inputs, "Max", mx_)
        self._in(n.inputs, "ID", idfield)
        self._in(n.inputs, "Seed", seed)
        return sock(n.outputs, "Value")

    def switch_float(self, cond, false, true):
        n = self.node("GeometryNodeSwitch", input_type="FLOAT")
        self._in(n.inputs, "Switch", cond)
        self._in(n.inputs, "False", false)
        self._in(n.inputs, "True", true)
        return n.outputs[0]

    def compare(self, op, a, b):
        n = self.node("FunctionNodeCompare", data_type="FLOAT", operation=op)
        ins = [s for s in n.inputs if s.enabled]
        self._in(ins, 0, a)
        self._in(ins, 1, b)
        return n.outputs[0]

    def bool_op(self, op, a, b=None):
        n = self.node("FunctionNodeBooleanMath", operation=op)
        self._in(n.inputs, 0, a)
        if b is not None:
            self._in(n.inputs, 1, b)
        return n.outputs[0]

    def sample_curve(self, curve, factor):
        n = self.node("GeometryNodeSampleCurve", mode="FACTOR")
        n.use_all_curves = True
        self.link(curve, sock(n.inputs, "Curves"))
        self._in(n.inputs, "Factor", factor)
        return n


# ---------------------------------------------------------------------------
# Szene leeren
# ---------------------------------------------------------------------------
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene


# ---------------------------------------------------------------------------
# Pfad
# ---------------------------------------------------------------------------
def make_path():
    cu = bpy.data.curves.new("Kugel_Pfad", "CURVE")
    cu.dimensions = "3D"
    cu.resolution_u = 64
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(PFAD_PUNKTE) - 1)
    for bp, co in zip(sp.bezier_points, PFAD_PUNKTE):
        bp.co = co
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    ob = bpy.data.objects.new("Kugel_Pfad", cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.hide_render = True        # der Pfad selbst wird nicht gerendert
    return ob


# ---------------------------------------------------------------------------
# Materialien (alle additiv: Emission + Transparent, "Blended")
# ---------------------------------------------------------------------------
def additive_material(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    m.surface_render_method = "BLENDED"
    m.use_backface_culling = True
    if hasattr(m, "use_transparency_overlap"):
        m.use_transparency_overlap = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (900, 0)
    add = nt.nodes.new("ShaderNodeAddShader"); add.location = (700, 0)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); tr.location = (500, 120)
    em = nt.nodes.new("ShaderNodeEmission"); em.location = (500, -60)
    nt.links.new(tr.outputs[0], add.inputs[0])
    nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs["Surface"])
    # weicher Rand: Mitte (zur Kamera) hell, Rand dunkel → runde "Bokeh"-Punkte
    lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.location = (-300, -250)
    lw.inputs["Blend"].default_value = 0.5
    inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.location = (-100, -250)
    inv.inputs[0].default_value = 1.0
    nt.links.new(lw.outputs["Facing"], inv.inputs[1])
    soft = nt.nodes.new("ShaderNodeMath"); soft.operation = "POWER"; soft.location = (80, -250)
    nt.links.new(inv.outputs[0], soft.inputs[0])
    soft.inputs[1].default_value = 1.6
    return m, nt, em, soft


def attr_node(nt, name, loc):
    a = nt.nodes.new("ShaderNodeAttribute")
    a.attribute_type = "INSTANCER"
    a.attribute_name = name
    a.location = loc
    return a


def make_spark_material():
    m, nt, em, soft = additive_material("Funken")
    farbe = attr_node(nt, "farbe", (-500, 200))
    alter = attr_node(nt, "alter", (-500, 0))
    glow = attr_node(nt, "glow", (-500, -450))

    ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.location = (-250, 250)
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, (1.0, 0.22, 0.02, 1)    # tiefes Orange
    els[1].position, els[1].color = 1.0, (1.0, 1.0, 1.0, 1)      # Weiß
    for pos, col in [(0.40, (1.0, 0.40, 0.04, 1)),               # Orange-Gold
                     (0.72, (1.0, 0.62, 0.14, 1)),               # Gold
                     (0.94, (1.0, 0.85, 0.50, 1))]:              # Hellgold
        e = els.new(pos); e.color = col
    nt.links.new(farbe.outputs["Fac"], ramp.inputs["Fac"])

    # ältere Funken werden silbriger / kühler (wie das Ende der Spur in der Referenz)
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.location = (100, 200)
    mix.blend_type = "MIX"
    fac = nt.nodes.new("ShaderNodeMath"); fac.operation = "MULTIPLY"; fac.location = (-100, 0)
    nt.links.new(alter.outputs["Fac"], fac.inputs[0]); fac.inputs[1].default_value = 0.55
    nt.links.new(fac.outputs[0], sock(mix.inputs, "Factor"))
    nt.links.new(ramp.outputs["Color"], sock(mix.inputs, "A"))
    sock(mix.inputs, "B").default_value = (0.85, 0.88, 1.0, 1)
    nt.links.new(sock(mix.outputs, "Result"), em.inputs["Color"])

    st = nt.nodes.new("ShaderNodeMath"); st.operation = "MULTIPLY"; st.location = (300, -300)
    nt.links.new(glow.outputs["Fac"], st.inputs[0])
    nt.links.new(soft.outputs[0], st.inputs[1])
    nt.links.new(st.outputs[0], em.inputs["Strength"])
    return m


def make_simple_glow_material(name, color, strength, softness):
    m, nt, em, soft = additive_material(name)
    soft.inputs[1].default_value = softness
    em.inputs["Color"].default_value = color
    st = nt.nodes.new("ShaderNodeMath"); st.operation = "MULTIPLY"; st.location = (300, -300)
    nt.links.new(soft.outputs[0], st.inputs[0])
    st.inputs[1].default_value = strength
    nt.links.new(st.outputs[0], em.inputs["Strength"])
    return m


# ---------------------------------------------------------------------------
# Geometry Nodes: Kugel + Schweif + Glitzerspur
# ---------------------------------------------------------------------------
def make_gn_tree(path_obj, mats):
    t = bpy.data.node_groups.new("Leuchtkugel_Glitzerspur", "GeometryNodeTree")
    t.is_modifier = True
    iface = t.interface
    iface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    iface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")

    def inp(name, typ, default, mn=None, mx=None, desc="", sub=None, panel=None):
        s = iface.new_socket(name, in_out="INPUT", socket_type=typ, parent=panel)
        if default is not None:
            s.default_value = default
        if mn is not None:
            s.min_value = mn
        if mx is not None:
            s.max_value = mx
        if sub:
            s.subtype = sub
        s.description = desc
        return s

    p_anim = iface.new_panel("Pfad & Timing")
    inp("Pfad", "NodeSocketObject", path_obj, desc="Bezier-Kurve, der die Kugel folgt", panel=p_anim)
    inp("Start Frame", "NodeSocketFloat", float(FLUG_START), desc="Frame, an dem die Kugel losfliegt", panel=p_anim)
    inp("Ende Frame", "NodeSocketFloat", float(FLUG_ENDE), desc="Frame, an dem die Kugel das Pfadende erreicht (kleiner = schneller)", panel=p_anim)
    inp("Ease In/Out", "NodeSocketBool", True, desc="Weich beschleunigen und abbremsen statt konstanter Geschwindigkeit", panel=p_anim)
    inp("Bildrate", "NodeSocketFloat", float(FPS), 1, 240, desc="Muss der Szenen-Bildrate entsprechen", panel=p_anim)

    p_ball = iface.new_panel("Kugel")
    inp("Kugel sichtbar", "NodeSocketBool", True, panel=p_ball)
    inp("Kugel Größe", "NodeSocketFloat", 0.07, 0, 10, sub="DISTANCE", panel=p_ball)
    inp("Halo Größe", "NodeSocketFloat", 0.3, 0, 10, sub="DISTANCE", panel=p_ball)
    inp("Schweif Länge", "NodeSocketFloat", 1.6, 0, 100, sub="DISTANCE", desc="Länge des hellen, dünnen Leuchtstreifens direkt hinter der Kugel", panel=p_ball)
    inp("Schweif Dicke", "NodeSocketFloat", 0.022, 0, 10, sub="DISTANCE", panel=p_ball)

    p_sp = iface.new_panel("Glitzerspur")
    inp("Anzahl Funken", "NodeSocketInt", 9000, 0, 200000, desc="Gesamtzahl der Funken entlang des ganzen Pfads", panel=p_sp)
    inp("Funken Größe", "NodeSocketFloat", 0.022, 0, 10, sub="DISTANCE", panel=p_sp)
    inp("Größen-Variation", "NodeSocketFloat", 4.0, 1, 20, desc="Höher = wenige große Bokeh-Punkte, viele kleine", panel=p_sp)
    inp("Breite am Kopf", "NodeSocketFloat", 0.03, 0, 10, sub="DISTANCE", panel=p_sp)
    inp("Ausbreitung", "NodeSocketFloat", 0.22, 0, 10, desc="Wie stark die Spur mit der Zeit auffächert (Einheiten pro Sekunde)", panel=p_sp)
    inp("Schwerkraft", "NodeSocketFloat", 0.12, -10, 10, desc="Herabrieseln der Funken (Einheiten / s²)", panel=p_sp)
    inp("Drift", "NodeSocketFloat", 0.06, 0, 10, desc="Zufällige Eigenbewegung der Funken", panel=p_sp)
    inp("Turbulenz", "NodeSocketFloat", 0.12, 0, 10, panel=p_sp)
    inp("Lebensdauer", "NodeSocketFloat", 4.5, 0.01, 1000, desc="Mittlere Lebensdauer eines Funkens in Sekunden", panel=p_sp)
    inp("Funkeln", "NodeSocketFloat", 0.55, 0, 1, sub="FACTOR", desc="Stärke des Flackerns", panel=p_sp)
    inp("Helligkeit", "NodeSocketFloat", 1.5, 0, 1000, panel=p_sp)
    inp("Seed", "NodeSocketInt", 0, panel=p_sp)

    b = NB(t)
    gin = b.node("NodeGroupInput", loc=(-2000, 0))
    gout = b.node("NodeGroupOutput", loc=(2400, 0))
    G = lambda n: gin.outputs[n]

    # Pfad holen ---------------------------------------------------------------
    oi = b.node("GeometryNodeObjectInfo", transform_space="RELATIVE")
    b.link(G("Pfad"), sock(oi.inputs, "Object"))
    curve = sock(oi.outputs, "Geometry")
    clen = b.node("GeometryNodeCurveLength")
    b.link(curve, clen.inputs[0])
    L = clen.outputs[0]

    # Zeit ---------------------------------------------------------------------
    st = b.node("GeometryNodeInputSceneTime")
    frame = sock(st.outputs, "Frame")
    dur = b.mx(b.sub(G("Ende Frame"), G("Start Frame")), 0.001)
    lin = b.clamp01(b.div(b.sub(frame, G("Start Frame")), dur))
    smooth = b.mul(b.mul(lin, lin), b.sub(3.0, b.mul(2.0, lin)))      # smoothstep
    prog = b.switch_float(G("Ease In/Out"), lin, smooth)

    # ===== Kugel ================================================================
    head_pos = sock(b.sample_curve(curve, prog).outputs, "Position")
    pt = b.node("GeometryNodePoints")
    sock(pt.inputs, "Count").default_value = 1
    b.link(head_pos, sock(pt.inputs, "Position"))

    def ball_layer(radius_sock, mat, subdiv):
        ico = b.node("GeometryNodeMeshIcoSphere")
        sock(ico.inputs, "Radius").default_value = 1.0
        sock(ico.inputs, "Subdivisions").default_value = subdiv
        iop = b.node("GeometryNodeInstanceOnPoints")
        b.link(pt.outputs[0], sock(iop.inputs, "Points"))
        b.link(sock(ico.outputs, "Mesh"), sock(iop.inputs, "Instance"))
        b.link(radius_sock, sock(iop.inputs, "Scale"))
        sm = b.node("GeometryNodeSetMaterial")
        b.link(iop.outputs[0], sock(sm.inputs, "Geometry"))
        sock(sm.inputs, "Material").default_value = mat
        return sm.outputs[0]

    core = ball_layer(G("Kugel Größe"), mats["kugel"], 3)
    halo = ball_layer(G("Halo Größe"), mats["halo"], 3)
    jb = b.node("GeometryNodeJoinGeometry")
    b.link(halo, jb.inputs[0]); b.link(core, jb.inputs[0])
    sw_ball = b.node("GeometryNodeSwitch", input_type="GEOMETRY")
    b.link(G("Kugel sichtbar"), sock(sw_ball.inputs, "Switch"))
    b.link(jb.outputs[0], sock(sw_ball.inputs, "True"))
    ball_geo = sw_ball.outputs[0]

    # ===== Schweif (dünner heller Streifen direkt hinter der Kugel) =============
    head_len = b.mul(prog, L)
    tr = b.node("GeometryNodeTrimCurve", mode="LENGTH")
    b.link(curve, sock(tr.inputs, "Curve"))
    b.link(b.mx(b.sub(head_len, G("Schweif Länge")), 0.0), sock(tr.inputs, "Start"))
    b.link(head_len, sock(tr.inputs, "End"))
    rs = b.node("GeometryNodeResampleCurve")
    b.link(tr.outputs[0], rs.inputs[0])
    sock(rs.inputs, "Count").default_value = 96
    spar = b.node("GeometryNodeSplineParameter")
    radius = b.mul(b.pow(sock(spar.outputs, "Factor"), 1.8), G("Schweif Dicke"))
    prof = b.node("GeometryNodeCurvePrimitiveCircle", mode="RADIUS")
    sock(prof.inputs, "Resolution").default_value = 10
    sock(prof.inputs, "Radius").default_value = 1.0
    c2m = b.node("GeometryNodeCurveToMesh")
    b.link(rs.outputs[0], sock(c2m.inputs, "Curve"))
    b.link(sock(prof.outputs, "Curve"), sock(c2m.inputs, "Profile Curve"))
    b.link(radius, sock(c2m.inputs, "Scale"))
    smt = b.node("GeometryNodeSetMaterial")
    b.link(c2m.outputs[0], sock(smt.inputs, "Geometry"))
    sock(smt.inputs, "Material").default_value = mats["schweif"]
    tail_geo = smt.outputs[0]

    # ===== Glitzerspur ===========================================================
    pts = b.node("GeometryNodePoints")
    b.link(G("Anzahl Funken"), sock(pts.inputs, "Count"))
    idx = b.node("GeometryNodeInputIndex").outputs[0]
    seed = G("Seed")
    seed_n = lambda k: b.math("ADD", seed, float(k))

    u = b.rand_float(0.0, 1.0, idx, seed)                       # Position auf dem Pfad
    # Zeitpunkt, an dem die Kugel u passiert (Umkehrung von smoothstep bei Easing)
    inv_ss = b.sub(0.5, b.math("SINE", b.div(b.math("ARCSINE", b.sub(1.0, b.mul(2.0, u))), 3.0)))
    t_norm = b.switch_float(G("Ease In/Out"), u, inv_ss)
    t_pass = b.add(G("Start Frame"), b.mul(t_norm, dur))
    age_f = b.sub(frame, t_pass)                                # Alter in Frames
    age_s = b.mx(b.div(age_f, G("Bildrate")), 0.0)              # Alter in Sekunden
    life = b.mul(G("Lebensdauer"), b.rand_float(0.45, 1.55, idx, seed_n(7)))
    age_n = b.clamp01(b.div(age_s, life))

    # sichtbar: schon "geboren" (Kugel war hier) und noch nicht verloschen
    born = b.compare("GREATER_EQUAL", age_f, 0.0)
    alive = b.compare("LESS_THAN", age_s, life)
    vis = b.bool_op("AND", born, alive)
    dead = b.bool_op("NOT", vis)

    # Position: Pfadpunkt + Auffächerung + Fallen + Drift + Turbulenz
    sc_u = b.sample_curve(curve, u)
    base = sock(sc_u.outputs, "Position")
    rdir = b.vmath("NORMALIZE", b.rand_vec((-1, -1, -1), (1, 1, 1), idx, seed_n(1)))
    rmag = b.pow(b.rand_float(0.0, 1.0, idx, seed_n(2)), 1.3)
    spread = b.add(G("Breite am Kopf"), b.mul(G("Ausbreitung"), b.pow(age_s, 0.7)))
    off_spread = b.vscale(rdir, b.mul(rmag, spread))
    fall = b.combine(0.0, 0.0, b.mul(b.mul(-0.5, G("Schwerkraft")), b.mul(age_s, age_s)))
    drift = b.vscale(b.rand_vec((-1, -0.3, -1), (1, 0.3, 1), idx, seed_n(3)), b.mul(G("Drift"), age_s))
    noise = b.node("ShaderNodeTexNoise", noise_dimensions="4D")
    b.link(base, sock(noise.inputs, "Vector"))
    b.link(b.mul(sock(st.outputs, "Seconds"), 0.25), sock(noise.inputs, "W"))
    sock(noise.inputs, "Scale").default_value = 1.2
    sock(noise.inputs, "Detail").default_value = 1.0
    turb_v = b.vmath("SUBTRACT", sock(noise.outputs, "Color"), (0.5, 0.5, 0.5))
    turb = b.vscale(turb_v, b.mul(b.mul(G("Turbulenz"), 2.0), b.mn(age_s, 1.5)))
    pos = b.vadd(b.vadd(base, off_spread), b.vadd(fall, b.vadd(drift, turb)))

    setp = b.node("GeometryNodeSetPosition")
    b.link(pts.outputs[0], sock(setp.inputs, "Geometry"))
    b.link(pos, sock(setp.inputs, "Position"))

    # Helligkeit: verglühen + funkeln
    fade = b.sub(1.0, b.pow(age_n, 2.2))
    rate = b.rand_float(0.15, 0.9, idx, seed_n(4))
    phase = b.rand_float(0.0, 6.2832, idx, seed_n(5))
    tw_sin = b.math("SINE", b.add(b.mul(frame, rate), phase))
    tw = b.sub(1.0, b.mul(G("Funkeln"), b.mul(b.add(tw_sin, 1.0), 0.5)))
    # frische Funken direkt hinter der Kugel kurz extra hell
    hot = b.add(1.0, b.mul(2.5, b.math("EXPONENT", b.mul(age_s, -6.0))))
    glow = b.mul(b.mul(b.mul(fade, tw), hot), G("Helligkeit"))

    def store(geo, name, value):
        n = b.node("GeometryNodeStoreNamedAttribute", data_type="FLOAT", domain="POINT")
        b.link(geo, sock(n.inputs, "Geometry"))
        sock(n.inputs, "Name").default_value = name
        b.link(value, sock(n.inputs, "Value"))
        return n.outputs[0]

    g = store(setp.outputs[0], "glow", glow)
    g = store(g, "alter", age_n)
    g = store(g, "farbe", b.rand_float(0.0, 1.0, idx, seed_n(6)))

    dele = b.node("GeometryNodeDeleteGeometry", domain="POINT")
    b.link(g, sock(dele.inputs, "Geometry"))
    b.link(dead, sock(dele.inputs, "Selection"))

    # Größe: viele kleine, wenige große Punkte; schrumpfen beim Verglühen
    rsz = b.pow(b.rand_float(0.0, 1.0, idx, seed_n(8)), G("Größen-Variation"))
    size = b.mul(G("Funken Größe"), b.add(0.25, b.mul(2.6, rsz)))
    size = b.mul(size, b.sub(1.0, b.mul(0.55, age_n)))

    ico = b.node("GeometryNodeMeshIcoSphere")
    sock(ico.inputs, "Radius").default_value = 1.0
    sock(ico.inputs, "Subdivisions").default_value = 2
    iop = b.node("GeometryNodeInstanceOnPoints")
    b.link(dele.outputs[0], sock(iop.inputs, "Points"))
    b.link(sock(ico.outputs, "Mesh"), sock(iop.inputs, "Instance"))
    b.link(size, sock(iop.inputs, "Scale"))
    smf = b.node("GeometryNodeSetMaterial")
    b.link(iop.outputs[0], sock(smf.inputs, "Geometry"))
    sock(smf.inputs, "Material").default_value = mats["funken"]

    join = b.node("GeometryNodeJoinGeometry", loc=(2200, 0))
    for geo in (smf.outputs[0], tail_geo, ball_geo):
        b.link(geo, join.inputs[0])
    b.link(join.outputs[0], gout.inputs[0])

    # Nodes grob anordnen (rein kosmetisch)
    for i, n in enumerate(t.nodes):
        if n not in (gin, gout, join):
            n.location = ((i % 14) * 220 - 1700, -(i // 14) * 260)
    return t


# ---------------------------------------------------------------------------
# Kamera, Welt, Render, Compositor
# ---------------------------------------------------------------------------
def setup_camera(scene):
    cam = bpy.data.cameras.new("Kamera")
    cam.lens = 35
    ob = bpy.data.objects.new("Kamera", cam)
    scene.collection.objects.link(ob)
    ob.location = (0.0, -11.5, 0.0)
    ob.rotation_euler = (math.radians(90), 0, 0)
    scene.camera = ob


def setup_world(scene):
    w = bpy.data.worlds.new("Schwarz")
    try:
        w.use_nodes = True
    except Exception:
        pass
    bg = w.node_tree.nodes.get("Background") or w.node_tree.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0, 0, 0, 1)
    bg.inputs["Strength"].default_value = 0.0
    if hasattr(w, "color"):
        w.color = (0, 0, 0)
    scene.world = w


def setup_render(scene):
    scene.render.engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in [
        e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items
    ] else "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x, scene.render.resolution_y = AUFLOESUNG
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = FRAME_START, FRAME_END
    scene.frame_current = 96
    scene.render.film_transparent = False          # Ausgabe auf Schwarz
    scene.eevee.taa_render_samples = 64
    # "Standard" hält das Gold/Orange satt (AgX würde die Funken eher weißlich machen)
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    # Ausgabe: PNG-Sequenz (verlustfrei, für Schnittprogramm)
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = "//render/leuchtkugel_"


def setup_compositor(scene):
    if not hasattr(scene, "compositing_node_group"):
        print("Hinweis: Compositor-API nicht gefunden – Glow übersprungen.")
        return
    t = bpy.data.node_groups.new("Glow", "CompositorNodeTree")
    scene.compositing_node_group = t
    iface = t.interface
    iface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl = t.nodes.new("CompositorNodeRLayers"); rl.location = (-600, 0)
    out = t.nodes.new("NodeGroupOutput"); out.location = (900, 0)

    def glare(kind, loc, **vals):
        g = t.nodes.new("CompositorNodeGlare"); g.location = loc
        sock(g.inputs, "Type").default_value = kind
        for k, v in vals.items():
            sock(g.inputs, k).default_value = v
        return g

    # 1) weiches Glühen um alles
    g1 = glare("Bloom", (-300, 0), Threshold=0.8, Smoothness=0.5, Strength=0.55, Size=0.65)
    try:
        sock(g1.inputs, "Quality").default_value = "High"
    except Exception:
        pass
    # 2) feine Sternchen nur auf den hellsten Funken
    g2 = glare("Streaks", (0, 0), Threshold=3.0, Smoothness=0.3, Strength=0.12,
               Streaks=4, Fade=0.84, **{"Streaks Angle": math.radians(45)})
    t.links.new(sock(rl.outputs, "Image"), sock(g1.inputs, "Image"))
    t.links.new(sock(g1.outputs, "Image"), sock(g2.inputs, "Image"))
    t.links.new(sock(g2.outputs, "Image"), out.inputs[0])


# ---------------------------------------------------------------------------
def main():
    scene = reset_scene()
    path = make_path()

    mats = {
        "funken": make_spark_material(),
        "kugel": make_simple_glow_material("Kugel", (1.0, 0.75, 0.45, 1), 30.0, 0.4),
        "halo": make_simple_glow_material("Kugel_Halo", (1.0, 0.32, 0.04, 1), 0.7, 4.0),
        "schweif": make_simple_glow_material("Schweif", (1.0, 0.42, 0.06, 1), 6.0, 1.2),
    }
    tree = make_gn_tree(path, mats)

    me = bpy.data.meshes.new("Glitzerspur")
    ob = bpy.data.objects.new("Glitzerspur", me)
    scene.collection.objects.link(ob)
    mod = ob.modifiers.new("Leuchtkugel", "NODES")
    mod.node_group = tree
    for item in tree.interface.items_tree:
        if getattr(item, "name", "") == "Pfad" and item.item_type == "SOCKET":
            try:
                mod[item.identifier] = path                              # Blender 4.x
            except TypeError:
                getattr(mod.properties.inputs, item.identifier).value = path  # Blender 5.x
    for m in mats.values():
        me.materials.append(m)

    setup_camera(scene)
    setup_world(scene)
    setup_render(scene)
    setup_compositor(scene)

    # Pfad auswählen, damit man direkt loslegen kann
    for o in scene.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = path
    path.select_set(True)

    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if argv:
        bpy.ops.wm.save_as_mainfile(filepath=argv[0])
        print("Gespeichert:", argv[0])


if __name__ == "__main__":
    main()
