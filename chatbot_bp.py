from flask import Blueprint, request, jsonify
import urllib.request
import urllib.error
import json

chatbot_bp = Blueprint('chatbot', __name__)

GROK_API_URL = 'https://api.groq.com/openai/v1/chat/completions'
GROK_MODEL   = 'llama-3.1-8b-instant'

SYSTEM_PROMPT = (
    "You are a medicine discount-list editor. "
    "Items format: name|disc%. "
    "For analysis: answer in plain text. "
    "For bulk changes: return ONLY the updated list in name|disc% format, one item per line."
)

@chatbot_bp.route('/chatbot/grok', methods=['POST'])
def grok_chat():
    data    = request.get_json(force=True) or {}
    api_key = (data.get('apiKey') or '').strip()
    if not api_key:
        return jsonify({'error': 'API key missing'}), 400

    # If frontend already built the full payload (vision or text), use it directly
    raw_payload = data.get('rawPayload')
    if raw_payload and isinstance(raw_payload, dict):
        payload = raw_payload
    else:
        # Build minimal payload from items + command
        command = (data.get('command') or '').strip()
        items   = data.get('items', [])
        if not command:
            return jsonify({'error': 'Command missing'}), 400
        compact  = '\n'.join(f"{it['name']}|{it['disc']}%" for it in items if it.get('name'))
        user_msg = (f"Current list:\n{compact}\n\n" if compact else '') + f"Command: {command}"
        payload  = {
            'model': GROK_MODEL,
            'messages': [
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user',   'content': user_msg},
            ],
            'max_tokens': 1200,
            'temperature': 0.1,
        }

    req = urllib.request.Request(
        GROK_API_URL,
        data=json.dumps(payload).encode(),
        headers={
            'Content-Type':  'application/json',
            'Authorization': f'Bearer {api_key}',
            'User-Agent':    'Mozilla/5.0',
        },
        method='POST',
    )

    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            body  = json.loads(resp.read())
            reply = body['choices'][0]['message']['content']
            return jsonify({'reply': reply})
    except urllib.error.HTTPError as e:
        err_body = e.read().decode(errors='ignore')
        if e.code == 429:
            return jsonify({'error': 'rate limit — wait a moment and retry'}), 429
        if e.code in (401, 403):
            # Extract Groq's own error message for clearer diagnosis
            try:
                detail = json.loads(err_body).get('error', {})
                msg = detail.get('message', err_body[:200]) if isinstance(detail, dict) else str(detail)[:200]
            except Exception:
                msg = err_body[:200]
            return jsonify({'error': f'401: {msg}', 'code': e.code}), 401
        return jsonify({'error': f'Groq API {e.code}: {err_body[:300]}'}), 502
    except Exception as e:
        return jsonify({'error': str(e)}), 500
