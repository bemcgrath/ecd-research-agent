# Case corpus walkthrough — early vs delayed therapy

**Research aid only — not medical advice.** This page restates what one automated run of the case corpus found in published papers. It cannot tell anyone when to start treatment. Share questions with an ECD specialist.

Source for these numbers: a master corpus run after the PMC full-text fix (roughly **9** validated records, **7** unique single cases, **0** early / **3** delayed timing labels, full text on **15/20** selected articles). Re-run `cases_cli` if you need a fresh table; do not treat this narrative as live database output.

Terms (BRAF, MEK, Sx→Dx, brand names): **[GLOSSARY.md](GLOSSARY.md)**.

---

## Bottom line in plain language

Among **seven unique single-patient stories** the tool kept after cleanup:

| Timing label | Count | What it means here |
| --- | --- | --- |
| **Early** targeted therapy | **0** | No unique case in this set was labeled "early" start of BRAF/MEK therapy |
| **Delayed** targeted therapy | **3** | Papers describe a long path from symptoms (and sometimes from diagnosis) to MAPK-targeted drugs |
| **Unclear** | **2** | Timing language was present but not cleanly early vs delayed |
| **Not reported** | **2** | Timing of targeted therapy was not extractable from what the tool saw |

That is a **tiny** sample. It does **not** prove that early therapy is better or worse than delayed therapy. Many neurologic outcomes are incomplete; one record is abstract-limited. Case reports describe individuals — they do not replace trials or specialist judgment.

---

## The seven unique single cases (stories, not proof)

Brand names below are the common U.S. names families may hear; papers usually use the generic name. Listing a drug is **not** a recommendation.

### Delayed targeted therapy (3)

1. **Mixed LCH/ECD, BRAF V600E** ([PMID 41562816](https://pubmed.ncbi.nlm.nih.gov/41562816/))  
   Long journey: about **4 years** symptoms → diagnosis, then about **2 years** to targeted therapy. Treated with **dabrafenib + trametinib** (**Tafinlar + Mekinist**), after earlier chemo-type and steroid regimens. After months on Dab/Tra, ataxia scores improved somewhat, but after ~21 months ataxia, spastic gait, and dysarthria still persisted. Classic illustration: **delayed start**, **partial neurologic change**, not a clean "cure" story.

2. **Mixed histiocytosis with long neurologic course** ([PMID 40131415](https://pubmed.ncbi.nlm.nih.gov/40131415/) — one patient in a small series)  
   About **7 years** from first seizure-related symptoms to diagnosis. Treated with **cobimetinib** (**Cotellic**). Paper reports ongoing clinical and imaging improvement. Timing labeled **delayed**.

3. **ECD with orbital/CNS features, BRAF V600E** ([PMID 33204897](https://pubmed.ncbi.nlm.nih.gov/33204897/))  
   Roughly **7 months** from first symptoms to diagnosis, then about **a year** from presentation before **vemurafenib** (**Zelboraf**). After many immunosuppressants failed, Zelboraf was associated with stopping orbital inflammation flares and lasting clinical/PET stability on a reduced dose in the report's follow-up window. Timing labeled **delayed**.

### Timing unclear (2)

Both from the same monocytic-meningitis series ([PMID 40131415](https://pubmed.ncbi.nlm.nih.gov/40131415/)):

4. **ECD / histiocytosis with MAP2K1 mutation** — **binimetinib** (**Mektovi**). Meningitis resolved quickly with neurologic and imaging improvement in the paper's account. Interval wording did not map cleanly to early vs delayed in the corpus labels.

5. **Histiocytosis (unspecified mutation in the extract)** — also **Mektovi**. Partial, time-limited response; neurologic progression after ~two months; death reported in May 2022. Again **unclear** timing, not "early."

### Timing not reported (2)

6. **ECD with BRAF V600E and KRAS Q61H** ([PMID 27940476](https://pubmed.ncbi.nlm.nih.gov/27940476/)) — **dabrafenib** then **trametinib** (**Tafinlar**, **Mekinist**). CNS and timing fields were not reported in the extract; neurologic outcome blank in the table.

7. **BRAF V600E–negative ECD with CNS involvement** ([PMID 41312426](https://pubmed.ncbi.nlm.nih.gov/41312426/)) — **cladribine** (chemo-type; not a BRAF/MEK pill). Symptoms ~4 years before diagnosis; neurologic symptoms improved clinically with a complicated MRI course and later stability off therapy. Targeted BRAF/MEK timing is **not** the story here; timing of MAPK inhibitors was **not reported**.

---

## Reviews and large series (keep separate)

These rows are **not** one patient each. Do not fold their large `n` into the early/delayed counts above.

| Paper | n (approx.) | Useful takeaway from the extract | Timing in corpus |
| --- | --- | --- | --- |
| [PMID 33993305](https://pubmed.ncbi.nlm.nih.gov/33993305/) — neurologic histiocytosis review/series context | 30 neurologic ECD | Targeted BRAF/MEK (and related) therapies associated with much higher MRI response rates than chemo/immunosuppression in that retrospective neurologic ECD slice | not reported for individual early/late starts |
| [PMID 36135995](https://pubmed.ncbi.nlm.nih.gov/36135995/) — systematic review, isolated CNS ECD | 40 | Mixed outcomes: about half stabilized or improved on symptoms/imaging; others progressed; mortality in a sizable minority | not reported as early vs delayed per patient |

Drugs named across these reviews include **vemurafenib (Zelboraf)**, **dabrafenib (Tafinlar)**, **trametinib (Mekinist)**, **cobimetinib (Cotellic)**, plus older options (interferon, cladribine, steroids, etc.).

---

## How to read this without overclaiming

- **"Delayed"** means when MAPK-targeted therapy started relative to symptoms/diagnosis **as the paper described** — not how fast someone felt better after the first dose.
- **Zero early cases** in this unique set is a finding about **this extract**, not a claim that early therapy never happens in the literature.
- Full text helped (15/20 articles), but **gaps remain**: timing missing in 2/7 unique rows; neuro outcomes incomplete; diagnosis-to-treatment often blank.
- Use PMIDs to open the papers, then ask the care team what applies to a specific person.

---

## Related docs

- [GLOSSARY.md](GLOSSARY.md) — brand/generic names and table columns  
- [USER_GUIDE.md](USER_GUIDE.md) — how to re-run `cases_cli` and read reports  
- [MISSION.md](MISSION.md) — project intent (research aid, not clinical decision support)
