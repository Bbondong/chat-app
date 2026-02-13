# ============================================
# APPLICATION FLASK - CHAT APP AVEC IA
# Déploiement sur Vercel
# GEMINI - DÉTECTION AUTOMATIQUE DES MODÈLES
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

# 🔥 API GEMINI - Utilise OPENAI_API_KEY ou GEMINI_API_KEY
GEMINI_API_KEY = os.environ.get('OPENAI_API_KEY') or os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    print("⚠️ ATTENTION: Aucune clé API Gemini trouvée!")
else:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        print("✅ Gemini configuré avec succès!")
    except Exception as e:
        print(f"❌ Erreur configuration Gemini: {str(e)}")

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
    """Service VPN avec proxies gratuits"""
    
    _proxies_cache = None
    _cache_timestamp = 0
    CACHE_DURATION = 1800  # 30 minutes
    
    @classmethod
    def get_free_vpn_proxies(cls, force_refresh=False):
        """Récupère une liste de proxies"""
        
        current_time = time.time()
        if (not force_refresh and 
            cls._proxies_cache is not None and 
            current_time - cls._cache_timestamp < cls.CACHE_DURATION):
            return cls._proxies_cache
        
        proxy_sources = [
            'https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all',
            'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
            'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt',
            'https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt'
        ]
        
        all_proxies = []
        
        for source in proxy_sources:
            try:
                response = requests.get(source, timeout=10)
                if response.status_code == 200:
                    text = response.text.strip()
                    
                    if '\r\n' in text:
                        proxies = text.split('\r\n')
                    elif '\n' in text:
                        proxies = text.split('\n')
                    else:
                        proxies = text.split()
                    
                    for proxy in proxies:
                        proxy = proxy.strip()
                        if ':' in proxy and len(proxy.split(':')) == 2:
                            parts = proxy.split(':')
                            if parts[0].count('.') == 3 and parts[1].isdigit():
                                all_proxies.append(proxy)
                                
            except Exception as e:
                if DEBUG_MODE:
                    print(f"⚠️ Source indisponible: {source[:30]}...")
                continue
        
        cls._proxies_cache = list(set(all_proxies))[:50]
        cls._cache_timestamp = current_time
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
        
        for proxy in proxies[:10]:
            if cls.test_proxy(proxy):
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
# SERVICE GEMINI - DÉTECTION AUTOMATIQUE
# ============================================

class GeminiService:
    """Service Gemini avec détection automatique des modèles"""
    
    _available_models = None
    _selected_model = None
    _last_check = 0
    CACHE_DURATION = 3600  # 1 heure
    
    @classmethod
    def get_available_models(cls, force_refresh=False):
        """Liste les modèles Gemini disponibles"""
        
        current_time = time.time()
        if (not force_refresh and 
            cls._available_models is not None and 
            current_time - cls._last_check < cls.CACHE_DURATION):
            return cls._available_models
        
        if not GEMINI_API_KEY:
            return []
        
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            models = []
            
            for model in genai.list_models():
                if 'generateContent' in model.supported_generation_methods:
                    models.append({
                        'name': model.name,
                        'display_name': model.display_name,
                        'methods': list(model.supported_generation_methods)
                    })
                    print(f"📋 Modèle trouvé: {model.name}")
            
            cls._available_models = models
            cls._last_check = current_time
            return models
            
        except Exception as e:
            print(f"❌ Erreur chargement modèles: {str(e)}")
            return []
    
    @classmethod
    def get_best_model(cls):
        """Sélectionne le meilleur modèle disponible"""
        
        models = cls.get_available_models()
        
        if not models:
            return None
        
        # Liste des modèles préférés par ordre de priorité
        preferred_names = [
            'models/gemini-1.5-pro',
            'models/gemini-1.5-flash',
            'models/gemini-1.0-pro',
            'models/gemini-pro',
            'gemini-1.5-pro',
            'gemini-1.5-flash',
            'gemini-1.0-pro',
            'gemini-pro'
        ]
        
        # Chercher d'abord les modèles préférés
        for preferred in preferred_names:
            for model in models:
                if model['name'] == preferred:
                    print(f"✅ Modèle sélectionné: {preferred}")
                    return preferred
        
        # Sinon prendre le premier modèle disponible
        if models:
            print(f"⚠️ Modèle par défaut: {models[0]['name']}")
            return models[0]['name']
        
        return None
    
    @classmethod
    def generate_response(cls, user_message, max_tokens=500, temperature=0.7):
        """Génère une réponse avec le meilleur modèle disponible"""
        
        if not GEMINI_API_KEY:
            return {
                'success': False,
                'error': 'Clé API manquante',
                'response': "Service IA non configuré."
            }
        
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            model_name = cls.get_best_model()
            
            if not model_name:
                return {
                    'success': False,
                    'error': 'Aucun modèle disponible',
                    'response': "Aucun modèle IA disponible."
                }
            
            model = genai.GenerativeModel(model_name)
            
            # Prompt optimisé pour BenBot
            prompt = f"""Tu es BenBot, un assistant IA amical et serviable.
            Réponds en français de manière concise, claire et utile.
            Message de l'utilisateur: {user_message}
            Réponse de BenBot:"""
            
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                    "top_p": 0.9,
                    "top_k": 40
                }
            )
            
            if response and response.text:
                return {
                    'success': True,
                    'response': response.text,
                    'model': model_name,
                    'tokens_used': len(response.text) // 4
                }
            else:
                return {
                    'success': False,
                    'error': 'Réponse vide',
                    'response': "Désolé, je n'ai pas pu générer une réponse."
                }
                
        except Exception as e:
            print(f"❌ Erreur Gemini: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'response': f"BenBot: Bonjour ! Je suis en ligne. Votre message a bien été reçu."
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
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time()
    })

