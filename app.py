from flask import Flask, request, jsonify
import pymysql
import random
import smtplib
from email.mime.text import MIMEText
from flask import Flask, request, jsonify
from summarization import summarize_text
from generation import generate_answer
from translation import translate_text
import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

app = Flask(__name__)
load_dotenv()
db_config = {
    'host' : os.getenv("DB_HOST"),
    'user' : os.getenv("DB_USER"),
    'port' : int(os.getenv("DB_PORT")),
    'password': os.getenv("DB_PASSWORD"),
    'database': os.getenv("DB_NAME")
}
SECRET_KEY=os.getenv("SECRET_KEY")
def get_connection():
    conn = pymysql.connect(
        host=db_config['host'],
        user=db_config['user'],
        passwd=db_config['password'],
        database=db_config['database'],
        port=db_config['port'],
        cursorclass=pymysql.cursors.DictCursor
    )
    return conn
def get_user_id_jwt(token):
    if token.startswith('Bearer'):
        token=token[7:]
    else:
        raise ValueError("Token inválido!!!")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user_id=payload.get('user_id')
        if not user_id:
            raise ValueError("User ID não encontrado no token!!!")
        return user_id
    except jwt.ExpiredSignatureError:
        raise ValueError("Token Expirado!!!")
    except jwt.InvalidTokenError:
        raise ValueError("Token inválido!!!")
def send_verification_email(to_email, code):
    smtp_server='smtp.gmail.com'
    smtp_port=587
    smtp_user=os.getenv("SMTP_USER")
    smtp_password=os.getenv("SMTP_PASSWORD")

    msg = MIMEText(f'seu código de verificação é: {code}')
    msg["Subject"] = "Confirmação de cadastro MAKENLP"
    msg["From"] = smtp_user
    msg["To"] = to_email

    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(smtp_user, smtp_password)
    server.send_message(msg)
    server.quit()

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    login = data.get('login')
    password = data.get('password')

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM user WHERE login=%s",
        (login,)
    )
    user = cursor.fetchone()
    conn.close()

    if not user:
        return jsonify({'status': 'error', 'message': 'Usuário não cadastrado'}), 404
    if user['password'] != password:
        return jsonify({'status': 'error', 'message': 'Senha incorreta'}), 401
    
    payload = {
        "user_id": user["id"],
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    token=jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return jsonify({'status': 'success', 'message': 'Login realizado', 'token': token, 'login': user['login']}), 200
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    login=data.get("login")
    email = data.get("email")
    password = data.get("password")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user WHERE email=%s", (email,))
    user = cursor.fetchone()

    if user:
        conn.close()
        return jsonify({"status": "error", "message": "Email já cadastrado"}), 409

    verification_code = str(random.randint(100000, 999999))
    cursor.execute(
        "INSERT INTO user (login,email, password, code, verified) VALUES (%s, %s, %s, %s, %s)",
        (login,email, password, verification_code, 0)
    )
    conn.commit()
    conn.close()

    send_verification_email(email, verification_code)

    return jsonify({"status": "success", "message": "Usuário criado, código enviado para o email"}), 201

@app.route('/verify', methods=['POST'])
def verify():
    data = request.json
    email = data.get("email")
    code = data.get("code")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user WHERE email=%s", (email,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return jsonify({"status": "error", "message": "Usuário não encontrado"}), 404

    if user["code"] != code:
        conn.close()
        return jsonify({"status": "error", "message": "Código incorreto"}), 400

    cursor.execute("UPDATE user SET verified=1 WHERE email=%s", (email,))
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "Email verificado"}), 200

@app.route('/summarize', methods=['POST'])
def summarize():
    data = request.json
    text = data.get("text")
    if not text:
        return jsonify({"status": "error", "message": "Texto não enviado"}), 400
    summary = summarize_text(text)
    return jsonify({"status": "success", "summary": summary}), 200


@app.route('/answer', methods=['POST'])
def answer():
    data = request.json
    context = data.get("context")
    question = data.get("question")
    if not context or not question:
        return jsonify({"status": "error", "message": "Contexto ou pergunta faltando"}), 400
    answer = generate_answer(question, context)
    return jsonify({"status": "success", "answer": answer}), 200


@app.route('/translate', methods=['POST'])
def translate():
    data = request.json
    text = data.get("text")
    language = data.get("language")
    if not text or not language:
        return jsonify({"status": "error", "message": "Texto ou idioma faltando"}), 400
    translated_text = translate_text(text, language)
    return jsonify({"status": "success", "translated": translated_text}), 200

@app.route('/save', methods=['POST'])
def save():
    data=request.json
    text = data.get("text")
    summary = data.get("summary")
    context = data.get("context")
    answer = data.get("answer")
    question = data.get("question")
    translation = data.get("translation")
    language = data.get("language")
    translated_text = data.get("translated_text")
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"status": "error", "message": "Token não fornecido"}), 401

    try:
        user_id = get_user_id_jwt(token)
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 401

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO app_dados (user_id, text_summarization, summarized_text, text_generation, question, answer, text_translation, language, translated_text)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (user_id, text, summary, context, answer, question, translation, language, translated_text)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"status": "success", "message": "Dados salvos com sucesso!!!"}), 200

@app.route('/status', methods=['GET'])
def get_status():
     return jsonify({"status": "success", "message": "API online"}), 200

if __name__ == '__main__':
    app.run(debug=True)