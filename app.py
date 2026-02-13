# ============================================
# APPLICATION FLASK - CHAT APP AVEC IA
# Déploiement sur Vercel
# Variables d'environnement depuis Vercel Dashboard
# ============================================

from flask import Flask, render_template, request, jsonify, session
import os
import requests
import json
import random
import time
from functools import wraps
import google.generativeai as genai  # 👈 REMPLACE openai

# ============================================
# CONFIGURATION - VARIABLES D'ENVIRONNEMENT
# ============================================

app = Flask(__name__)

# Clé secrète pour les sessions Flask
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("❌ ERREUR CRITIQUE: SECRET_KEY non définie dans Vercel!")
app.secret_key = SECRET_KEY

# 🔥 API GEMINI (même nom de variable que OPENAI_API_KEY pour compatibilité)
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')  # 👈 TU METS TA CLÉ GEMINI ICI !
if not OPENAI_API_KEY:
    raise ValueError("❌ ERREUR CRITIQUE: OPENAI_API_KEY non définie dans Vercel!")
genai.configure(api_key=OPENAI_API_KEY)  # 👈 Configuration Gemini avec la même clé

# Google AdSense
ADSENSE_CLIENT_ID = os.environ.get('ADSENSE_CLIENT_ID', 'ca-pub-XXXXXXXXXXXXXXXX')

# Mode debug
DEBUG_MODE = os.environ.get('FLASK_ENV', 'production') == 'development'

# ============================================
# LOGS DE DÉMARRAGE (visibles dans Vercel)
# ============================================

print("\n" + "="*50)
print("🚀 APPLICATION DÉMARRÉE SUR VERCEL AVEC GEMINI")
print("="*50)
print(f"✅ SECRET_KEY: {'Configurée' if SECRET_KEY else 'MANQUANTE'}")
print(f"✅ GEMINI_API_KEY: {'Configurée' if OPENAI_API_KEY else 'MANQUANTE'}")
print(f"✅ ADSENSE_CLIENT_ID: {'Configuré' if ADSENSE_CLIENT_ID != 'ca-pub-XXXXXXXXXXXXXXXX' else 'Défaut'}")
print(f"✅ Mode: {'Développement' if DEBUG_MODE else 'Production'}")
print("="*50 + "\n")

# ============================================
# DÉCORATEURS ET UTILITAIRES (ADAPTÉS POUR GEMINI)
# ============================================

def handle_errors(f):
    """Décorateur pour gérer les erreurs API"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            error_str = str(e).lower()
            
            # Gestion des erreurs Gemini
            if 'quota' in error_str or 'rate' in error_str or 'limit' in error_str:
                return jsonify({'error': 'Limite de requêtes dépassée. Réessayez dans quelques instants.'}), 429
            elif 'api key' in error_str or 'authentication' in error_str:
                return jsonify({'error': 'Erreur d\'authentification API. Vérifiez votre clé.'}), 401
            elif 'not found' in error_str or 'model' in error_str:
                return jsonify({'error': f'Modèle non disponible: {str(e)}'}), 400
            elif 'timeout' in error_str:
                return jsonify({'error': 'Délai d\'attente dépassé'}), 503
            else:
                print(f"❌ Erreur non gérée: {str(e)}")
                return jsonify({'error': 'Erreur interne du serveur'}), 500
    return decorated_function

# ============================================
# SERVICE VPN (INCHANGÉ)
# ============================================

class VPNService:
    """Service VPN avec proxies gratuits"""
    
    # Cache des proxies (1 heure)
    _proxies_cache = None
    _cache_timestamp = 0
    CACHE_DURATION = 3600
    
    @classmethod
    def get_free_vpn_proxies(cls, force_refresh=False):
        """Récupère une liste de proxies avec cache"""
        
        current_time = time.time()
        if (not force_refresh and 
            cls._proxies_cache is not None and 
            current_time - cls._cache_timestamp < cls.CACHE_DURATION):
            return cls._proxies_cache
        
        proxy_sources = [
            'https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all',
            'https://www.proxy-list.download/api/v1/get?type=http',
            'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
            'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt'
        ]
        
        all_proxies = []
        
        for source in proxy_sources:
            try:
                response = requests.get(source, timeout=5)
                if response.status_code == 200:
                    if '\r\n' in response.text:
                        proxies = response.text.strip().split('\r\n')
                    elif '\n' in response.text:
                        proxies = response.text.strip().split('\n')
                    else:
                        proxies = response.text.strip().split()
                    
                    for proxy in proxies:
                        proxy = proxy.strip()
                        if ':' in proxy and len(proxy.split(':')) == 2:
                            all_proxies.append(proxy)
                            
            except Exception as e:
                if DEBUG_MODE:
                    print(f"⚠️ Source de proxy indisponible: {source[:50]}...")
                continue
        
        cls._proxies_cache = list(set(all_proxies))[:100]
        cls._cache_timestamp = current_time
        
        if DEBUG_MODE:
            print(f"✅ {len(cls._proxies_cache)} proxies chargés")
        
        return cls._proxies_cache
    
    @classmethod
    def get_random_proxy(cls):
        """Retourne un proxy aléatoire"""
        proxies = cls.get_free_vpn_proxies()
        if proxies:
            return random.choice(proxies)
        return None
    
    @classmethod
    def make_request_with_vpn(cls, url, max_retries=2):
        """Fait une requête via un proxy"""
        
        for attempt in range(max_retries):
            proxy = cls.get_random_proxy()
            if proxy:
                try:
                    proxies = {
                        'http': f'http://{proxy}',
                        'https': f'http://{proxy}'
                    }
                    response = requests.get(
                        url, 
                        proxies=proxies, 
                        timeout=5,
                        headers={'User-Agent': 'Mozilla/5.0'}
                    )
                    if response.status_code == 200:
                        return response
                except:
                    continue
        
        return requests.get(
            url,
            timeout=5,
            headers={'User-Agent': 'Mozilla/5.0'}
        )

# ============================================
# ROUTES PRINCIPALES
# ============================================

@app.route('/')
def index():
    """Page d'accueil"""
    return render_template(
        'index.html',
        adsense_client_id=ADSENSE_CLIENT_ID
    )

