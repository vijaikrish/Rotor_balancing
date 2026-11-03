# Rotor balancing: standards and research references

Research checked 3 November 2026. This is a source map and interpretation aid, not a reproduction of standards. Standards are copyrighted; use the controlled, applicable edition and amendments for engineering decisions. Public abstracts and previews do not establish full clause compliance.

## Primary standards

1. **ISO 21940-11:2016, including Amendment 1:2022 — rotors with rigid behaviour.** Official abstract says it sets permissible residual unbalance, required correction-plane count, tolerance-plane allocation, and accounting for balancing errors. It explicitly excludes flexible-behaviour rotors, which ISO 21940-12 addresses. ISO page reports the 2016 edition current after review, with Amendment 1:2022.[27][29] The grade G is a balance-quality descriptor used to derive permissible residual unbalance; it is not a measured installed-machine vibration severity limit. Do not read a G grade in mm/s as a direct measured vibration acceptance value.

2. **ISO 21940-12:2016 — rotors with flexible behaviour.** Covers typical flexible rotor configurations, balancing procedures, assessment of final balance, and guidance for balance-quality criteria. The ISO abstract explicitly says it is not an acceptance specification for any rotor. Structural resonances and modifications are outside its scope.[28] Do not call a tool compliant with Part 12 merely because it has multiple planes/speeds or uses an influence matrix.

3. **ISO 20816-1:2026 — general machine-vibration evaluation.** Current official entry establishes general principles for measurements on rotating/non-rotating machine parts, including relative and absolute radial shaft vibration in the stated context, and evaluation by both magnitude and change. It excludes axial shaft vibration unless otherwise stated.[31]

4. **ISO 20816-3:2026 — in-situ vibration evaluation for its specified machine set.** Current official entry (published October 2026) covers specified coupled industrial machine types in its speed range and broadband in-situ measurements at shafts/bearings/housings near bearings under steady operation; it applies to acceptance testing and monitoring.[30] The application’s existing classifier is labelled ISO 20816-3 and uses the 2022-era group/support thresholds; that edition is now withdrawn and replaced by the 2026 edition. Do not present the current GUI values as a current-edition acceptance tool without checking and updating to the relevant controlled 2026 text and machine applicability. ISO 20816 is not “shaft vibration only”: Part 1 expressly covers non-rotating parts and radial shaft measures; Part 3 includes shaft and bearing/pedestal/housing measurement points. The applicable part, measurement quantity, location, machine category and conditions matter.

5. **API TR 684-1:2019.** This is a rotordynamic tutorial intended to explain API standard paragraphs (including lateral/torsional dynamics and machinery balancing), give background, and aid interpretation; it is not a blanket API compliance certificate for a general-purpose balancing calculator.[36] API’s digital catalog currently identifies API TR 684 as a tutorial title and lists a third edition in editing, so check the applicable API equipment specification and current edition directly.[37] Do not substitute this tutorial for the machine-specific API standard/spec or its acceptance paragraphs. No verified public evidence supports the README’s asserted API “20–50% vibration change” rule; it is removed. Trial-weight selection must be engineered for measurable response while respecting rotor stress, trip limits, safe operation and applicable procedures, without this unsourced fixed percentage.

   **API residual-unbalance tolerance formula, per journal.** The same API TR 684-1 tutorial (restating what it attributes to API SP paragraph 2.8.2.4, item b) gives, for the total residual unbalance a newly built rotor is allowed to have after balancing: `U = 6350·W/N` g·mm (SI) `= 4·W/N` oz·in (US customary), with `W` the journal static load (or overhung weight load for an end-mode shape) and `N` the operating speed nearest the critical of concern.[36][38] The application's Standards tab section 3 implements this directly per journal — it is referenced to bearing reaction, not total rotor mass, and is distinct from the ISO grade-G approach. Independent secondary sources (API 610/612/617-oriented balancing tutorials) corroborate the same `4W/N` (US) / `6350W/N` (SI) criterion, generally citing API 617 and historically MIL-STD-167-1 for the same formula structure; W there is commonly described as journal static load or total rotor weight split across two planes depending on source — confirm which load basis your specific API equipment spec/edition requires before use.[39][40]

