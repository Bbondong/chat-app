# ============================================
# APPLICATION FLASK - CHAT APP AVEC IA
# Déploiement sur Vercel
# GEMINI - DÉTECTION AUTOMATIQUE DES MODÈLES
# MÉMOIRE 24H INTÉGRÉE
# ROUTES VPN COMPLÈTES (/api/vpn-test ET /api/get-proxies)
# ============================================

from flask import Flask, render_template, request, jsonify, session
import os
import requests
import json
import random
import time
from functools import wraps
import google.generativeai as genai
from datetime import datetime, timedelta
import hashlib

# ============================================
# CONFIGURATION - VARIABLES D'ENVIRONNEMENT
# ============================================

app = Flask(__name__)

# Clé secrète pour les sessions Flask
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("❌ ERREUR CRITIQUE: SECRET_KEY non définie dans Vercel!")
app.secret_key = SECRET_KEY

# Configuration de la session pour 24h
app.config['SECRET_KEY'] = SECRET_KEY
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)  # ⏰ 24 HEURES !
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_NAME'] = 'benbot_session'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # Mettre True en HTTPS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

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
print("🚀 APPLICATION DÉMARRÉE SUR VERCEL AVEC MÉMOIRE 24H")
print("="*50)
print(f"✅ SECRET_KEY: {'Configurée' if SECRET_KEY else 'MANQUANTE'}")
print(f"✅ GEMINI_API_KEY: {'Configurée' if GEMINI_API_KEY else 'MANQUANTE'}")
print(f"✅ ADSENSE_CLIENT_ID: {'Configuré' if ADSENSE_CLIENT_ID != 'ca-pub-XXXXXXXXXXXXXXXX' else 'Défaut'}")
print(f"✅ Mode: {'Développement' if DEBUG_MODE else 'Production'}")
print(f"✅ Mémoire: 24 heures active")
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
# SERVICE VPN
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
# SERVICE DE MÉMOIRE 24H
# ============================================

@app.before_request
def make_session_permanent():
    """Active la session permanente pour 24h"""
    session.permanent = True
    if 'last_activity' not in session:
        session['last_activity'] = time.time()

class MemoryService24h:
    """Service de mémoire avec expiration 24h"""
    
    @staticmethod
    def init_conversation():
        """Initialise une nouvelle conversation"""
        if 'conversation' not in session:
            session['conversation'] = {
                'id': hashlib.md5(str(time.time()).encode()).hexdigest()[:8],
                'created_at': time.time(),
                'expires_at': time.time() + 86400,  # 24h en secondes
                'messages': [],
                'user_info': {},
                'topics': [],
                'message_count': 0
            }
            session.modified = True
        return session['conversation']
    
    @staticmethod
    def is_expired():
        """Vérifie si la session a expiré (24h)"""
        if 'conversation' not in session:
            return True
        
        expires_at = session['conversation'].get('expires_at', 0)
        if time.time() > expires_at:
            session.pop('conversation', None)
            session.modified = True
            return True
        return False
    
    @staticmethod
    def add_message(role, content):
        """Ajoute un message à la conversation"""
        MemoryService24h.init_conversation()
        
        if MemoryService24h.is_expired():
            MemoryService24h.init_conversation()
        
        session['conversation']['messages'].append({
            'id': len(session['conversation']['messages']),
            'role': role,
            'content': content,
            'timestamp': time.time(),
            'time_str': datetime.now().strftime('%H:%M'),
            'date_str': datetime.now().strftime('%d/%m/%Y')
        })
        
        session['conversation']['message_count'] += 1
        
        # Garder seulement les 50 derniers messages
        if len(session['conversation']['messages']) > 50:
            session['conversation']['messages'] = session['conversation']['messages'][-50:]
        
        session.modified = True
        return session['conversation']
    
    @staticmethod
    def get_context(limit=10):
        """Récupère le contexte de conversation"""
        if MemoryService24h.is_expired():
            return []
        
        conversation = session.get('conversation', {})
        messages = conversation.get('messages', [])
        return messages[-limit:]
    
    @staticmethod
    def get_conversation_summary():
        """Résumé de la conversation"""
        if MemoryService24h.is_expired():
            return None
        
        conv = session.get('conversation', {})
        messages = conv.get('messages', [])
        
        if messages and len(messages) > 0:
            start_time = messages[0].get('timestamp', time.time())
            duration = time.time() - start_time
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
        else:
            hours, minutes = 0, 0
        
        return {
            'id': conv.get('id'),
            'message_count': len(messages),
            'duration': f"{hours}h{minutes}min",
            'created_at': datetime.fromtimestamp(conv.get('created_at', time.time())).strftime('%H:%M %d/%m/%Y'),
            'expires_at': datetime.fromtimestamp(conv.get('expires_at', time.time())).strftime('%H:%M %d/%m/%Y'),
            'time_remaining': int(conv.get('expires_at', 0) - time.time())
        }
    
    @staticmethod
    def remember_info(key, value):
        """Mémorise une information utilisateur"""
        if MemoryService24h.is_expired():
            MemoryService24h.init_conversation()
        
        if 'user_info' not in session['conversation']:
            session['conversation']['user_info'] = {}
        
        session['conversation']['user_info'][key] = {
            'value': value,
            'timestamp': time.time()
        }
        session.modified = True
    
    @staticmethod
    def get_user_info(key=None):
        """Récupère les informations utilisateur"""
        if MemoryService24h.is_expired():
            return None
        
        user_info = session.get('conversation', {}).get('user_info', {})
        if key:
            info = user_info.get(key, {})
            return info.get('value') if info else None
        return {k: v['value'] for k, v in user_info.items()}
    
    @staticmethod
    def add_topic(topic):
        """Ajoute un sujet de discussion"""
        if MemoryService24h.is_expired():
            MemoryService24h.init_conversation()
        
        if 'topics' not in session['conversation']:
            session['conversation']['topics'] = []
        
        if topic not in session['conversation']['topics']:
            session['conversation']['topics'].append(topic)
            if len(session['conversation']['topics']) > 10:
                session['conversation']['topics'] = session['conversation']['topics'][-10:]
        
        session.modified = True
    
    @staticmethod
    def clear():
        """Efface la conversation"""
        session.pop('conversation', None)
        session.modified = True

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
        
        for preferred in preferred_names:
            for model in models:
                if model['name'] == preferred:
                    print(f"✅ Modèle sélectionné: {preferred}")
                    return preferred
        
        if models:
            print(f"⚠️ Modèle par défaut: {models[0]['name']}")
            return models[0]['name']
        
        return None

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
        'memory': '24h active',
        'timestamp': time.time()
    })

