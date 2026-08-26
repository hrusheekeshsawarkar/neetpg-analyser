import json
from topic_rules import classify_topics

with open("analysis/data/merged_questions.json") as f:
    qs = json.load(f)

print(f"Total: {len(qs)}")
before = sum(
    1 for q in qs if q.get("topic_clean", "").lower() in ["general", "unknown"]
)
print(f"General/Unknown before: {before}")

qs = classify_topics(qs)

after = sum(1 for q in qs if q.get("topic_clean", "").lower() in ["general", "unknown"])
print(f"General/Unknown after: {after}")

with open("analysis/data/merged_questions.json", "w") as f:
    json.dump(qs, f, indent=2, ensure_ascii=False)

from collections import Counter

tc = Counter(q["topic_clean"] for q in qs)
print(f"\nTop 20 topics:")
for t, c in sorted(tc.items(), key=lambda x: -x[1])[:20]:
    print(f"  {t}: {c}")
