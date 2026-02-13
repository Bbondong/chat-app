from flask import Flask, render_template, request, jsonify, session
import os
import requests
import openai
from dotenv import load_dotenv
import json
import random

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'votre-cle-secrete-par-defaut')

# Configuration de l'API OpenAI
openai.api_key = os.environ.get('OPENAI_API_KEY')

# Configuration Google AdSense (à mettre dans les templates)
ADSENSE_CLIENT_ID = os.environ.get('ADSENSE_CLIENT_ID', 'ca-pub-XXXXXXXXXXXXXXX')

class VPNService:
    """Service VPN pour changer l'IP apparente"""
    
    @staticmethod
    def get_free_vpn_proxies():
        """Récupère une liste de proxies VPN gratuits"""
        # Sources de proxies gratuits (à utiliser avec modération)
        proxy_sources = [
            'https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all',
            'https://www.proxy-list.download/api/v1/get?type=http'
        ]
        
        proxies = []
        for source in proxy_sources:
            try:
                response = requests.get(source, timeout=10)
                if response.status_code == 200:
                    proxy_list = response.text.strip().split('\r\n')
                    proxies.extend([p for p in proxy_list if p])
            except:
                continue
        
        return list(set(proxies))[:50]  # Limiter à 50 proxies uniques
    
    @staticmethod
    def get_random_proxy():
        """Retourne un proxy aléatoire"""
        proxies = VPNService.get_free_vpn_proxies()
        if proxies:
            return random.choice(proxies)
        return None
    
    @staticmethod
    def make_request_with_vpn(url, max_retries=3):
        """Fait une requête via un proxy VPN"""
        for attempt in range(max_retries):
            proxy = VPNService.get_random_proxy()
            if proxy:
                proxies = {
                    'http': f'http://{proxy}',
                    'https': f'http://{proxy}'
                }
                try:
                    response = requests.get(url, proxies=proxies, timeout=30)
                    if response.status_code == 200:
                        return response
                except:
                    continue
        
        # Si tous les proxies échouent, faire une requête normale
        return requests.get(url)

@app.route('/')
def index():
    """Page d'accueil"""
    return render_template(
        'index.html',
        adsense_client_id=ADSENSE_CLIENT_ID
    )

@app.route('/api/chat', methods=['POST'])
def chat():
    """API pour ChatGPT"""
    try:
        data = request.json
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({'error': 'Message vide'}), 400
        
        # Utiliser l'API OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Vous êtes Ben bot un assistant IA utile."},
                {"role": "user", "content": user_message}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        ai_response = response.choices[0].message.content
        
        return jsonify({
            'response': ai_response,
            'tokens_used': response.usage.total_tokens
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/vpn-test', methods=['GET'])
def vpn_test():
    """Test du service VPN"""
    try:
        # URL pour tester l'IP
        test_url = 'https://api.ipify.org?format=json'
        
        # Essayer avec VPN d'abord
        response = VPNService.make_request_with_vpn(test_url)
        
        if response.status_code == 200:
            ip_data = response.json()
            return jsonify({
                'success': True,
                'ip': ip_data.get('ip'),
                'method': 'via VPN/proxy'
            })
        else:
            # Fallback à une requête normale
            response = requests.get(test_url)
            ip_data = response.json()
            return jsonify({
                'success': True,
                'ip': ip_data.get('ip'),
                'method': 'direct (sans VPN)'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/get-proxies', methods=['GET'])
def get_proxies():
    """Obtenir la liste des proxies disponibles"""
    try:
        proxies = VPNService.get_free_vpn_proxies()
        return jsonify({
            'success': True,
            'count': len(proxies),
            'proxies': proxies[:10]  # Retourner seulement 10 pour l'affichage
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health')
def health():
    """Endpoint de santé pour Vercel"""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)