# ============================================
# ROUTE CHAT AVEC MÉMOIRE 24H
# ============================================

@app.route('/api/chat', methods=['POST'])
def chat():
    """API Gemini avec mémoire 24h et détection automatique"""
    
    data = request.json
    if not data:
        return jsonify({'error': 'Données JSON invalides'}), 400
    
    user_message = data.get('message', '').strip()
    if not user_message:
        return jsonify({'error': 'Message vide'}), 400
    
    # 🔥 INITIALISER LA MÉMOIRE 24H
    MemoryService24h.init_conversation()
    
    if MemoryService24h.is_expired():
        MemoryService24h.init_conversation()
    
    # 🔥 AJOUTER LE MESSAGE UTILISATEUR
    MemoryService24h.add_message('user', user_message)
    
    # 🔥 DÉTECTION DU PRÉNOM
    if "je m'appelle" in user_message.lower() or "mon nom est" in user_message.lower() or "moi c'est" in user_message.lower():
        words = user_message.lower().split()
        for i, word in enumerate(words):
            if word in ["m'appelle", "nom", "c'est"] and i + 1 < len(words):
                name = words[i + 1].capitalize()
                MemoryService24h.remember_info('prenom', name)
                break
    
    # 🔥 DÉTECTION DES SUJETS
    topics_keywords = {
        'travail': ['travail', 'emploi', 'job', 'carrière', 'métier', 'profession'],
        'etude': ['étude', 'école', 'cours', 'apprendre', 'formation', 'université'],
        'technologie': ['ordinateur', 'programmation', 'code', 'python', 'logiciel', 'site web'],
        'sante': ['santé', 'médecin', 'malade', 'douleur', 'bien-être'],
        'voyage': ['voyage', 'vacances', 'pays', 'visiter', 'avion', 'hôtel']
    }
    
    for topic, keywords in topics_keywords.items():
        if any(keyword in user_message.lower() for keyword in keywords):
            MemoryService24h.add_topic(topic)
    
    # Paramètres optionnels
    max_tokens = min(int(data.get('max_tokens', 500)), 1000)
    temperature = float(data.get('temperature', 0.7))
    
    try:
        # 🔥 CONSTRUIRE LE CONTEXTE AVEC MÉMOIRE
        context_messages = MemoryService24h.get_context(8)
        user_info = MemoryService24h.get_user_info()
        topics = session.get('conversation', {}).get('topics', [])
        summary = MemoryService24h.get_conversation_summary()
        
        # Construire le prompt avec mémoire
        memory_context = ""
        
        if user_info and 'prenom' in user_info:
            memory_context += f"L'utilisateur s'appelle {user_info['prenom']}. "
        
        if topics:
            memory_context += f"Sujets discutés récemment: {', '.join(topics[-3:])}. "
        
        if summary and summary['time_remaining'] > 0:
            hours_left = summary['time_remaining'] // 3600
            if hours_left > 0:
                memory_context += f"Conversation active depuis {summary['duration']}. "
        
        conversation_history = ""
        for msg in context_messages:
            role = "Utilisateur" if msg['role'] == 'user' else "BenBot"
            conversation_history += f"{role}: {msg['content']}\n"
        
        # Prompt final
        prompt = f"""Tu es BenBot, un assistant IA amical et serviable.
Réponds en français de manière naturelle, chaleureuse et utile.

{memory_context}
Historique de la conversation:
{conversation_history}
BenBot:"""
        
        # Générer la réponse avec Gemini
        genai.configure(api_key=GEMINI_API_KEY)
        model_name = GeminiService.get_best_model()
        
        if not model_name:
            return jsonify({
                'success': True,
                'response': f"BenBot: {user_message}",
                'model': 'memory-only'
            }), 200
        
        model = genai.GenerativeModel(model_name)
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
            ai_response = response.text
            
            # 🔥 AJOUTER LA RÉPONSE À LA MÉMOIRE
            MemoryService24h.add_message('assistant', ai_response)
            
            return jsonify({
                'success': True,
                'response': ai_response,
                'model': model_name,
                'memory': {
                    'active': True,
                    'expires_in': '24h',
                    'time_remaining': summary['time_remaining'] if summary else 86400,
                    'message_count': session.get('conversation', {}).get('message_count', 0),
                    'user_name': user_info.get('prenom') if user_info else None
                },
                'timestamp': time.time()
            })
        else:
            MemoryService24h.add_message('assistant', f"BenBot: J'ai bien reçu ton message !")
            return jsonify({
                'success': True,
                'response': f"BenBot: J'ai bien reçu ton message !",
                'model': 'simple-response'
            }), 200
            
    except Exception as e:
        print(f"❌ Erreur Gemini: {str(e)}")
        
        MemoryService24h.add_message('assistant', f"BenBot: {user_message}")
        
        return jsonify({
            'success': True,
            'response': f"BenBot: {user_message}",
            'model': 'fallback',
            'timestamp': time.time()
        }), 200

