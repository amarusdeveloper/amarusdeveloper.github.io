import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from supabase import create_client, Client
from functools import wraps
from datetime import datetime

load_dotenv()
app = Flask(__name__)
CORS(app)



SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
ADMIN_USER = os.environ.get('ADMIN_USER')
ADMIN_PASS = os.environ.get('ADMIN_PASS')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError('SUPABASE_URL e SUPABASE_KEY precisam estar definidos no .env')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def classificar_lead(orcamento):
    if orcamento == 'Até R$800':
        return 'fraco'
    elif orcamento == 'R$800–1500':
        return 'medio'
    elif orcamento == 'R$1500+':
        return 'forte'
    return 'indefinido'

def check_auth(username, password):
    return username == ADMIN_USER and password == ADMIN_PASS

def authenticate():
    return Response('Acesso restrito', 401, {'WWW-Authenticate': 'Basic realm="Login"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route('/lead', methods=['POST'])
def receber_lead():
    if not request.is_json:
        return jsonify({'success': False, 'error': 'Envie os dados como JSON (Content-Type: application/json)'}), 400
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'success': False, 'error': 'JSON inválido ou não enviado'}), 400
    required = ['tipo', 'objetivo', 'orcamento', 'prazo', 'mensagem', 'email']
    for field in required:
        if field not in data or not data[field]:
            return jsonify({'success': False, 'error': f'Campo obrigatório faltando: {field}'}), 400
    classificacao = classificar_lead(data['orcamento'])
    lead = {
        'tipo': data['tipo'],
        'objetivo': data['objetivo'],
        'orcamento': data['orcamento'],
        'prazo': data['prazo'],
        'mensagem': data['mensagem'],
        'email': data['email'],
        'classificacao': classificacao,
        'data': datetime.utcnow().isoformat()
    }
    try:
        supabase.table('leads').insert(lead).execute()
        return jsonify({'success': True, 'classificacao': classificacao})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/leads', methods=['GET'])
@requires_auth
def listar_leads():
    try:
        res = supabase.table('leads').select('*').order('data', desc=True).execute()
        return jsonify(res.data)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