@app.route('/health')
def health():
    """Health check pour Vercel"""
    return jsonify({
        'status': 'healthy',
        'environment': 'production' if not DEBUG_MODE else 'development',
        'timestamp': time.time()
    })

@app.route('/api/chat', methods=['POST'])
@handle_errors
def chat():
    """API ChatGPT - MAIS AVEC GEMINI !"""
    
    # Récupérer et valider le message
    data = request.json
    if not data:
        return jsonify({'error': 'Données JSON invalides'}), 400
    
    user_message = data.get('message', '').strip()
    if not user_message:
        return jsonify({'error': 'Message vide'}), 400
    
    # Options supplémentaires (adaptées pour Gemini)
    model = data.get('model', 'gemini-1.5-flash')  # 👈 Modèle Gemini gratuit
    temperature = float(data.get('temperature', 0.7))
    max_tokens = min(int(data.get('max_tokens', 500)), 1000)
    
    try:
        # 🔥 CRÉER LE MODÈLE GEMINI
        model_instance = genai.GenerativeModel(
            model_name=model,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
                "top_p": 0.9,
                "top_k": 40
            }
        )
        
        # 🔥 CONSTRUIRE LE PROMPT AVEC SYSTEM PROMPT
        chat_session = model_instance.start_chat(history=[])
        
        # Ajouter le contexte système
        system_prompt = "Tu es BenBot, un assistant IA amical et serviable. Réponds en français de manière concise et utile."
        full_prompt = f"{system_prompt}\n\nUtilisateur: {user_message}\nBenBot:"
        
        # 🔥 APPEL À GEMINI
        response = model_instance.generate_content(full_prompt)
        
        # 🔥 EXTRAIRE LA RÉPONSE
        if response.text:
            ai_response = response.text
        else:
            ai_response = "Désolé, je n'ai pas pu générer une réponse."
        
        # Journalisation
        if DEBUG_MODE:
            print(f"💬 Message: {user_message[:50]}...")
            print(f"🤖 Réponse: {ai_response[:50]}...")
        
        return jsonify({
            'success': True,
            'response': ai_response,
            'model': model,
            'tokens_used': len(ai_response) // 4,  # Approximation
            'timestamp': time.time()
        })
        
    except Exception as e:
        print(f"❌ Erreur Gemini: {str(e)}")
        
        # FALLBACK: Si Gemini plante, on utilise un modèle plus simple
        try:
            fallback_model = genai.GenerativeModel('gemini-1.0-pro')
            fallback_response = fallback_model.generate_content(user_message[:100])
            
            return jsonify({
                'success': True,
                'response': fallback_response.text,
                'model': 'gemini-1.0-pro (fallback)',
                'tokens_used': len(fallback_response.text) // 4,
                'timestamp': time.time()
            })
        except:
            # DERNIER FALLBACK: réponse simple
            return jsonify({
                'success': True,
                'response': f"Message reçu: '{user_message[:50]}...' (Mode hors-ligne)",
                'model': 'offline-fallback',
                'tokens_used': 0,
                'timestamp': time.time()
            })