# ============================================
# ROUTES VPN - VERSION COMPLÈTE AVEC TOUS LES ALIAS
# ============================================

@app.route('/api/vpn/test', methods=['GET'])
@app.route('/api/vpn-test', methods=['GET'])  # 🔥 AJOUTÉ POUR COMPATIBILITÉ FRONTEND
def vpn_test():
    """Test VPN - Supporte /api/vpn/test ET /api/vpn-test"""
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
@app.route('/api/get-proxies', methods=['GET'])  # 🔥 AJOUTÉ POUR COMPATIBILITÉ FRONTEND
def get_proxies():
    """Liste des proxies - Supporte /api/vpn/proxies ET /api/get-proxies"""
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
        print(f"❌ Erreur proxies: {str(e)}")
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500

# ============================================
# ROUTES DE MÉMOIRE
# ============================================

@app.route('/api/memory/status', methods=['GET'])
def memory_status():
    """Statut de la mémoire 24h"""
    if 'conversation' not in session:
        return jsonify({
            'success': True,
            'memory': 'inactive',
            'message': 'Aucune conversation active'
        })
    
    summary = MemoryService24h.get_conversation_summary()
    user_info = MemoryService24h.get_user_info()
    topics = session.get('conversation', {}).get('topics', [])
    
    return jsonify({
        'success': True,
        'memory': 'active',
        'expiration': '24h',
        'summary': summary,
        'user_info': user_info,
        'topics': topics,
        'recent_messages': MemoryService24h.get_context(4)
    })

@app.route('/api/memory/clear', methods=['POST'])
def memory_clear():
    """Efface la mémoire 24h"""
    MemoryService24h.clear()
    return jsonify({
        'success': True,
        'message': 'Mémoire effacée'
    })

@app.route('/api/memory/remember', methods=['POST'])
def memory_remember():
    """Mémorise une information personnalisée"""
    data = request.json
    key = data.get('key')
    value = data.get('value')
    
    if key and value:
        MemoryService24h.remember_info(key, value)
        return jsonify({
            'success': True,
            'message': f"J'ai mémorisé: {key} = {value}"
        })
    
    return jsonify({'error': 'Clé ou valeur manquante'}), 400

@app.route('/api/memory/time-left', methods=['GET'])
def memory_time_left():
    """Temps restant sur la mémoire 24h"""
    if 'conversation' not in session:
        return jsonify({
            'success': True,
            'active': False,
            'time_left': 0
        })
    
    expires_at = session['conversation'].get('expires_at', 0)
    time_left = max(0, int(expires_at - time.time()))
    
    hours = time_left // 3600
    minutes = (time_left % 3600) // 60
    seconds = time_left % 60
    
    return jsonify({
        'success': True,
        'active': True,
        'time_left_seconds': time_left,
        'time_left_formatted': f"{hours}h{minutes}min{seconds}s",
        'expires_at': datetime.fromtimestamp(expires_at).strftime('%H:%M %d/%m/%Y')
    })

# ============================================
# ROUTES GEMINI
# ============================================

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
            'environment': 'production' if not DEBUG_MODE else 'development',
            'memory': '24h active'
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
        'memory': {
            'active': 'conversation' in session,
            'expiration': '24h'
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