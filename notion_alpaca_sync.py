
from datetime import datetime
import requests
from flask import Flask, request, jsonify
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

def get_stock_price(ticker: str) -> float:
    try:
        trade = alpaca.get_latest_trade(ticker)
        return trade.price
    except Exception as e:
        print(f"Error getting price for {ticker}: {e}")
        return 0.0

@app.route('/sync', methods=['GET'])
def sync_stocks():
    updated_pages = []
    deleted_pages = []

    response = notion.databases.query(database_id=NOTION_DATABASE_ID)
    for page in response.get('results', []):
        page_id = page["id"]
        properties = page["properties"]
        try:
            ticker = properties["Name"]["title"][0]["plain_text"]
            quantity = properties.get("Quantity", {}).get("number", 0)
            avg_price = properties.get("Average Price", {}).get("number", 0)

            if quantity == 0:
                notion.pages.update(page_id=page_id, archived=True)
                deleted_pages.append(ticker)
                continue

            current_price = get_stock_price(ticker)
            unrealized_pl = (current_price - avg_price) * quantity
            pl_percent = ((current_price - avg_price) / avg_price) * 100 if avg_price else 0
            market_value = current_price * quantity

            notion.pages.update(
                page_id=page_id,
                properties={
                    "Current Price": {"number": current_price},
                    "Unrealized P&L": {"number": unrealized_pl},
                    "P&L %": {"number": pl_percent},
                    "Market Value": {"number": market_value},
                    "Last Updated": {"date": {"start": datetime.utcnow().isoformat()}}
                }
            )
            updated_pages.append(ticker)
        except Exception as e:
            print(f"Error processing page: {e}")

    return jsonify({
        "updated": updated_pages,
        "deleted": deleted_pages,
        "status": "sync complete"
    })

if __name__ == '__main__':
    app.run(debug=True)
