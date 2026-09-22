from src.news import NewsItem, score_headline, summarize_news


def test_headline_scoring_and_risk_gate():
    positive_score, positive_impact = score_headline("Bitcoin adoption expands after institutional approval")
    negative_score, negative_impact = score_headline("Crypto exchange hack triggers liquidation and regulatory crackdown")
    assert positive_score > 0
    assert negative_score < 0
    assert positive_impact == "HIGH"
    assert negative_impact == "HIGH"
    bank_score, _ = score_headline("Major bank expands its digital asset research team")
    assert bank_score >= 0

    summary = summarize_news(
        [
            NewsItem("Bitcoin hack and liquidation", "https://a.example", "a.example", "", -50, "HIGH"),
            NewsItem("Ethereum exploit and crackdown", "https://b.example", "b.example", "", -50, "HIGH"),
        ]
    )
    assert summary.risk_gate is True
    assert summary.label == "CAUTIOUS / NEGATIVE"
