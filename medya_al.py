# medya_al.py - MEDYA/SENTIMENT MODÜL

import random
from datetime import datetime


def get_media_sentiment():
    """
    Haber sentiment analizi (demo)
    """
    random.seed(datetime.now().day)

    sentiment_score = random.uniform(30, 70)
    kap_count = random.randint(0, 10)
    news_positive = random.randint(40, 60)

    if sentiment_score > 60:
        sentiment_label = 'POZITIF'
    elif sentiment_score < 40:
        sentiment_label = 'NEGATIF'
    else:
        sentiment_label = 'NÖTR'

    return {
        'status': 'OK',
        'data': {
            'sentiment_score': round(sentiment_score, 1),
            'sentiment_label': sentiment_label,
            'kap_bildirim': kap_count,
            'haber_pozitif': news_positive,
            'haber_negatif': 100 - news_positive
        },
        'score': round(sentiment_score, 1),
        'weight': 0.15,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


if __name__ == "__main__":
    medya = get_media_sentiment()
    print(f"\n{'=' * 50}")
    print(f"MEDYA/SENTIMENT")
    print(f"{'=' * 50}")
    print(f"Sentiment: {medya['data']['sentiment_label']} ({medya['data']['sentiment_score']})")
    print(f"KAP Bildirim: {medya['data']['kap_bildirim']}")
    print(f"Haberler: %{medya['data']['haber_pozitif']} pozitif")
    print(f"\nMedya Skor: {medya['score']}/100")
    print(f"{'=' * 50}")