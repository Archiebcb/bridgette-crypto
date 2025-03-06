from flask import Flask, render_template, jsonify, request, send_from_directory
import ccxt
import random
import sqlite3
import logging
from datetime import datetime

app = Flask(__name__, static_folder='static')

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Bridgette's personality
class Bridgette:
    def greet(self):
        return random.choice([
            "Hey, sexy! Welcome to my bridge—crypto’s flowing!",
            "What’s up, babe? Bridgette’s here to rock your tokens!",
            "Yo, darling! Let’s bridge some shit—futuristic style!"
        ])
    def talk(self):
        return random.choice([
            "Scanning the market, hun—hold tight!",
            "Bridge is lit, stud—rates coming your way!",
            "Future’s now, babe—watch me flex!"
        ])

# Crypto.com setup
def setup_exchange():
    try:
        return ccxt.cryptocom({
            'apiKey': 'qs8bkoi6De3se4D6Smw2Tw',
            'secret': 'cxakp_SbQK3oSt3n5mVFqi6opCTk',
            'enableRateLimit': True,
        })
    except Exception as e:
        logger.error(f"Exchange setup failed: {e}")
        return None

exchange = setup_exchange()

# Database setup
def init_db():
    conn = sqlite3.connect('bridgette.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS swaps
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT,
                  from_token TEXT,
                  amount REAL,
                  to_token TEXT,
                  quote REAL,
                  error TEXT)''')
    conn.commit()
    conn.close()

init_db()

def save_swap(from_token, amount, to_token, quote, error=None):
    conn = sqlite3.connect('bridgette.db')
    c = conn.cursor()
    c.execute("INSERT INTO swaps (timestamp, from_token, amount, to_token, quote, error) VALUES (?, ?, ?, ?, ?, ?)",
              (datetime.now().isoformat(), from_token, amount, to_token, quote, error))
    conn.commit()
    conn.close()

@app.route('/')
def home():
    bridgette = Bridgette()
    return render_template('index.html', greeting=bridgette.greet())

@app.route('/ticker')
def get_ticker():
    bridgette = Bridgette()
    if not exchange:
        return jsonify({'message': 'Exchange setup failed', 'rates': {}})
    try:
        pairs = ['ETH/USDT', 'BTC/USDT', 'XRP/USDT']
        rates = {}
        for pair in pairs:
            try:
                ticker = exchange.fetch_ticker(pair)
                rates[pair] = f"{pair}: {ticker['last']}"
            except Exception as e:
                logger.error(f"Ticker fetch error for {pair}: {e}")
                rates[pair] = f"{pair}: N/A"
        return jsonify({'message': bridgette.talk(), 'rates': rates})
    except Exception as e:
        logger.error(f"Ticker fetch error: {e}")
        return jsonify({'message': f"Oops, babe: {e}", 'rates': {}})

@app.route('/available_pairs')
def available_pairs():
    if not exchange:
        logger.error("Exchange not initialized")
        return jsonify({'error': 'Exchange not initialized', 'pairs': []})
    try:
        markets = exchange.load_markets()
        pairs = [pair for pair in markets.keys() if markets[pair]['active'] and markets[pair]['quote'] == 'USDT']
        logger.debug(f"Fetched pairs: {pairs}")
        return jsonify({'pairs': pairs})
    except Exception as e:
        logger.error(f"Pairs fetch error: {e}")
        return jsonify({'error': str(e), 'pairs': []})

@app.route('/simulate_swap', methods=['POST'])
def simulate_swap():
    if not exchange:
        return jsonify({'quote': 0, 'error': 'Exchange not initialized'})
    data = request.json
    from_token = data.get('from')
    amount = data.get('amount')
    to_token = data.get('to')
    try:
        ticker = exchange.fetch_ticker(f'{from_token}/{to_token}')
        rate = ticker['last']
        quote = amount * rate
        save_swap(from_token, amount, to_token, quote)
        return jsonify({'quote': quote})
    except Exception as e:
        logger.error(f"Simulate swap error: {e}")
        save_swap(from_token, amount, to_token, 0, str(e))
        return jsonify({'quote': 0, 'error': str(e)})

@app.route('/history')
def get_history():
    conn = sqlite3.connect('bridgette.db')
    c = conn.cursor()
    c.execute("SELECT * FROM swaps ORDER BY timestamp DESC")
    history = c.fetchall()
    conn.close()
    return jsonify({'history': [{'id': row[0], 'timestamp': row[1], 'from_token': row[2], 'amount': row[3], 'to_token': row[4], 'quote': row[5], 'error': row[6]} for row in history]})

@app.route('/analytics')
def get_analytics():
    conn = sqlite3.connect('bridgette.db')
    c = conn.cursor()
    c.execute("SELECT SUM(amount), MAX(quote) FROM swaps WHERE error IS NULL")
    total_bridged, best_trade = c.fetchone()
    conn.close()
    return jsonify({'total_bridged': total_bridged or 0, 'best_trade': best_trade or 0})

@app.route('/static/<path:filename>')
def serve_static(filename):
    try:
        return send_from_directory(app.static_folder, filename)
    except Exception as e:
        logger.error(f"Static file error: {e}")
        return "Static file not found", 404

if __name__ == "__main__":
    app.run(debug=True)