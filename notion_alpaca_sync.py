from datetime import datetime
import requests
from flask import Flask, jsonify
from notion_client import Client as NotionClient
import alpaca_trade_api as tradeapi

# Fixed credentials
NOTION_TOKEN = "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"
NOTION_DATABASE_ID = "234a7f28f361806f8d41eb843ca04e8e"
ALPACA_API_KEY = "AKZY72TYY4BU9QMZGMSR"
ALPACA_SECRET_KEY = "5cu8LCaoW2Q78IBgg3fIOKFLvWeOlxMQGJ9iPdbQ"
ALPACA_BASE_URL = "https://api.alpaca.markets"

app = Flask(__name__)

# Initialize clients
notion = NotionClient(auth=NOTION_TOKEN)
alpaca = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL)

def get_existing_tickers_from_notion():
    response = notion.databases.query(database_id=NOTION_DATABASE_ID)
    tickers = {}
    for page in response.get('results', []):
        try:
            ticker = page["properties"]["Name"]["title"][0]["plain_text"]
            tickers[ticker] = page["id"]
        except:
            continue
    return tickers

@app.route('/sync', methods=['GET'])
def sync_stocks():
    updated_pages = []
    created_pages = []
    deleted_pages = []

    # Step 1: Fetch current positions from Alpaca
    alpaca_positions = {p.symbol: p for p in alpaca.list_positions()}

    # Step 2: Fetch existing pages from Notion
    notion_pages = get_existing_tickers_from_notion()

    for ticker, position in alpaca_positions.items():
        qty = float(position.qty)
        avg_price = float(position.avg_entry_price)
        current_price = float(position.current_price)
        unrealized_pl = float(position.unrealized_pl)
        pl_percent = float(position.unrealized_plpc) * 100
        market_value = float(position.market_value)

        props = {
            "Name": {"title": [{"text": {"content": ticker}}]},
            "Average Price": {"number": avg_price},
            "Current Price": {"number": current_price},
            "Quantity": {"number": qty},
            "Unrealized P&L": {"number": unrealized_pl},
            "P&L %": {"number": pl_percent},
            "Market Value": {"number": market_value},
            "Last Updated": {"date": {"start": datetime.utcnow().isoformat()}}
        }

        if ticker in notion_pages:
            notion.pages.update(page_id=notion_pages[ticker], properties=props)
            updated_pages.append(ticker)
        else:
            notion.pages.create(parent={"database_id": NOTION_DATABASE_ID}, properties=props)
            created_pages.append(ticker)

    # Step 3: Delete Notion pages for positions no longer in Alpaca
    alpaca_tickers = set(alpaca_positions.keys())
    for ticker, page_id in notion_pages.items():
        if ticker not in alpaca_tickers:
            notion.pages.update(page_id=page_id, archived=True)
            deleted_pages.append(ticker)

    return jsonify({
        "updated": updated_pages,
        "created": created_pages,
        "deleted": deleted_pages,
        "status": "sync complete"
    })

if __name__ == '__main__':
    app.run(debug=True)
