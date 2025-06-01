from flask import Flask, jsonify, request, render_template_string
import requests
from datetime import datetime

app = Flask(__name__)

def fetch_market_data():
    try:
        response = requests.get("https://gamma-api.polymarket.com/markets")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching market data: {e}")
        return []

def estimate_urgency_and_duration(total_price):
    margin = round(1.0 - total_price, 4)
    if margin >= 0.05:
        return "⏳ Moderate urgency", "Likely to last a few minutes"
    elif margin >= 0.02:
        return "⚠️ Act soon", "Could disappear in under a minute"
    else:
        return "🔥 Act immediately", "Might be gone in seconds"

def detect_arbitrage(markets):
    opportunities = []
    for market in markets:
        outcomes = market.get("outcomes", [])
        prices = market.get("outcomePrices", [])
        if len(outcomes) == 2 and len(prices) == 2:
            try:
                yes = float(prices[0])
                no = float(prices[1])
                total = yes + no
                if total < 1.0:
                    urgency, estimate = estimate_urgency_and_duration(total)
                    opportunities.append({
                        "question": market.get("question", "N/A"),
                        "conditionId": market.get("conditionId", "N/A"),
                        "yes_price": yes,
                        "no_price": no,
                        "total": round(total, 4),
                        "arbitrage_margin": round((1.0 - total) * 100, 2),
                        "urgency": urgency,
                        "expected_duration": estimate,
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    })
            except (ValueError, TypeError):
                continue
    return opportunities

@app.route('/')
def root():
    return jsonify({
        "message": "Polymarket Arbitrage Detector API ✅",
        "try": "/arbs"
    })

@app.route('/arbs')
def arbs():
    format_type = request.args.get("format", "html").lower()
    data = detect_arbitrage(fetch_market_data())
    timestamp = datetime.utcnow().isoformat() + "Z"

    if format_type == "json":
        if not data:
            return jsonify({
                "message": "❌ No arbitrage opportunities right now.",
                "checked_at": timestamp,
                "hint": "Try refreshing later."
            })
        return jsonify(data)

    # HTML Response with Auto-Refresh
    html = """
    <html>
    <head>
        <meta http-equiv="refresh" content="10">
        <title>Polymarket Arbitrage</title>
        <style>
            body { font-family: Arial; background: #111; color: #0f0; padding: 20px; }
            .op { border-bottom: 1px solid #0f0; margin-bottom: 12px; padding-bottom: 12px; }
        </style>
    </head>
    <body>
        <h2>🔁 Polymarket Arbitrage Opportunities</h2>
        <p>Last checked: {{ time }}</p>
        {% if not arbs %}
            <p><strong>No arbitrage opportunities right now.</strong></p>
        {% else %}
            {% for op in arbs %}
                <div class="op">
                    <strong>{{ op.question }}</strong><br>
                    YES: {{ op.yes_price }} | NO: {{ op.no_price }} | Total: {{ op.total }}<br>
                    Margin: {{ op.arbitrage_margin }}%<br>
                    Urgency: {{ op.urgency }}<br>
                    Expected Duration: {{ op.expected_duration }}<br>
                </div>
            {% endfor %}
        {% endif %}
        <p>⏳ Auto-refreshing every 10 seconds...</p>
    </body>
    </html>
    """
    return render_template_string(html, arbs=data, time=timestamp)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
