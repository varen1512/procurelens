from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

POLICIES = [
    {
        "source": "Procurement Policy · Supplier Onboarding",
        "section": "2.1 Due diligence",
        "text": "Before a supplier is activated, the requester must provide legal name, tax details, bank verification, and a business justification. Procurement reviews duplicate supplier records before creating a new vendor profile.",
    },
    {
        "source": "Procurement Policy · Purchase Approval",
        "section": "3.2 Approval thresholds",
        "text": "Purchase requests up to INR 25,000 require manager approval. Requests from INR 25,001 to INR 250,000 require both manager and procurement approval. Requests above INR 250,000 also require finance approval before a purchase order is issued.",
    },
    {
        "source": "Procurement Policy · Competitive Quotes",
        "section": "4.1 Sourcing",
        "text": "Purchases above INR 50,000 should include at least three comparable supplier quotes unless an approved single-source exception is documented. The exception record must include rationale and approver.",
    },
    {
        "source": "Procurement Policy · Invoice Controls",
        "section": "5.4 Duplicate invoices",
        "text": "Accounts payable must check supplier identity, invoice number, amount, and invoice date before payment. Suspected duplicate invoices are placed on hold and escalated to the invoice owner for review.",
    },
    {
        "source": "Procurement Policy · Software and Cloud",
        "section": "6.3 Software subscriptions",
        "text": "Software and cloud subscriptions require an identified business owner, data classification review, security review when company data is processed, and documented renewal dates. Auto-renewal terms must be recorded.",
    },
]

_vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
_matrix = _vectorizer.fit_transform([item["text"] for item in POLICIES])


def retrieve_policy(question: str, top_k: int = 3) -> list[dict]:
    query = _vectorizer.transform([question])
    scores = cosine_similarity(query, _matrix).ravel()
    ranked = scores.argsort()[::-1][:top_k]
    return [
        {**POLICIES[int(index)], "score": round(float(scores[index]), 3)}
        for index in ranked
        if scores[index] > 0
    ]
