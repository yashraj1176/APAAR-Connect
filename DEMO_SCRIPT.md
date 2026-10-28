# 3-minute judge demo script

1. **Overview (20 sec):** show synthetic record count, Data Quality Passport and explain that the score prioritises data cleanup, not fraud.
2. **Registry (20 sec):** search `STU-2026-001`; point out the masked APAAR-like identifier.
3. **Upload (40 sec):** download the template, upload a CSV with one duplicate and one invalid identifier, inspect rule codes and download findings. Commit only after acknowledging the preview.
4. **Review Queue (30 sec):** open a case, write a reason, resolve/dismiss it. Explain human-in-the-loop review.
5. **Seat Ledger Lab (25 sec):** increase hypothetical admissions to exceed the configured demo intake. Emphasise that actual intake rules need authoritative data.
6. **Verification Portal (25 sec):** show no response without consent, then preview limited fields with consent. Point out `SIMULATED — NOT OFFICIAL APAAR VERIFICATION`.
7. **Reports & Audit (20 sec):** export masked registry and verify the hash chain.

**Closing line:** “Our prototype makes data issues explainable, reviewable and auditable. Official identity verification and approved intake values remain behind a documented integration boundary until authorised access and authoritative rules are available.”
