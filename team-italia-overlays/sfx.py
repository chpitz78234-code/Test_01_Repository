"""Synthetisiert die Soundeffekte zu den Animations-Cues und mischt sie zu einer WAV-Spur.

    python3 sfx.py renders/.build/cues.json renders/sfx_komplett.wav

Alle Klänge werden hier erzeugt (keine Samples), deterministisch über einen festen Seed.
Cue-Typen und ihre Herkunft aus den CSS-Animationen stehen in render.js (cuesFromPage).
"""
import json
import sys
import wave

import numpy as np

SR = 48000
rng = np.random.default_rng(7)

PENTA = [523.25, 587.33, 659.25, 783.99, 880.00, 1046.5, 1174.7, 1318.5]


def t_axis(dur):
    return np.arange(int(dur * SR)) / SR


def onepole_lp(x, cutoff):
    """Einpoliger Tiefpass mit zeitvariabler Grenzfrequenz (Array oder Skalar)."""
    cutoff = np.broadcast_to(cutoff, x.shape)
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    s = 0.0
    for i in range(len(x)):
        s = (1 - a[i]) * x[i] + a[i] * s
        y[i] = s
    return y


def hp(x, cutoff):
    return x - onepole_lp(x, cutoff)


def env_ad(n, attack, decay_tau):
    t = np.arange(n) / SR
    e = np.minimum(t / max(attack, 1e-4), 1.0) * np.exp(-np.maximum(t - attack, 0) / decay_tau)
    return e


def bell(freq, dur=0.6, tau=0.18, partials=((1, 1), (2.76, .35), (5.4, .12))):
    t = t_axis(dur)
    y = sum(a * np.sin(2 * np.pi * freq * m * t) * np.exp(-t / (tau / m ** .5)) for m, a in partials)
    return y * np.minimum(t / .002, 1)


def whoosh(dur=0.6, peak=0.35, lo=250, hi=4200):
    t = t_axis(dur)
    x = rng.standard_normal(len(t))
    ph = t / dur
    shape = np.where(ph < peak, (ph / peak) ** 2, np.exp(-(ph - peak) / (1 - peak) * 4))
    cutoff = lo + (hi - lo) * shape
    y = hp(onepole_lp(onepole_lp(x, cutoff), cutoff), 120)
    return y * shape * 1.6


def pop(f0=650, dur=0.16, thump=0.0):
    t = t_axis(dur)
    f = f0 * (1 + .7 * np.exp(-t / .012))
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t / .045)
    click = rng.standard_normal(len(t)) * np.exp(-t / .0015) * .25
    y = y + hp(click, 2000)
    if thump:
        y += thump * np.sin(2 * np.pi * 110 * t * (1 + .5 * np.exp(-t / .02))) * np.exp(-t / .07)
    return y * np.minimum(t / .001, 1)


def tick(freq=2600, dur=0.05, amp=1.0):
    t = t_axis(dur)
    n = hp(rng.standard_normal(len(t)), 3000) * np.exp(-t / .002)
    s = np.sin(2 * np.pi * freq * t) * np.exp(-t / .012)
    return amp * (n * .5 + s * .6)


def blip(freq, dur=0.12):
    t = t_axis(dur)
    return np.sin(2 * np.pi * freq * t) * np.exp(-t / .035) * np.minimum(t / .002, 1)


def swipe(dur=0.55):
    t = t_axis(dur)
    x = rng.standard_normal(len(t))
    e = np.sin(np.pi * np.minimum(t / dur, 1)) ** 2
    y = onepole_lp(hp(x, 1800), 6000)
    return y * e * .5


def motor(dur, f):
    """Schrittmotor-Surren für eine Druckschicht."""
    t = t_axis(dur)
    vib = 1 + .01 * np.sin(2 * np.pi * 9 * t)
    ph = 2 * np.pi * f * np.cumsum(vib) / SR
    y = np.sign(np.sin(ph)) * .35 + np.sin(2 * ph) * .25 + np.sin(3 * ph) * .1
    y = onepole_lp(y, 1400)
    fade = np.minimum(np.minimum(t / .01, 1), np.minimum((dur - t) / .01, 1))
    return y * fade


def shimmer():
    out = np.zeros(int(.6 * SR))
    for i, f in enumerate((2637, 3136, 3951)):
        b = bell(f, .5, .12, ((1, 1),))
        o = int(i * .045 * SR)
        out[o:o + len(b)] += b[:len(out) - o] * (1 - i * .2)
    return out