6. **ISO 21940-12:2016 — flexible-behaviour rotor tolerance derivation.** ISO 21940-12 does not define an independent residual-unbalance formula. It derives tolerances for rotors with flexible behaviour FROM the rigid-rotor permissible residual unbalance of ISO 21940-11, expressed as percentages applied to equivalent modal unbalances: generic published guidance (see the Energiforsk/Nöremark 2018 summary of the standard, citing its clause 9) states the equivalent 1st and 2nd modal residual unbalance shall each not exceed 60% of the ISO 21940-11 `U_per` for the significant bending modes, and if low-speed (rigid-body) balancing is also or only performed, the total rigid-body residual unbalance shall not exceed 100% of `U_per`; limits on a less-significant mode may be relaxed but never beyond 100%.[28][41] The application's Standards tab section 2 implements exactly this scaling (60%/60%/100% of the rigid `U_per`) as a sizing aid — it does NOT implement the standard's Annex D procedure for evaluating equivalent modal unbalance from measured mode shapes, which requires the actual modal model/test data for the specific rotor.

## Peer-reviewed / primary research

7. **Tessarzik, J. M. (1972), “Flexible rotor balancing by the influence coefficient method. Part 1: Evaluation of the exact point-speed and least squares procedures,” NASA-CR-12107 / MTI-72TR32.** NASA’s record describes tests over three rotor-bearing critical speeds, comparison of exact point-speed and least-squares procedures, and generally equivalent capability for studied configurations. Full report download linked by NASA.[32]

8. **Tessarzik, J. M., Badgley, R. H. & Fleming, D. P. (1975), “Experimental evaluation of multiplane-multispeed rotor balancing through multiple critical speeds,” ASME paper 75-DET-73.** NASA record states laboratory testing extended influence-coefficient (especially least-squares) balancing to multiple bending critical speeds, with results through four criticals on the test rotor. This is experimental evidence for the method, not proof of applicability to every machine.[33]

9. **Lund, J. W. & Tonnesen, J. (1972), “Analysis and Experiments on Multi-Plane Balancing of a Flexible Rotor,” Journal of Engineering for Industry 94(1), 233–242.** ASME’s article page confirms title, authors, issue and date; access to full text may require subscription.[34]

10. **Yao et al. (2020), “Balancing optimization of a multiple speeds flexible rotor,” Journal of Sound and Vibration 480, 115405.** DOI 10.1016/j.jsv.2020.115405. The article discusses classical least-squares influence coefficients for multiple speeds and motivates an optimization approach because an aggregate least-squares objective can leave excessive residual at particular speeds. This is a reminder that a least-squares minimum is not a guarantee that every channel/speed satisfies an independent limit.[35]

## Practical interpretation for this application

- A multi-speed, multi-plane influence-coefficient solve is a recognized experimental balancing approach, but validity depends on useful/consistent measurements, linear response over the applied correction range, repeatable operating conditions, adequate independent information, and a well-conditioned model. Count of channels ≥ planes is only a necessary equation-count fact, not a guarantee of unique or stable estimates. Matrix rank must equal the number of unknown plane weights for a unique unconstrained solution; rank deficiency and high condition number matter.
- No universal rpm-to-mm/s vibration acceptance conversion exists. An ISO G grade and a machine vibration severity zone answer different questions. The service speed participates in conversion from balance quality to residual unbalance, not into a universal installed vibration limit.
- Standards thresholds, simplified formula implementations, and public abstracts in software documentation are orientation only. Verify full clauses, editions, amendments, machine class, sensors, locations, units and agreed acceptance criteria before sign-off.

## Evidence notes / source excerpts

