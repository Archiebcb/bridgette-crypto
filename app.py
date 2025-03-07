from flask import Flask, render_template, jsonify, request, send_from_directory
import ccxt
import random
import sqlite3
import logging
from datetime import datetime
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
            "Yo, darling! Let’s bridge some crypto—futuristic style!"
        ])
    def talk(self):
        return random.choice([
            "Scanning the market, hun—hold tight!",
            "Bridge is glowing, stud—rates incoming!",
            "Future’s here, babe—watch me shine!"
        ])

# Setup exchanges
def setup_exchanges():
    exchanges = {}
    try:
        exchanges['cryptocom'] = ccxt.cryptocom({
            'apiKey': 'YOUR_VALID_API_KEY',  # Replace with your actual API key
            'secret': 'YOUR_VALID_SECRET',   # Replace with your actual secret
            'enableRateLimit': True,
        })
        exchanges['cryptocom'].load_markets()
        logger.info("Crypto.com exchange initialized successfully")
    except Exception as e:
        logger.error(f"Crypto.com setup failed: {e}", exc_info=True)
        exchanges['cryptocom'] = None
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
        response = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={token.lower()}&vs_currencies=usd")
        data = response.json()
        return data[token.lower()]['usd'] if token.lower() in data else 150.00
    except Exception as e:
        logger.error(f"Solana price fetch error: {e}")
        return 150.00

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
            rates['ETH/USDT'] = ticker['last']
        sol_price = get_solana_price('solana')
        rates['SOL/USDT'] = sol_price
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
        pairs['solana'] = ['SOL/USDT', 'SRM/USDT', 'RAY/USDT']
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

    if not all([from_chain, from_token, amount, to_chain, to_token]):
        save_swap(from_chain, from_token, amount, to_chain, to_token, 0, 'Missing required fields')
        return jsonify({'quote': 0, 'error': 'Missing required fields'})

    if from_chain not in ['cryptocom', 'solana'] or to_chain not in ['cryptocom', 'solana']:
        save_swap(from_chain, from_token, amount, to_chain, to_token, 0, 'Chain not supported')
        return jsonify({'quote': 0, 'error': 'Chain not supported'})

    try:
        rate = 1.0
        if from_chain == 'cryptocom' and exchanges['cryptocom']:
            pair = f"{from_token}/USDT"
            markets = exchanges['cryptocom'].load_markets()
            if pair not in markets or not markets[pair]['active']:
                raise Exception(f"Invalid token pair {pair} for Crypto.com")
            ticker = exchanges['cryptocom'].fetch_ticker(pair)
            rate *= ticker['last'] / 100  # Adjust rate for realistic conversion
        elif from_chain == 'solana':
            rate *= get_solana_price(from_token) / 100

        if to_chain == 'cryptocom' and exchanges['cryptocom']:
            pair = f"{to_token}/USDT"
            markets = exchanges['cryptocom'].load_markets()
            if pair not in markets or not markets[pair]['active']:
                raise Exception(f"Invalid token pair {pair} for Crypto.com")
            ticker = exchanges['cryptocom'].fetch_ticker(pair)
            rate /= ticker['last'] / 100
        elif to_chain == 'solana':
            rate /= get_solana_price(to_token) / 100

        quote = amount * rate
        save_swap(from_chain, from_token, amount, to_chain, to_token, quote)
        return jsonify({'quote': quote})
    except Exception as e:
        logger.error(f"Simulate swap error: {str(e)}", exc_info=True)
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