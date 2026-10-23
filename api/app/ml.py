import re
from collections import defaultdict

from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline


TRAINING_EXAMPLES = {
    "Office Supplies": [
        "printer paper toner cartridges pens notebooks folders office chairs stationery",
        "desk supplies printer ink keyboard mouse monitor furniture workspace",
        "copy paper envelopes whiteboard markers ergonomic chair",
    ],
    "Cloud & Software": [
        "cloud hosting compute storage backup subscription saas software licenses",
        "collaboration platform annual software license database server hosting",
        "cloud infrastructure api platform user seats renewal",
    ],
    "Logistics": [
        "regional freight delivery courier shipping transportation handling charges",
        "interstate shipment parcel same day document delivery warehouse",
        "express delivery trucking customs and freight services",
    ],
    "Telecom": [
        "mobile voice data plans internet connectivity broadband telecom charges",
        "business phone lines cellular service network bandwidth",
        "office internet fiber connection phone service monthly bill",
    ],
    "Professional Services": [
        "technology implementation advisory consulting professional services",
        "legal audit consulting support process review strategy advisory",
        "engineering design services project management consulting",
    ],
    "Human Resources": [
        "employee medical insurance premium recruitment platform subscription",
        "payroll benefits talent acquisition background screening hiring",
        "employee training wellness health insurance human resources services",
    ],
}

_texts, _labels = [], []
for _label, _samples in TRAINING_EXAMPLES.items():
    _texts.extend(_samples)
    _labels.extend([_label] * len(_samples))

classifier = make_pipeline(
    TfidfVectorizer(ngram_range=(1, 2), strip_accents="unicode", sublinear_tf=True),
    LogisticRegression(max_iter=600, class_weight="balanced", random_state=7),
)
classifier.fit(_texts, _labels)


def classify(description: str, supplier: str = "") -> tuple[str, float]:
    probabilities = classifier.predict_proba([f"{description} {supplier}"])[0]
    index = int(probabilities.argmax())
    return str(classifier.classes_[index]), float(probabilities[index])


def normalize_supplier(name: str) -> str:
    value = re.sub(r"\b(incorporated|limited|private|pvt|ltd|llp|inc|corp|corporation|company|co)\b", " ", name.lower())
    return " ".join(re.findall(r"[a-z0-9]+", value))


def find_supplier_matches(name: str, existing_names: list[str], limit: int = 3) -> list[dict]:
    normalized = normalize_supplier(name)
    candidates: dict[str, int] = defaultdict(int)
    for existing in existing_names:
        if existing.casefold() == name.casefold():
            continue
        score = fuzz.token_set_ratio(normalized, normalize_supplier(existing))
        if score >= 72:
            candidates[existing] = max(candidates[existing], int(score))
    return [
        {"supplier": supplier, "similarity": score}
        for supplier, score in sorted(candidates.items(), key=lambda item: item[1], reverse=True)[:limit]
    ]