- ISO 21940-11 official abstract: “does not cover the balancing of rotors with flexible behaviour”; procedures/tolerances for those rotors are in Part 12.[27]
- ISO 21940-12 official abstract: “not intended to serve as an acceptance specification for any rotor”.[28]
- ISO 20816-3 official 2026 entry identifies the current edition as 2026 and describes in-situ broadband measurements and its specified machine types.[30]
- NASA 1972 abstract: rotor operated across three critical speeds; least-squares procedure generally equivalent to exact point-speed for configurations studied.[32]
- NASA 1975 abstract: test demonstrated systematic balancing through four bending critical speeds on the laboratory test rotor.[33]
- API TR 684-1 description calls it a tutorial to clarify API standard paragraphs and provide background/interpretive guidance.[36]
- API TR 684-1 / studylib excerpt of its equation (2)/(3-1)/(3-2): "U = 6350W/N" (SI) and "U = 4W/N" (US customary), attributed to "SP 2.8.2.4, Item b", described as the total residual unbalance a newly constructed rotor is allowed after balancing, with W the journal static weight load (or overhung weight load for end-mode shapes) and N the operating speed nearest the critical of concern.[38]
- Independent balancing tutorials (Texas A&M Rotordynamics Lab course notes; a turbomachinery balancing-techniques document) both state "API standards, such as API 617, specify unbalance tolerances... U = 6350(W/N) g-mm (SI) / U = 4(W/N) oz-in (US customary), W = journal static load", and describe the API residual-unbalance verification test procedure (trial weight at six angular positions per plane).[39][40]
- A pump/vibration monitoring reference states the API 610/612/617 residual-unbalance limit as "4W/N" with "N = maximum actual running speed > 1000 rpm, W = static journal weight on each end", and separately notes this limit's history tracing to MIL-STD-167-1 (U.S. Navy).[41]
- Energiforsk/Nöremark (2018) ISO-standards presentation summarizing ISO 21940-12 clause 9: "First and second bending modes: a) the equivalent first modal residual unbalance shall not exceed 60%... b) the equivalent second modal residual unbalance shall not exceed 60%... c) if low-speed balancing is carried out, the total residual unbalance as a rigid body shall not exceed 100%", all percentages of the ISO 21940-11 rigid-rotor permissible residual unbalance.[42]

## Sources

[27] https://www.iso.org/standard/54074.html
[28] https://www.iso.org/standard/50429.html
[29] https://www.iso.org/standard/78116.html
[30] https://www.iso.org/standard/89922.html
[31] https://www.iso.org/standard/89921.html
[32] https://ntrs.nasa.gov/citations/19730005750
[33] https://ntrs.nasa.gov/citations/19760037757
[34] https://asmedigitalcollection.asme.org/manufacturingscience/article-abstract/94/1/233/393581/Analysis-and-Experiments-on-Multi-Plane-Balancing?redirectedFrom=fulltext
[35] https://doi.org/10.1016/j.jsv.2020.115405
[36] https://www.normsplash.com/Samples/API/184137116/API-TR-684-1-2019-en.pdf
[37] https://www.api.org/products-and-services/standards/digital-catalog
[38] https://studylib.net/doc/27891451/api-publ-684
[39] https://rotorlab.tamu.edu/me459/Rotor%20Balancing/2016%20TPS%20Tut%20ROTOR%20BALANCING%20Pavelek.pdf
[40] https://www.scribd.com/document/817386163/Balancing-tutorial
[41] https://www.911metallurgist.com/wp-content/uploads/2016/01/Monitoring-Repairs-to-your-Pumps.pdf
[42] https://files.engineering.com/files/57ebe030-d42e-41f6-8579-44a390c7deda/ISO_Standard_Vibration_Summary.pdf (Nöremark, "Vibration in nuclear application", Energiforsk 2018 — ISO 21940-12 clause 9 summary; verify directly against the controlled ISO 21940-12 text, this is a secondary summary)

