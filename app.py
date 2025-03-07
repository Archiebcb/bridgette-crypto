from flask import Flask, render_template, jsonify, request, send_from_directory
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
            "Yo, darling! Let’s bridge some crypto—futuristic style!"
        ])
    def talk(self):
        return random.choice([
            "Scanning the market, hun—hold tight!",
            "Bridge is glowing, stud—rates incoming!",
            "Future’s here, babe—watch me shine!"
        ])

# Mock exchange rates for testing
mock_rates = {
    'ETH/USDT': 2500.00,
    'SOL/USDT': 150.00,
    'SRM/USDT': 1.50,
    'RAY/USDT': 2.00,
    'XRP/USDT': 2.50,
    'BTC/USDT': 60000.00,
    'ADA/USDT': 1.00
}

# Database setup
def init_db():
    try:
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
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

init_db()

def save_swap(from_chain, from_token, amount, to_chain, to_token, quote, error=None):
    try:
        conn = sqlite3.connect('bridgette.db')
        c = conn.cursor()
        c.execute("INSERT INTO swaps (timestamp, from_chain, from_token, amount, to_chain, to_token, quote, error) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (datetime.now().isoformat(), from_chain, from_token, amount, to_chain, to_token, quote, error))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to save swap: {e}")

@app.route('/')
def home():
    bridgette = Bridgette()
    return render_template('index.html', greeting=bridgette.greet())

@app.route('/ticker')
def get_ticker():
    bridgette = Bridgette()
    rates = mock_rates.copy()
    return jsonify({'message': bridgette.talk(), 'rates': rates})

@app.route('/available_pairs')
def available_pairs():
    pairs = {
        'cryptocom': ['ETH/USDT', 'XRP/USDT', 'BTC/USDT', 'ADA/USDT'],
        'solana': ['SOL/USDT', 'SRM/USDT', 'RAY/USDT']
    }
    return jsonify({'pairs': pairs})

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
        from_rate = mock_rates.get(f"{from_token.split('/')[0]}/USDT", 1.0)
        to_rate = mock_rates.get(f"{to_token.split('/')[0]}/USDT", 1.0)
        if from_rate == 0 or to_rate == 0:
            raise ValueError("Invalid rate detected")
        rate = from_rate / to_rate if to_rate != 0 else 1.0
        quote = amount * rate
        save_swap(from_chain, from_token, amount, to_chain, to_token, quote)
        return jsonify({'quote': quote})
    except Exception as e:
        logger.error(f"Simulate swap error: {str(e)}")
        save_swap(from_chain, from_token, amount, to_chain, to_token, 0, str(e))
        return jsonify({'quote': 0, 'error': str(e)})

@app.route('/history')
def get_history():
    try:
        conn = sqlite3.connect('bridgette.db')
        c = conn.cursor()
        c.execute("SELECT * FROM swaps ORDER BY timestamp DESC")
        history = c.fetchall()
        conn.close()
        return jsonify({'history': [{'id': row[0], 'timestamp': row[1], 'from_chain': row[2], 'from_token': row[3], 'amount': row[4], 'to_chain': row[5], 'to_token': row[6], 'quote': row[7], 'error': row[8]} for row in history]})
    except Exception as e:
        logger.error(f"History fetch error: {e}")
        return jsonify({'history': []})

@app.route('/analytics')
def get_analytics():
    try:
        conn = sqlite3.connect('bridgette.db')
        c = conn.cursor()
        c.execute("SELECT SUM(amount), MAX(quote) FROM swaps WHERE error IS NULL")
        total_bridged, best_trade = c.fetchone()
        conn.close()
        return jsonify({'total_bridged': total_bridged or 0, 'best_trade': best_trade or 0})
    except Exception as e:
        logger.error(f"Analytics fetch error: {e}")
        return jsonify({'total_bridged': 0, 'best_trade': 0})

@app.route('/static/<path:filename>')
def serve_static(filename):
    try:
        return send_from_directory(app.static_folder, filename)
    except Exception as e:
        logger.error(f"Static file error: {e}")
        return "Static file not found", 404

if __name__ == "__main__":
    app.run(debug=True)