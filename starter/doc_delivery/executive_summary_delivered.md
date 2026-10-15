# Executive Risk Summary

## Overview

We conducted an authorized red-team assessment of FinanceGuard's three AI
systems — the receipt-screening image classifier, the employee expense chatbot,
and the container that runs them. In an isolated test environment we exercised
five attacks. **All five succeeded to some degree.** The most serious finding is
that the expense chatbot freely hands confidential executive-compensation data
(salaries, bonuses, stock-option terms) to anyone who asks, because the system
has no access controls on what information it can retrieve.

## Risk Dashboard

| System | Risk Level | Key Finding |
|--------|-----------|-------------|
| Receipt Classifier | **HIGH** | Can be fooled by invisible image tampering, and can be silently crippled by corrupting a small amount of training data. |
| RAG Chatbot | **CRITICAL** | Leaks confidential executive pay data to any user; 6 of 6 probing questions succeeded. |
| Deployment Infrastructure | **HIGH** | Runs with maximum privileges (root) and may bake secrets into the shipped image, amplifying any breach. |

## Findings Summary

### 1. Chatbot leaks confidential executive compensation — CRITICAL

**Business Impact:** Any employee (or anyone who reaches the chatbot) can extract
restricted C-suite salary ranges, bonus formulas, and stock-option details that
are meant for the Compensation Committee and CHRO only. This is a direct
confidentiality breach with legal, regulatory, and employee-relations fallout,
and it works even when the chatbot "refuses," because the data is pulled before
the refusal. This is the single most urgent issue.

### 2. Receipt classifier can be silently poisoned — HIGH

**Business Impact:** Corrupting under 10% of the training data cut the model's
real-world accuracy nearly in half (94% to 57%) while looking completely normal.
An insider or a compromised data supplier could quietly degrade expense
screening, letting fraudulent or invalid submissions through undetected.

### 3. Receipt classifier can be fooled by invisible tampering — HIGH

**Business Impact:** An attacker can add human-invisible "noise" to an image to
make the classifier accept a non-receipt as valid (or reject a real one),
defeating automated expense checks without a reviewer noticing anything unusual.

### 4. Container runs with excessive privilege and may expose secrets — HIGH

**Business Impact:** The application runs as the all-powerful "root" user and its
build may embed API keys and internal files into the shipped image. If any
component is breached, the attacker immediately gets maximum control and
potentially the organization's API credentials — turning a small foothold into a
full compromise.

### 5. Chatbot can be manipulated by crafted instructions — MEDIUM

**Business Impact:** The chatbot's own refusals held up reasonably well, but
crafted messages can still steer it toward confidential material. On its own this
is moderate; combined with Finding 1 it becomes a reliable path to data
disclosure.

## Prioritized Remediation

| Priority | Action | Effort | Impact |
|----------|--------|--------|--------|
| 1 | Remove confidential documents from the chatbot's shared knowledge base and add access controls (authentication + per-document classification filtering) so restricted data is never retrieved for unauthorized users. | Medium | **Critical** — closes the data-leak |
| 2 | Harden the container: run as a non-root user and exclude secrets, credentials, and model files from the image. | Low | High — limits blast radius of any breach |
| 3 | Protect the classifier's training pipeline: verify data provenance, audit labels, and monitor live accuracy against a trusted reference set. | Medium | High — prevents silent poisoning |
| 4 | Add robustness to the classifier (adversarial training + input preprocessing) and keep human review on low-confidence decisions. | Medium | Medium — blunts evasion attacks |

## Conclusion

The organization's AI systems are functional but not yet secure. **The top
recommendation is to immediately close the confidential-data leak in the expense
chatbot (Priority 1):** it is the highest-impact, actively-exploitable finding,
it requires no sophistication to trigger, and it exposes the company's most
sensitive compensation information. Container hardening and training-pipeline
integrity should follow close behind. None of these fixes is large; the risk
today comes from controls that were simply never put in place.