# ============================================
# ROUTES GEMINI - OPTION 2 (DÉTECTION AUTOMATIQUE)
# ============================================

@app.route('/api/chat', methods=['POST'])
def chat():
    """API Gemini avec détection automatique des modèles"""
    
    data = request.json
    if not data:
        return jsonify({'error': 'Données JSON invalides'}), 400
    
    user_message = data.get('message', '').strip()
    if not user_message:
        return jsonify({'error': 'Message vide'}), 400
    
    # Paramètres optionnels
    max_tokens = min(int(data.get('max_tokens', 500)), 1000)
    temperature = float(data.get('temperature', 0.7))
    
    # Générer la réponse avec Gemini
    result = GeminiService.generate_response(
        user_message,
        max_tokens=max_tokens,
        temperature=temperature
    )
    
    return jsonify({
        'success': result['success'],
        'response': result['response'],
        'model': result.get('model', 'unknown'),
        'error': result.get('error'),
        'timestamp': time.time()
    })

@app.route('/api/gemini/models', methods=['GET'])
def list_gemini_models():
    """Liste tous les modèles Gemini disponibles"""
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'
    models = GeminiService.get_available_models(force_refresh=force_refresh)
    
    return jsonify({
        'success': True,
        'count': len(models),
        'models': models,
        'selected': GeminiService.get_best_model(),
        'timestamp': time.time()
    })

@app.route('/api/gemini/debug', methods=['GET'])
def debug_gemini():
    """Debug complet Gemini"""
    result = {
        'api_key_configured': bool(GEMINI_API_KEY),
        'api_key_prefix': GEMINI_API_KEY[:8] + '...' if GEMINI_API_KEY else None,
        'models': [],
        'selected_model': GeminiService.get_best_model(),
        'error': None
    }
    
    if not GEMINI_API_KEY:
        result['error'] = 'Clé API manquante'
        return jsonify(result)
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        
        for model in genai.list_models():
            model_info = {
                'name': model.name,
                'display_name': model.display_name,
                'supports_generate': 'generateContent' in model.supported_generation_methods,
                'methods': list(model.supported_generation_methods)
            }
            
            # Tester le modèle s'il supporte generateContent
            if model_info['supports_generate']:
                try:
                    test_model = genai.GenerativeModel(model.name)
                    test_response = test_model.generate_content(
                        "Dis 'OK' en un mot",
                        generation_config={"max_output_tokens": 10}
                    )
                    model_info['test'] = '✅ OK' if test_response.text else '⚠️ Vide'
                except Exception as e:
                    model_info['test'] = f'❌ {str(e)[:50]}'
            
            result['models'].append(model_info)
        
        result['count'] = len(result['models'])
        
    except Exception as e:
        result['error'] = str(e)
    
    return jsonify(result)

# ============================================
# ROUTES VPN
# ============================================

@app.route('/api/vpn/test', methods=['GET'])
def vpn_test():
    """Test VPN"""
    try:
        vpn_info = VPNService.get_ip_info(use_vpn=True)
        direct_info = VPNService.get_ip_info(use_vpn=False)
        proxies = VPNService.get_free_vpn_proxies()
        working_proxy = VPNService.get_working_proxy()
        
        return jsonify({
            'success': True,
            'vpn': {
                'ip': vpn_info.get('ip'),
                'proxy': vpn_info.get('proxy'),
                'status': 'connected' if vpn_info.get('success') else 'failed',
                'method': vpn_info.get('method')
            },
            'direct': {
                'ip': direct_info.get('ip'),
                'status': 'connected' if direct_info.get('success') else 'failed',
                'method': direct_info.get('method')
            },
            'proxies': {
                'total': len(proxies),
                'working': 1 if working_proxy else 0
            },
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
    """Liste des proxies"""
    try:
        force_refresh = request.args.get('refresh', 'false').lower() == 'true'
        proxies = VPNService.get_free_vpn_proxies(force_refresh=force_refresh)
        
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
    models = GeminiService.get_available_models()
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
                'models_available': len(models),
                'selected_model': GeminiService.get_best_model()
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
    return jsonify({'error': 'Erreur interne du serveur'}), 500

@app.errorhandler(429)
def rate_limit(error):
    return jsonify({'error': 'Trop de requêtes'}), 429

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

# Pour Vercel
application = app