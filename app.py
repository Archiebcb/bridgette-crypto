from flask import Flask, render_template, jsonify, request, send_from_directory
import ccxt
import random
import logging

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

@app.route('/')
def home():
    bridgette = Bridgette()
    return render_template('index.html', greeting=bridgette.greet())

@app.route('/ticker')
def get_ticker():
    bridgette = Bridgette()
    if not exchange:
        return jsonify({'message': 'Exchange setup failed', 'rate': None})
    try:
        ticker = exchange.fetch_ticker('ETH/USDT')
        rate = ticker['last']
        return jsonify({'message': bridgette.talk(), 'rate': f"ETH/USDT: {rate}"})
    except Exception as e:
        logger.error(f"Ticker fetch error: {e}")
        return jsonify({'message': f"Oops, babe: {e}", 'rate': None})

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
        return jsonify({'quote': quote})
    except Exception as e:
        logger.error(f"Simulate swap error: {e}")
        return jsonify({'quote': 0, 'error': str(e)})

@app.route('/static/<path:filename>')
def serve_static(filename):
    try:
        return send_from_directory(app.static_folder, filename)
    except Exception as e:
        logger.error(f"Static file error: {e}")
        return "Static file not found", 404

if __name__ == "__main__":
    app.run(debug=True)