def chime():
    out = np.zeros(int(1.8 * SR))
    for i, f in enumerate((523.25, 659.25, 783.99, 1046.5)):
        b = bell(f, 1.6, .6)
        o = int(i * .07 * SR)
        out[o:o + len(b)] += b[:len(out) - o] * .55
    return out


def counter_ticks(n_to, dur):
    """Zeitpunkte der Zahlensprünge für cubic-bezier(0,0,0,1): x=s^3, y=3s^2-2s^3."""
    s = np.linspace(0, 1, 4000)
    x, y = s ** 3, 3 * s ** 2 - 2 * s ** 3
    vals = np.round(y * n_to).astype(int)
    idx = np.nonzero(np.diff(vals))[0] + 1
    return [(x[i] * dur, vals[i]) for i in idx]


def build(cues, total):
    L = np.zeros(int(total * SR) + SR * 2)
    R = np.zeros_like(L)

    def add(sig, at, gain, pan=0.0):
        o = int(round(at * SR))
        if o < 0:
            sig, o = sig[-o:], 0
        sig = sig[:len(L) - o]
        p = (np.clip(pan, -1, 1) + 1) * np.pi / 4
        L[o:o + len(sig)] += sig * gain * np.cos(p)
        R[o:o + len(sig)] += sig * gain * np.sin(p)

    seq = {}
    for c in sorted(cues, key=lambda c: c['t']):
        k, t, pan = c['type'], c['t'], c.get('pan', 0) * .6
        if k == 'whoosh':
            add(whoosh(.62, .3), t - .12, .32, pan)
        elif k == 'whoosh_out':
            add(whoosh(.45, .75), t, .18, pan)
        elif k == 'pop':
            add(pop(rng.uniform(560, 820)), t + .03, .36, pan)
        elif k == 'pop_big':
            add(pop(rng.uniform(380, 440), .25, thump=.6), t + .03, .5, pan)
        elif k == 'letter':
            add(tick(rng.uniform(2200, 3200), amp=.8), t + .06, .16, pan)
        elif k == 'soft':
            add(tick(rng.uniform(1600, 2000), amp=.5), t + .05, .1, pan)
        elif k == 'check':
            i = seq.setdefault(('check', c['scene']), [0])
            add(bell(PENTA[min(i[0] + 2, 7)] * 2, .5, .16), t + .05, .2, pan)
            i[0] += 1
        elif k == 'cell':
            add(bell(rng.choice(PENTA[3:]) * 2, .4, .1), t + .04, .12, pan)
        elif k == 'blip':
            key = ('blip', c['scene'])
            last = seq.get(key, [(-9, 0)])
            i = last[0][1] + 1 if t - last[0][0] < .4 else 0
            seq[key] = [(t, i)]
            add(blip(PENTA[min(i, 7)]), t + .02, .22, pan)
        elif k == 'swipe':
            add(swipe(), t, .14, pan)
        elif k == 'counter':
            ticks = counter_ticks(c['to'], c['dur'])
            for j, (dt, v) in enumerate(ticks):
                add(tick(1800 + 60 * v, .04, 1), t + dt, .22, pan)
            add(bell(1046.5, .7, .22), t + ticks[-1][0], .22, pan)
        elif k == 'print':
            add(motor(c['dur'], 196 if c['i'] % 2 else 220), t, .07, pan)
            add(tick(1200, .03, .6), t, .1, pan)
        elif k == 'shimmer':
            add(shimmer(), t + .3, .05, pan)
        elif k == 'chime':
            add(chime(), t + .04, .3, pan)

    # kurze Erstreflexionen für etwas Raum
    for d, g in ((.023, .18), (.041, .12), (.067, .07)):
        n = int(d * SR)
        L[n:], R[n:] = L[n:] + R[:-n] * g, R[n:] + L[:-n] * g * .8
    mix = np.stack([L, R], 1)[:int(total * SR)]
    mix = np.tanh(mix * 1.15) / np.tanh(1.15)
    peak = np.abs(mix).max()
    if peak > .89:
        mix *= .89 / peak
    return mix


def main():
    data = json.load(open(sys.argv[1]))
    mix = build(data['cues'], data['total'])
    with wave.open(sys.argv[2], 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype('<i2').tobytes())
    print(f"{len(data['cues'])} Cues -> {sys.argv[2]}")


if __name__ == '__main__':
    main()
