#!/usr/bin/env python3

import os
import subprocess
import hmac
import hashlib
import json
import logging
from flask import Flask, request, jsonify

app = Flask(__name__)

# 設定
API_SECRET = os.environ.get('CERT_API_SECRET', 'change-this-secret-in-production')
SCRIPTS_PATH = '/scripts'

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_signature(data, signature):
    """Verify HMAC signature"""
    if not signature:
        return False
    expected = hmac.new(API_SECRET.encode(), data.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(f'sha256={expected}', signature)

def validate_input(data):
    """入力値検証"""
    if not isinstance(data, dict):
        return False, "Invalid JSON format"
    
    username = data.get('username', '').strip()
    device_name = data.get('device_name', '').strip()
    
    if not username or not device_name:
        return False, "username and device_name are required"
    
    # セキュリティ: 危険な文字をチェック
    dangerous_chars = ['..', '/', '\\', ';', '&', '|', '$', '`']
    for char in dangerous_chars:
        if char in username or char in device_name:
            return False, f"Invalid character '{char}' in username or device_name"
    
    # 長さ制限
    if len(username) > 50 or len(device_name) > 50:
        return False, "username and device_name must be 50 characters or less"
    
    return True, None

@app.route('/health', methods=['GET'])
def health_check():
    """ヘルスチェック"""
    return jsonify({'status': 'healthy', 'service': 'cert-api'}), 200

@app.route('/generate-cert', methods=['POST'])
def generate_cert():
    """Certificate generation API"""
    try:
        # Check Content-Type
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400

        # Verify signature
        signature = request.headers.get('X-Signature')
        request_body = request.get_data(as_text=True)

        if not verify_signature(request_body, signature):
            logger.warning(f"Invalid signature from {request.remote_addr}")
            return jsonify({'error': 'Authentication failed'}), 403

        # Validate input
        data = request.get_json()
        valid, error_msg = validate_input(data)
        if not valid:
            logger.warning(f"Invalid input: {error_msg}")
            return jsonify({'error': error_msg}), 400

        username = data['username']
        device_name = data['device_name']
        cert_serial = f"{username}-{device_name}"

        logger.info(f"Certificate generation request: {cert_serial}")

        # Execute script
        script_path = os.path.join(SCRIPTS_PATH, 'generate-client-cert.sh')
        if not os.path.exists(script_path):
            logger.error(f"Script not found: {script_path}")
            return jsonify({'error': 'Certificate generation script not found'}), 500

        # Call shell script
        result = subprocess.run(
            [script_path, username, device_name],
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout
            cwd='/etc/openvpn'  # Explicitly set working directory
        )
        
        if result.returncode == 0:
            logger.info(f"Certificate generated successfully: {cert_serial}")
            return jsonify({
                'status': 'success',
                'cert_serial': cert_serial,
                'message': 'Certificate generated successfully'
            }), 200
        else:
            logger.error(f"Certificate generation failed: {result.stderr}")
            return jsonify({
                'error': 'Certificate generation failed',
                'details': result.stderr.strip() if result.stderr else 'Unknown error'
            }), 500
            
    except subprocess.TimeoutExpired:
        logger.error("Certificate generation timeout")
        return jsonify({'error': 'Certificate generation timeout'}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/revoke-cert', methods=['POST'])
def revoke_cert():
    """Certificate revocation API"""
    try:
        # Check Content-Type
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400

        # Verify signature
        signature = request.headers.get('X-Signature')
        request_body = request.get_data(as_text=True)

        if not verify_signature(request_body, signature):
            logger.warning(f"Invalid signature from {request.remote_addr}")
            return jsonify({'error': 'Authentication failed'}), 403

        # Validate input
        data = request.get_json()
        cert_serial = data.get('cert_serial', '').strip()

        if not cert_serial:
            return jsonify({'error': 'cert_serial is required'}), 400

        # Security: Check for dangerous characters
        dangerous_chars = ['..', '/', '\\', ';', '&', '|', '$', '`']
        for char in dangerous_chars:
            if char in cert_serial:
                return jsonify({'error': f'Invalid character "{char}" in cert_serial'}), 400
        
        # 長さ制限
        if len(cert_serial) > 100:
            return jsonify({'error': 'cert_serial must be 100 characters or less'}), 400
        
        logger.info(f"Certificate revocation request: {cert_serial}")
        
        # 無効化スクリプトファイルの存在チェック
        script_path = os.path.join(SCRIPTS_PATH, 'revoke-client-cert.sh')
        if not os.path.exists(script_path):
            logger.error(f"Revocation script not found: {script_path}")
            return jsonify({'error': 'Certificate revocation script not found'}), 500
        
        # 証明書無効化スクリプト実行
        result = subprocess.run(
            [script_path, cert_serial],
            capture_output=True,
            text=True,
            timeout=120,  # 2分タイムアウト
            cwd='/etc/openvpn'  # 作業ディレクトリを明示
        )
        
        if result.returncode == 0:
            logger.info(f"Certificate revoked successfully: {cert_serial}")
            return jsonify({
                'status': 'success',
                'cert_serial': cert_serial,
                'message': 'Certificate revoked successfully'
            }), 200
        else:
            logger.error(f"Certificate revocation failed: {result.stderr}")
            return jsonify({
                'error': 'Certificate revocation failed',
                'details': result.stderr.strip() if result.stderr else 'Unknown error'
            }), 500
            
    except subprocess.TimeoutExpired:
        logger.error("Certificate revocation timeout")
        return jsonify({'error': 'Certificate revocation timeout'}), 500
    except Exception as e:
        logger.error(f"Revocation error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Set debug mode only in development environment
    debug_mode = os.environ.get('FLASK_ENV') == 'development'

    # Start API server
    logger.info("Starting Certificate API server...")
    bind_ip = os.environ.get('CERT_API_BIND_IP', '127.0.0.1')
    port = int(os.environ.get('CERT_API_INTERNAL_PORT', 8080))
    app.run(host=bind_ip, port=port, debug=debug_mode)
