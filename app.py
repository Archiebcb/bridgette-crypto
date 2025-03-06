from flask import Flask, render_template, jsonify, request, send_from_directory
import ccxt
import random
import sqlite3
import logging
from datetime import datetime
import solana.rpc.api as solrpc
from solana.publickey import PublicKey
import requests

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

# Setup exchanges
def setup_exchanges():
    exchanges = {}
    try:
        exchanges['cryptocom'] = ccxt.cryptocom({
            'apiKey': 'qs8bkoi6De3se4D6Smw2Tw',
            'secret': 'cxakp_SbQK3oSt3n5mVFqi6opCTk',
            'enableRateLimit': True,
        })
    except Exception as e:
        logger.error(f"Crypto.com setup failed: {e}")
        exchanges['cryptocom'] = None

    try:
        exchanges['solana'] = solrpc.Client("https://api.mainnet-beta.solana.com")
    except Exception as e:
        logger.error(f"Solana setup failed: {e}")
        exchanges['solana'] = None

    return exchanges

exchanges = setup_exchanges()

# Database setup
def init_db():
    conn = sqlite3.connect('bridgette.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS swaps
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT,
                  from_chain TEXT,
                  from_token TEXT,
                  amount REAL,
                  to_chain TEXT,
                  to_token TEXT,
                  quote REAL,
                  error TEXT)''')
    conn.commit()
    conn.close()

init_db()

def save_swap(from_chain, from_token, amount, to_chain, to_token, quote, error=None):
    conn = sqlite3.connect('bridgette.db')
    c = conn.cursor()
    c.execute("INSERT INTO swaps (timestamp, from_chain, from_token, amount, to_chain, to_token, quote, error) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
              (datetime.now().isoformat(), from_chain, from_token, amount, to_chain, to_token, quote, error))
    conn.commit()
    conn.close()

def get_solana_price(token):
    try:
        # Use CoinGecko API as a simple public price feed (mock for now)
        response = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={token.lower()}&vs_currencies=usd")
        data = response.json()
        return data[token.lower()]['usd'] if token.lower() in data else 150.00  # Default to 150 if unavailable
    except Exception as e:
        logger.error(f"Solana price fetch error: {e}")
        return 150.00  # Mock fallback

@app.route('/')
def home():
    bridgette = Bridgette()
    return render_template('index.html', greeting=bridgette.greet())

@app.route('/ticker')
def get_ticker():
    bridgette = Bridgette()
    rates = {}
    try:
        if exchanges['cryptocom']:
            ticker = exchanges['cryptocom'].fetch_ticker('ETH/USDT')
            rates['ETH/USDT'] = f"ETH/USDT: {ticker['last']}"
        if exchanges['solana']:
            sol_price = get_solana_price('solana')
            rates['SOL/USDT'] = f"SOL/USDT: {sol_price}"
        return jsonify({'message': bridgette.talk(), 'rates': rates})
    except Exception as e:
        logger.error(f"Ticker fetch error: {e}")
        return jsonify({'message': f"Oops, babe: {e}", 'rates': {}})

@app.route('/available_pairs')
def available_pairs():
    pairs = {'cryptocom': [], 'solana': []}
    try:
        if exchanges['cryptocom']:
            markets = exchanges['cryptocom'].load_markets()
            pairs['cryptocom'] = [pair for pair in markets.keys() if markets[pair]['active'] and markets[pair]['quote'] == 'USDT']
        if exchanges['solana']:
            # Mock Solana pairs (using CoinGecko-compatible tokens)
            pairs['solana'] = ['SOL/USDT', 'SRM/USDT', 'RAY/USDT']  # Expand with real pairs later
        logger.debug(f"Fetched pairs: {pairs}")
        return jsonify({'pairs': pairs})
    except Exception as e:
        logger.error(f"Pairs fetch error: {e}")
        return jsonify({'error': str(e), 'pairs': {}})

@app.route('/simulate_swap', methods=['POST'])
def simulate_swap():
    data = request.json
    from_chain = data.get('from_chain')
    from_token = data.get('from_token')
    amount = data.get('amount')
    to_chain = data.get('to_chain')
    to_token = data.get('to_token')

    if from_chain not in exchanges or to_chain not in exchanges:
        return jsonify({'quote': 0, 'error': 'Chain not supported'})

    try:
        # Simplified cross-chain rate simulation
        rate = 1.0
        if from_chain == 'cryptocom':
            ticker = exchanges['cryptocom'].fetch_ticker(f'{from_token}/USDT')
            rate *= ticker['last']
        elif from_chain == 'solana':
            rate *= get_solana_price(from_token)

        if to_chain == 'cryptocom':
            ticker = exchanges['cryptocom'].fetch_ticker(f'{to_token}/USDT')
            rate /= ticker['last']
        elif to_chain == 'solana':
            rate /= get_solana_price(to_token)

        quote = amount * rate
        save_swap(from_chain, from_token, amount, to_chain, to_token, quote)
        return jsonify({'quote': quote})
    except Exception as e:
        logger.error(f"Simulate swap error: {e}")
        save_swap(from_chain, from_token, amount, to_chain, to_token, 0, str(e))
        return jsonify({'quote': 0, 'error': str(e)})

@app.route('/history')
def get_history():
    conn = sqlite3.connect('bridgette.db')
    c = conn.cursor()
    c.execute("SELECT * FROM swaps ORDER BY timestamp DESC")
    history = c.fetchall()
    conn.close()
    return jsonify({'history': [{'id': row[0], 'timestamp': row[1], 'from_chain': row[2], 'from_token': row[3], 'amount': row[4], 'to_chain': row[5], 'to_token': row[6], 'quote': row[7], 'error': row[8]} for row in history]})

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