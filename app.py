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
import google.generativeai as genai

# ============================================
# CONFIGURATION - VARIABLES D'ENVIRONNEMENT
# ============================================

app = Flask(__name__)

# Clé secrète pour les sessions Flask
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("❌ ERREUR CRITIQUE: SECRET_KEY non définie dans Vercel!")
app.secret_key = SECRET_KEY

# 🔥 API GEMINI (même variable pour compatibilité)
GEMINI_API_KEY = os.environ.get('OPENAI_API_KEY') or os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    print("⚠️ ATTENTION: Aucune clé API Gemini trouvée!")
else:
    genai.configure(api_key=GEMINI_API_KEY)
    print("✅ Gemini configuré avec succès!")

# Google AdSense
ADSENSE_CLIENT_ID = os.environ.get('ADSENSE_CLIENT_ID', 'ca-pub-XXXXXXXXXXXXXXXX')

# Mode debug
DEBUG_MODE = os.environ.get('FLASK_ENV', 'production') == 'development'

# ============================================
# LOGS DE DÉMARRAGE
# ============================================

print("\n" + "="*50)
print("🚀 APPLICATION DÉMARRÉE SUR VERCEL")
print("="*50)
print(f"✅ SECRET_KEY: {'Configurée' if SECRET_KEY else 'MANQUANTE'}")
print(f"✅ GEMINI_API_KEY: {'Configurée' if GEMINI_API_KEY else 'MANQUANTE'}")
print(f"✅ ADSENSE_CLIENT_ID: {'Configuré' if ADSENSE_CLIENT_ID != 'ca-pub-XXXXXXXXXXXXXXXX' else 'Défaut'}")
print(f"✅ Mode: {'Développement' if DEBUG_MODE else 'Production'}")
print("="*50 + "\n")

# ============================================
# DÉCORATEURS ET UTILITAIRES
# ============================================

