"""
hints.py - extra, clause-specific reading guidance that is inserted into the prompt
(only the prompts that contain the token <<CLAUSE_HINTS>> use it: v3, v4, v5).
These are GENERAL domain rules about how Indian/public works contracts are worded - they are not copied
from any particular contract. If a hint is wrong for your documents, edit it here and log the change.
"""

HINTS = {
    "payment_terms": """\
- Look for the time between a bill/statement being submitted or certified and the employer PAYING it.
  Typical wording: "shall pay within X days", "payment within X days of certification",
  "period for honouring certificates", "time for payment", "stage payment statement".
- A contract may contain several periods (engineer certifies within A days; employer pays within B days;
  final bill within C days). numeric_value = the period for paying INTERIM / running bills. Put the others in notes.
  If only the certification period exists and no payment period, report it and say so in notes.
- Record day_type: "working" or "calendar" only if the text says so, otherwise null.
- Mention interest on delayed payment in notes if it is stated.
- Do NOT report: payment to labour, advance recovery periods, defects liability periods, or bid validity.""",

    "retention": """\
- Three different things are often confused. Keep them apart:
  (a) the per-bill deduction rate (e.g. "x% of each bill is retained")  -> numeric_value
  (b) an overall maximum on the total retained (e.g. "not to exceed y% of contract value") -> cap_percent
  (c) a one-time deposit paid at the start (earnest money, initial security deposit, performance security) -> NOT retention
      unless the document says it is deducted from running bills.
- NEVER report the cap as the per-bill rate. If only a cap exists, set numeric_value to null and cap_percent to the cap.
- Other names: retention money, security deposit, guarantee money, amount retained, amount withheld.
- unit: say what the percentage is of ("% of each bill", "% of contract value"). Note when it is released
  (completion, end of defects liability period, in two stages).""",

    "advance": """\
- Distinguish: mobilisation advance (paid at the start), equipment advance, and secured advance on materials.
  numeric_value = the main mobilisation / advance payment percentage of contract price. Mention the others in notes.
- An "advance payment guarantee/security" is the guarantee for the advance, NOT the advance itself.
- Record in notes: whether interest is charged and how the advance is recovered (instalments, % of each bill).
- If the contract says no advance will be paid, set found=false and explicitly_excluded=true and quote that sentence.""",

    "liquidated_damages": """\
- Report ONLY delay damages payable by the CONTRACTOR for late completion (or late milestones). Ignore damages
  payable by the employer/authority, damages for defects, and damages for late submission of security.
- Convert wording to a rate plus unit: "half percent per week" -> 0.5 with unit "% per week";
  "0.75% per month" -> 0.75 with unit "% per month"; "0.1% per day" -> 0.1 with unit "% per day".
  If the rate is a fixed money amount per day/week, set numeric_value to null, unit "Rs per day" (or similar) and
  write the amount in notes.
- cap_percent = the maximum total as a percentage ("maximum 5% of contract value", "not exceeding 10%").
- If several tiers or milestones exist, report the main completion rate and describe the others in notes.
- Same rate may appear in a summary table and in the clause: if they agree, use either; if they differ, report the
  contract-specific one and describe the conflict in notes.""",

    "escalation": """\
- found=true only if there is an actual mechanism that adjusts payments for price changes: "price variation",
  "price adjustment", "price escalation", "rise and fall", or a formula using indices.
- If the text says rates are firm / fixed / no escalation or price variation on any account, set found=false,
  explicitly_excluded=true, and quote that sentence.
- A clause that applies only to some items, only after the original completion date, or only above a threshold
  still counts as found=true: describe the limits in notes.
- Do NOT confuse with "variations" in the sense of change orders / extra work, or with quantity variation limits.
- numeric_value is normally null (the clause is a formula). Do not invent a percentage.""",

    "performance_security": """\
- numeric_value = the main performance security / performance guarantee as a percentage of contract price or bid price.
- Keep apart: earnest money / bid security (before award), additional performance security (for abnormally low bids),
  advance payment guarantee, and security deposit deducted from bills. Report the main performance security; mention
  the others in notes.
- Note in notes whether it may be a bank guarantee, and its validity period if stated.
- If the percentage is a blank or placeholder, found=true (the clause exists) and numeric_value=null.""",
}
