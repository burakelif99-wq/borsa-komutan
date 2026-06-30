# Research Log — Shadow Mode (v1.0 vs v2.0)

## Stage 3: Controlled Experiment

### Completion Criteria
- [ ] 14 gun tamamlandi
- [ ] En az 20 islem olustu
- [ ] Tum islemlerin 1G ve 5G backfill'i tamamlandi
- [ ] Weekly report x2 uretildi
- [ ] Kanit tablosundaki 6 soru cevaplandi
- [ ] Production karari verildi

---

### 2026-06-29 — Experiment Started

**Hypothesis:** v1.0'daki weighted score fusion (`ai_entegre_skor`), AI'nin AL kararini yapisal olarak eziyor. v2.0 (role-based pipeline) AI aday gosterir, risk katmani filtreler. Bu yaklasim daha yuksek alpha uretecek.

**Design:** Shadow Mode. v1.0 (production, kontrol), v2.0 (shadow, deney). Ayni veri, ayni anda, ayri karar mantigi. Gercek emir yok.

**Parameters frozen:** ATR threshold, GB threshold, RF guard, likidite filtresi — hicbiri degismeyecek.

**Day 1 data:**
- 579 hisse tarandi
- v1.0 AL: 540, v2.0 AL: 529 (fark: -11)
- Anlasmazlik: 37 hisse (%6.4)
- Risk RED (v1=AL, v2=BEKLE): 24 (ATR=11, LIKIDITE=9, ?=4)
- Yeni firsat (v2=AL, v1≠AL): 13
- RALYH: v1=AL (GB_PASS), v2=BEKLE (ATR_LIMIT) — canary

**Notable:** ATR_LIMIT grubu GB_ort=0.790 (gap=+0.390), LIKIDITE grubu GB_ort=0.724 (gap=+0.324). Risk RED grubu ortalamasi yuksek guvenli hisseleri blokluyor.

### Day 1 Observation (29/06/2026)
ATR_LIMIT nedeniyle elenen iki hisse (RALYH gb=0.903, SANEL gb=0.671) gun icinde yaklasik %10 yukseldi. Bu, ATR filtresinin olasi firsat maliyetine isaret ediyor. Ancak filtre performansi hakkinda sonuc cikarmak icin 1G ve ozellikle 5G getirileri beklenmeli; tek gunluk hareket nihai kanit degildir.

---

### 2026-07-03 — Day 5
*(to be filled)*

---

### 2026-07-07 — Week 1 Review
*(to be filled)*

---

### 2026-07-13 — Final Review
*(to be filled)*

---

## Evaluation Protocol

### Day 7 — Intermediate Assessment
Only one of these three conclusions:
- 🟢 **Hipotez destekleniyor** — v2.0 lehine tutarli desen var
- 🟡 **Yeterli kanit olusmadi** — net desen yok, deney devam
- 🔴 **Hipotez zayifliyor** — v2.0 bekleneni veremedi

No parameter changes. No early termination unless critical bug.

### Day 14 — Final Assessment

**Patterns to examine:**
1. Risk RED grubu sistematik yukseliyor mu, yoksa birkac istisna mi?
2. Yeni Firsat grubu ort getirisi Ortak AL grubuna yaklasiyor mu?
3. RALYH tek istisna mi, yoksa benzer 10+ ornek var mi?
4. Bull vs Bear rejimlerinde anlasmazlik orani degisiyor mu?

**Kanit Tablosu:**
```
KANIT TABLOSU
v2 Alpha > v1 Alpha       [PASS/FAIL]
Sharpe                    [PASS/FAIL]
MaxDD                     [PASS/FAIL]
False BEKLE -%30          [PASS/FAIL]
False AL +%20 sinirinda   [PASS/FAIL]
Risk RED dogru karar      [PASS/FAIL]
─────────────────────────────────────
Production Decision
☐ Stay v1.0
☐ Extend Experiment (7 days)
☑ Promote v2.0
```

### Stage 3 Final Review
*To be generated at experiment end.*

### Sections
1. Deney Ozeti
2. Hipotez
3. Deney Tasarimi
4. Katilimci Evreni (579 hisse)
5. Shadow Sonuclari (v1.0 vs v2.0 KPI)
6. Anlasmazlik Analizi
7. Risk RED Analizi
8. Special Watchlist Sonuclari
9. Kanit Tablosu
10. Karar
11. Sonraki Adim

---

## Log Rules
Only log events that could affect experiment integrity:
- BIST sert dusus / devre kesici
- Veri saglayicisi kesintisi
- Tatil / dusuk hacim
- Backfill gecikmesi
- Yazilim hatasi (duzeltildi)
- Harvest/reboot vs.

No daily technical notes. No parameter change ideas.

---

*This log is read-only. No parameter changes during the experiment window.*