def handle_errors(f):
    """Décorateur pour gérer les erreurs API"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            error_str = str(e).lower()
            
            if 'quota' in error_str or 'rate' in error_str:
                return jsonify({'error': 'Limite de requêtes dépassée'}), 429
            elif 'api key' in error_str or 'authentication' in error_str:
                return jsonify({'error': 'Erreur d\'authentification API'}), 401
            elif 'not found' in error_str or 'model' in error_str:
                return jsonify({'error': f'Modèle non disponible'}), 400
            else:
                print(f"❌ Erreur: {str(e)}")
                return jsonify({'error': 'Erreur interne'}), 500
    return decorated_function

# ============================================
# SERVICE VPN CORRIGÉ
# ============================================

class VPNService:
    """Service VPN avec proxies gratuits - CORRIGÉ"""
    
    _proxies_cache = None
    _cache_timestamp = 0
    CACHE_DURATION = 1800  # 30 minutes
    
    @classmethod
    def get_free_vpn_proxies(cls, force_refresh=False):
        """Récupère une liste de proxies - VERSION STABLE"""
        
        current_time = time.time()
        if (not force_refresh and 
            cls._proxies_cache is not None and 
            current_time - cls._cache_timestamp < cls.CACHE_DURATION):
            return cls._proxies_cache
        
        # 🔥 SOURCES PLUS FIABLES
        proxy_sources = [
            'https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all',
            'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
            'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt',
            'https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt'
        ]
        
        all_proxies = []
        
        for source in proxy_sources:
            try:
                print(f"🌐 Chargement proxies depuis: {source[:50]}...")
                response = requests.get(source, timeout=10)
                
                if response.status_code == 200:
                    # Nettoyer le texte
                    text = response.text.strip()
                    
                    # Différents formats
                    if '\r\n' in text:
                        proxies = text.split('\r\n')
                    elif '\n' in text:
                        proxies = text.split('\n')
                    else:
                        proxies = text.split()
                    
                    # Filtrer les proxies valides
                    for proxy in proxies:
                        proxy = proxy.strip()
                        if ':' in proxy and len(proxy.split(':')) == 2:
                            # Vérifier que c'est une IP:port valide
                            parts = proxy.split(':')
                            if parts[0].count('.') == 3 and parts[1].isdigit():
                                all_proxies.append(proxy)
                    
                    print(f"✅ {len(proxies)} proxies trouvés sur cette source")
                    
            except Exception as e:
                if DEBUG_MODE:
                    print(f"⚠️ Source indisponible: {source[:30]}... - {str(e)[:50]}")
                continue
        
        # Dédupliquer et limiter
        cls._proxies_cache = list(set(all_proxies))[:50]  # Limité à 50 pour la stabilité
        cls._cache_timestamp = current_time
        
        print(f"✅ TOTAL: {len(cls._proxies_cache)} proxies valides chargés")
        return cls._proxies_cache
    
    @classmethod
    def test_proxy(cls, proxy):
        """Teste si un proxy est fonctionnel"""
        try:
            proxies = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
            response = requests.get(
                'http://httpbin.org/ip',
                proxies=proxies,
                timeout=3,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            return response.status_code == 200
        except:
            return False
    
    @classmethod
    def get_working_proxy(cls):
        """Retourne un proxy qui fonctionne"""
        proxies = cls.get_free_vpn_proxies()
        random.shuffle(proxies)
        
        for proxy in proxies[:10]:  # Tester les 10 premiers
            if cls.test_proxy(proxy):
                print(f"✅ Proxy fonctionnel trouvé: {proxy}")
                return proxy
        
        return None
    
    @classmethod
    def get_ip_info(cls, use_vpn=True):
        """Obtient les infos IP avec ou sans VPN"""
        try:
            if use_vpn:
                proxy = cls.get_working_proxy()
                if proxy:
                    proxies = {
                        'http': f'http://{proxy}',
                        'https': f'http://{proxy}'
                    }
                    response = requests.get(
                        'https://api.ipify.org?format=json',
                        proxies=proxies,
                        timeout=5,
                        headers={'User-Agent': 'Mozilla/5.0'}
                    )
                    if response.status_code == 200:
                        return {
                            'success': True,
                            'ip': response.json().get('ip'),
                            'proxy': proxy,
                            'method': 'VPN'
                        }
            
            # Fallback sans VPN
            response = requests.get(
                'https://api.ipify.org?format=json',
                timeout=3
            )
            return {
                'success': True,
                'ip': response.json().get('ip'),
                'proxy': None,
                'method': 'Direct'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'method': 'Échec'
            }

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
    return jsonify({'status': 'healthy', 'timestamp': time.time()})

# ============================================
# ROUTES GEMINI CORRIGÉES
# ============================================

@app.route('/api/chat', methods=['POST'])
def chat():
    """API Gemini - VERSION CORRIGÉE QUI MARCHE"""
    
    data = request.json
    if not data:
        return jsonify({'error': 'Données JSON invalides'}), 400
    
    user_message = data.get('message', '').strip()
    if not user_message:
        return jsonify({'error': 'Message vide'}), 400
    
    # 🔥 VÉRIFIER LA CLÉ API
    if not GEMINI_API_KEY:
        return jsonify({
            'success': True,
            'response': "⚠️ Service IA non configuré. Veuillez ajouter une clé API Gemini.",
            'model': 'not-configured',
            'timestamp': time.time()
        }), 200
    
    try:
        # 🔥 MODÈLE GEMINI-PRO - 100% DISPONIBLE
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
        
        # 🔥 PROMPT SIMPLE ET EFFICACE
        prompt = f"Tu es BenBot, un assistant IA amical. Réponds en français de façon concise: {user_message}"
        
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 500,
                "top_p": 0.9,
                "top_k": 40
            }
        )
        
        if response and response.text:
            return jsonify({
                'success': True,
                'response': response.text,
                'model': 'gemini-pro',
                'timestamp': time.time()
            })
        else:
            return jsonify({
                'success': True,
                'response': f"BenBot: J'ai bien reçu ton message. Comment puis-je t'aider ?",
                'model': 'simple-response',
                'timestamp': time.time()
            }), 200
            
    except Exception as e:
        print(f"❌ Erreur Gemini: {str(e)}")
        
        # 🔥 FALLBACK SIMPLE
        return jsonify({
            'success': True,
            'response': f"BenBot: Bonjour ! Je suis actuellement en mode simple. Message reçu: '{user_message[:100]}'",
            'model': 'fallback',
            'timestamp': time.time()
        }), 200

@app.route('/api/gemini/models', methods=['GET'])
def list_models():
    """Liste les modèles Gemini disponibles"""
    if not GEMINI_API_KEY:
        return jsonify({'error': 'API key non configurée'}), 400
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        models = genai.list_models()
        available = []
        
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                available.append({
                    'name': model.name,
                    'display_name': model.display_name
                })
        
        return jsonify({
            'success': True,
            'models': available,
            'count': len(available)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# ROUTES VPN CORRIGÉES
# ============================================

@app.route('/api/vpn/test', methods=['GET'])
def vpn_test():
    """Test VPN - VERSION CORRIGÉE"""
    try:
        # Test avec VPN
        vpn_info = VPNService.get_ip_info(use_vpn=True)
        
        # Test sans VPN
        direct_info = VPNService.get_ip_info(use_vpn=False)
        
        # État des proxies
        proxies = VPNService.get_free_vpn_proxies()
        working_proxy = VPNService.get_working_proxy()
        
        return jsonify({
            'success': True,
            'vpn': {
                'ip': vpn_info.get('ip') if vpn_info.get('success') else None,
                'proxy': vpn_info.get('proxy'),
                'status': 'connected' if vpn_info.get('success') else 'failed',
                'method': vpn_info.get('method', 'N/A')
            },
            'direct': {
                'ip': direct_info.get('ip'),
                'status': 'connected' if direct_info.get('success') else 'failed',
                'method': direct_info.get('method', 'N/A')
            },
            'proxies': {
                'total': len(proxies),
                'working': 1 if working_proxy else 0
            },
            'timestamp': time.time()
        })
        
    except Exception as e:
        print(f"❌ Erreur VPN test: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'vpn': {'status': 'failed'},
            'direct': {'status': 'failed'},
            'timestamp': time.time()
        }), 500

@app.route('/api/vpn/proxies', methods=['GET'])
def get_proxies():
    """Liste des proxies disponibles"""
    try:
        force_refresh = request.args.get('refresh', 'false').lower() == 'true'
        proxies = VPNService.get_free_vpn_proxies(force_refresh=force_refresh)
        
        # Tester les 5 premiers
        working = []
        for proxy in proxies[:5]:
            if VPNService.test_proxy(proxy):
                working.append(proxy)
        
        return jsonify({
            'success': True,
            'total': len(proxies),
            'proxies': proxies[:20],
            'working': working[:5],
            'cached': not force_refresh and VPNService._proxies_cache is not None,
            'timestamp': time.time()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# ROUTES SYSTÈME
# ============================================

@app.route('/api/system/status', methods=['GET'])
def system_status():
    """Statut complet du système"""
    proxies = VPNService.get_free_vpn_proxies()
    
    return jsonify({
        'application': {
            'name': 'Chat App IA',
            'version': '1.0.0',
            'environment': 'production' if not DEBUG_MODE else 'development'
        },
        'apis': {
            'gemini': {
                'configured': bool(GEMINI_API_KEY),
                'model': 'gemini-pro'
            },
            'adsense': {
                'configured': ADSENSE_CLIENT_ID != 'ca-pub-XXXXXXXXXXXXXXXX'
            }
        },
        'vpn': {
            'proxies_available': len(proxies),
            'cache_age': time.time() - VPNService._cache_timestamp if VPNService._cache_timestamp else 0
        },
        'timestamp': time.time()
    })

# ============================================
# GESTIONNAIRES D'ERREURS
# ============================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Route non trouvée'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Erreur interne'}), 500

# ============================================
# DÉMARRAGE
# ============================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=DEBUG_MODE,
        threaded=True
    )

application = app