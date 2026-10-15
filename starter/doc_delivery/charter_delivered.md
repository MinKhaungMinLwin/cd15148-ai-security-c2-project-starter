# Red Team Charter

## Engagement Details

| Field | Value |
|-------|-------|
| **Engagement Name** | FinanceGuard AI Systems Red Team Assessment |
| **Date** | 2026-10-16 |
| **Assessor** | Min Khaung Min Lwin (Red Team, Udacity AI Security Capstone) |
| **Sponsor** | FinanceGuard Inc. — CISO / Course Reviewer |

## Objectives

The engagement exercises five attack vectors across the three AI system
components. Each objective states what the attack aims to demonstrate.

1. **FGSM Evasion (Receipt Classifier).** Show that a white-box, gradient-based
   perturbation can flip the CNN's receipt / non-receipt decision while the
   image remains visually unchanged to a human reviewer — demonstrating that the
   expense-approval model can be fooled at inference time.
2. **Label-Flip Data Poisoning (Receipt Classifier).** Show that corrupting a
   small fraction (≤10%) of training labels measurably degrades accuracy on an
   otherwise-clean test set — demonstrating a training-time integrity risk.
3. **Prompt Injection (RAG Chatbot).** Show that user input can override or
   subvert the system prompt (prompt extraction, role hijacking, policy
   contradiction, instruction override, encoding bypass) — demonstrating that
   the chatbot cannot reliably separate instructions from data.
4. **Data Exfiltration (RAG Chatbot).** Show that semantic retrieval surfaces a
   CONFIDENTIAL compensation document that was indexed with no access control —
   demonstrating an architecture-level data-leak independent of LLM behavior.
5. **Supply Chain Vulnerability Analysis (Infrastructure).** Enumerate OS and
   Python package vulnerabilities from the Trivy scan and identify Dockerfile
   misconfigurations — demonstrating deployment-pipeline exposure.

## Scope

### In Scope
- **Receipt Classifier** (`classifier/`): the `ReceiptCNN` model, its training
  and evaluation pipeline, the `balanced_data/` dataset, and the published
  `receipt_cnn_clean.pt` checkpoint.
- **RAG Chatbot** (`rag_chatbot/`): the Flask `/chat` API, the FAISS index built
  from `data/policies/`, and the retrieval + generation pipeline.
- **Deployment Infrastructure**: the provided `Dockerfile` and the pre-generated
  `06_trivy_report.json` container scan.
- Attack tooling under `attacks/` and the artifacts it produces under
  `attacks/results/`.

### Out of Scope
- The production FinanceGuard environment and any live employee/compensation
  data. All testing uses the course's isolated copy.
- The upstream OpenAI / Vocareum API endpoints and their infrastructure; only
  our own use of them is in scope.
- Denial-of-service, load/stress testing, and any attack intended to disrupt
  availability.
- Modification of the clean test split (`balanced_data/test/`) — it must remain
  untouched so before/after comparisons stay valid.
- Social engineering of real people and any activity outside this repository.

## Rules of Engagement

1. **Isolated environment only.** All work runs locally against the provided
   starter repo and course-issued API credentials. No production system is
   touched and no real personal data is used.
2. **No destructive or availability-impacting actions.** No DoS, no deletion or
   corruption of source data; the poisoning attack operates only on a *copy*
   (`poisoned_data/`) and never on the clean test set.
3. **Confidential data handled as evidence, not exposed.** Where an attack
   retrieves the CONFIDENTIAL compensation document, it is cited as proof of the
   vulnerability; the data is not redistributed beyond this assessment.
4. **Reproducibility and honesty.** Every finding is backed by a saved artifact
   (JSON, PNG, metrics) and exact reproduction commands. Results are reported as
   observed, including partial successes and failures.
5. **Authorized, educational purpose.** This is a sanctioned capstone exercise;
   findings are shared only with the sponsor/reviewer.

## Success Criteria

| Attack Vector | Success Metric |
|---------------|---------------|
| FGSM Evasion | Adversarial accuracy drops progressively as ε increases, falling well below the clean baseline (target: below 50% at higher ε) while low-ε perturbations stay visually imperceptible. |
| Label-Flip Poisoning | Poisoned model shows **≥5 percentage-point** accuracy drop on the clean test set vs. the clean baseline, at a flip rate ≤10%. |
| Prompt Injection | At least 5 diverse techniques executed; ≥1 causes the bot to misbehave (reveal prompt, adopt role, repeat fake policy, or acknowledge override), with full transcript captured. |
| Data Exfiltration | At least one query causes FAISS to retrieve `executive_bonus_structure_CONFIDENTIAL.md` and/or confidential data points appear in the answer. |
| Supply Chain | Vulnerabilities categorized by severity and ≥5 distinct Dockerfile issues identified, each with a concrete remediation. |

## Deliverables

- **Red Team Charter** — this document (`charter_delivered.md`).
- **FGSM Results** (`fgsm_results_delivered.md`) — baseline metrics, per-ε
  accuracy table, visual evidence PNGs, and commentary.
- **Poisoning Results** (`poisoning_results_delivered.md`) — clean vs. poisoned
  metric comparison, label-flip evidence, and impact analysis.
- **Prompt Injection Transcript** (`prompt_injection_transcript_delivered.md`).
- **Data Exfiltration Evidence** (`data_exfiltration_evidence_delivered.md`) —
  including root-cause analysis.
- **Supply Chain Analysis** (`supply_chain_analysis_delivered.md`).
- **Vulnerability Log** (`vulnerability_log_delivered.md`) — VUL-001..VUL-005.
- **Executive Risk Summary** (`executive_summary_delivered.md`).
- **Reproduction Steps** (`reproduction_steps_delivered.md`).
- Supporting raw artifacts under `attacks/results/` (JSON reports, confusion
  matrices, FGSM and label-flip PNGs).
