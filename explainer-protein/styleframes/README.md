# Styleframes „Protein-Power“

Stiltest vor der Animation: drei Skriptstellen, jeweils in Stil A und Stil B
(siehe `motion-spec/STIL_UND_ANIMATIONSVORGABE.md`). Format 1080×1920.

| Skriptstelle | Stil A (Neo-Brutalismus) | Stil B (Soft-Gradient) |
|---|---|---|
| 5–15 s: Aminosäuren wie Perlen an einer Kette | `A1_aminosaeuren.png` | `B1_aminosaeuren.png` |
| 15–32 s: Antikörper wehren Viren ab | `A2_antikoerper.png` | `B2_antikoerper.png` |
| 40–52 s: 0,8 g pro kg und Proteinquellen | `A3_praxis.png` | `B3_praxis.png` |

`vergleich_A_B.jpg` zeigt alle sechs nebeneinander.

Neu rendern (Node + Playwright):

```
NODE_PATH=$(npm root -g) node gen.js .
```

Schriften: Anton und Space Mono (SIL Open Font License), Fließtext Inter (systemweit installiert).