@app.route('/api/chat/stream', methods=['POST'])
@handle_errors
def chat_stream():
    """Version streaming (adaptée pour Gemini)"""
    data = request.json
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return jsonify({'error': 'Message vide'}), 400
    
    def generate():
        try:
            model_instance = genai.GenerativeModel('gemini-1.5-flash')
            
            system_prompt = "Tu es BenBot, un assistant IA amical et serviable."
            full_prompt = f"{system_prompt}\n\nUtilisateur: {user_message}\nBenBot:"
            
            # Génération en streaming
            response = model_instance.generate_content(
                full_prompt,
                stream=True
            )
            
            for chunk in response:
                if chunk.text:
                    yield f"data: {json.dumps({'chunk': chunk.text})}\n\n"
                    time.sleep(0.01)  # Petit délai pour l'effet streaming
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return app.response_class(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )

# ============================================
# VPN ET AUTRES ROUTES (INCHANGÉES)
# ============================================

@app.route('/api/vpn/test', methods=['GET'])
def vpn_test():
    """Test complet du service VPN"""
    try:
        start_time = time.time()
        vpn_response = VPNService.make_request_with_vpn('https://api.ipify.org?format=json')
        vpn_time = time.time() - start_time
        
        if vpn_response.status_code == 200:
            vpn_ip = vpn_response.json().get('ip')
        else:
            vpn_ip = None
        
        start_time = time.time()
        direct_response = requests.get('https://api.ipify.org?format=json', timeout=5)
        direct_time = time.time() - start_time
        
        direct_ip = direct_response.json().get('ip')
        
        return jsonify({
            'success': True,
            'vpn': {
                'ip': vpn_ip,
                'latency': round(vpn_time * 1000, 2),
                'status': 'connected' if vpn_ip else 'failed'
            },
            'direct': {
                'ip': direct_ip,
                'latency': round(direct_time * 1000, 2),
                'status': 'connected'
            },
            'proxies_available': len(VPNService.get_free_vpn_proxies()),
            'timestamp': time.time()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': time.time()
        }), 500

@app.route('/api/vpn/proxies', methods=['GET'])
def get_proxies():
    """Liste des proxies disponibles"""
    try:
        force_refresh = request.args.get('refresh', 'false').lower() == 'true'
        proxies = VPNService.get_free_vpn_proxies(force_refresh=force_refresh)
        
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 50)
        start = (page - 1) * per_page
        end = start + per_page
        
        return jsonify({
            'success': True,
            'total': len(proxies),
            'page': page,
            'per_page': per_page,
            'proxies': proxies[start:end],
            'cached': not force_refresh and VPNService._proxies_cache is not None,
            'timestamp': time.time()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/system/status', methods=['GET'])
def system_status():
    """Statut complet du système"""
    return jsonify({
        'application': {
            'name': 'Chat App IA',
            'version': '1.0.0',
            'environment': 'production' if not DEBUG_MODE else 'development',
            'python_version': os.sys.version
        },
        'apis': {
            'gemini': {  # 👈 Changé de openai à gemini
                'configured': bool(OPENAI_API_KEY),
                'model': 'gemini-1.5-flash'
            },
            'adsense': {
                'configured': ADSENSE_CLIENT_ID != 'ca-pub-XXXXXXXXXXXXXXXX'
            }
        },
        'vpn': {
            'proxies_available': len(VPNService.get_free_vpn_proxies()),
            'cache_age': time.time() - VPNService._cache_timestamp if VPNService._cache_timestamp else 0
        },
        'timestamp': time.time()
    })

# ============================================
# GESTIONNAIRES D'ERREURS
# ============================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Route non trouvée',
        'status_code': 404
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Erreur interne du serveur',
        'status_code': 500
    }), 500

@app.errorhandler(429)
def rate_limit(error):
    return jsonify({
        'error': 'Trop de requêtes',
        'status_code': 429
    }), 429

# ============================================
# DÉMARRAGE DE L'APPLICATION
# ============================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=DEBUG_MODE,
        threaded=True
    )

# Pour Vercel - Point d'entrée
application = app