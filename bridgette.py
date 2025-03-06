from flask import Flask, render_template, jsonify
import ccxt
import random

app = Flask(__name__)

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
    return ccxt.cryptocom({
        'apiKey': 'qs8bkoi6De3se4D6Smw2Tw',
        'secret': 'cxakp_SbQK3oSt3n5mVFqi6opCTk',
        'enableRateLimit': True,
    })

exchange = setup_exchange()

# Routes
@app.route('/')
def home():
    bridgette = Bridgette()
    return render_template('index.html', greeting=bridgette.greet())

@app.route('/ticker')
def get_ticker():
    bridgette = Bridgette()
    try:
        ticker = exchange.fetch_ticker('ETH/USDT')
        rate = ticker['last']
        return jsonify({'message': bridgette.talk(), 'rate': f"ETH/USDT: {rate}"})
    except Exception as e:
        return jsonify({'message': f"Oops, babe: {e}", 'rate': None})

if __name__ == "__main__":
    app.run(debug=True)