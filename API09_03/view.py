import os
import datetime
import jwt
import pygal

from flask import jsonify, request, Response
from flask_bcrypt import generate_password_hash, check_password_hash
from fpdf import FPDF

from main import app, con


if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


@app.route('/livro', methods=['GET'])
def livro():
    cur = con.cursor()
    try:
        cur.execute("""
        SELECT id_livro, titulo, autor, ano_publicacao
        FROM livro
        """)

        livros = cur.fetchall()

        lista = []

        for l in livros:
            lista.append({
                "id_livro": l[0],
                "titulo": l[1],
                "autor": l[2],
                "ano_publicacao": l[3]
            })

        return jsonify(lista), 200

    except Exception as e:
        return jsonify({"erro": str(e)}), 500

    finally:
        cur.close()


@app.route('/livro', methods=['POST'])
def criar_livro():
    token = request.headers.get("Authorization")

    if not token:
        return jsonify({"erro": "Token necessário"}), 401

    token = remover_bearer(token)

    try:
        payload = jwt.decode(token, senha_secreta, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return jsonify({'menssage': 'Token expirado'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'menssage': 'Token invalido'}), 401

    try:
        jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])

        titulo = request.form.get("titulo")
        autor = request.form.get("autor")
        ano_publicacao = request.form.get("ano_publicacao")
        imagem = request.files.get("imagem")

        if not titulo or not autor or not ano_publicacao:
            return jsonify({"erro": "Campos obrigatórios"}), 400

        cur = con.cursor()

        cur.execute(
            "INSERT INTO livro (titulo, autor, ano_publicacao) VALUES (?, ?, ?) RETURNING id_livro",
            (titulo, autor, ano_publicacao)
        )

        id_livro = cur.fetchone()[0]
        con.commit()

        if imagem:
            pasta = os.path.join(app.config['UPLOAD_FOLDER'], "livros")
            os.makedirs(pasta, exist_ok=True)

            nome = f"{id_livro}.jpg"
            caminho = os.path.join(pasta, nome)

            imagem.save(caminho)

        return jsonify({
            "mensagem": "Livro criado",
            "id_livro": id_livro
        }), 201

    except Exception as e:
        con.rollback()
        return jsonify({"erro": str(e)}), 500

    finally:
        cur.close()


@app.route('/livro/<int:id>', methods=['PUT'])
def editar_livro(id):

    cur = con.cursor()

    data = request.get_json()

    titulo = data.get("titulo")
    autor = data.get("autor")
    ano = data.get("ano_publicacao")

    cur.execute("""
        UPDATE livro
        SET titulo=?, autor=?, ano_publicacao=?
        WHERE id_livro=?
    """, (titulo, autor, ano, id))

    con.commit()
    cur.close()

    return jsonify({"mensagem": "Livro atualizado"})


@app.route('/livro/<int:id>', methods=['DELETE'])
def deletar_livro(id):

    cur = con.cursor()

    cur.execute("DELETE FROM livro WHERE id_livro=?", (id,))

    con.commit()

    cur.close()

    return jsonify({"mensagem": "Livro deletado"})


@app.route('/usuario', methods=['POST'])
def criar_usuario():

    dados = request.get_json()

    nome = dados.get("nome")
    usuario = dados.get("usuario")
    senha = dados.get("senha")

    senha_hash = generate_password_hash(senha).decode("utf-8")

    cur = con.cursor()

    cur.execute("""
        INSERT INTO usuario (nome, usuario, senha)
        VALUES (?, ?, ?)
    """, (nome, usuario, senha_hash))

    con.commit()

    cur.close()

    return jsonify({"mensagem": "Usuário criado"})


@app.route('/login', methods=['POST'])
def login():

    data = request.get_json()

    usuario = data.get("usuario")
    senha = data.get("senha")

    cur = con.cursor()

    cur.execute(
        "SELECT id, senha FROM usuario WHERE usuario=?",
        (usuario,)
    )

    resultado = cur.fetchone()

    if not resultado:
        return jsonify({"erro": "Usuário inválido"}), 401

    id_usuario = resultado[0]
    senha_hash = resultado[1]

    if not check_password_hash(senha_hash, senha):
        return jsonify({"erro": "Senha inválida"}), 401

    token = gerar_token(id_usuario)

    return jsonify({
        "mensagem": "Login realizado",
        "token": token
    })


@app.route('/usuario', methods=['GET'])
def listar_usuarios():

    cur = con.cursor()

    cur.execute("SELECT id, nome, usuario FROM usuario")

    usuarios = cur.fetchall()

    cur.close()

    lista = []

    for u in usuarios:

        lista.append({
            "id": u[0],
            "nome": u[1],
            "usuario": u[2]
        })

    return jsonify(lista)


@app.route('/usuario/<int:id>', methods=['PUT'])
def atualizar_usuario(id):

    dados = request.get_json()

    senha_hash = generate_password_hash(
        dados["senha"]
    ).decode("utf-8")

    cur = con.cursor()

    cur.execute("""
        UPDATE usuario
        SET nome=?, usuario=?, senha=?
        WHERE id=?
    """, (
        dados["nome"],
        dados["usuario"],
        senha_hash,
        id
    ))

    con.commit()

    cur.close()

    return jsonify({"mensagem": "Usuário atualizado"})


@app.route('/usuario/<int:id>', methods=['DELETE'])
def deletar_usuario(id):

    cur = con.cursor()

    cur.execute(
        "DELETE FROM usuario WHERE id=?",
        (id,)
    )

    con.commit()

    cur.close()

    return jsonify({"mensagem": "Usuário removido"})


@app.route('/pdf_usuarios')
def pdf_usuarios():

    cur = con.cursor()

    pdf = FPDF()

    pdf.add_page()

    pdf.set_font("Arial", "B", 16)

    pdf.cell(0, 10, "Relatorio de Usuarios", 0, 1, "C")

    pdf.ln(10)

    pdf.set_font("Arial", "", 12)

    cur.execute("SELECT id, nome, usuario FROM usuario")

    dados = cur.fetchall()

    for u in dados:
        linha = f"{u[0]} - {u[1]} - {u[2]}"
        pdf.cell(0, 10, linha, 0, 1)

    cur.close()

    pdf_bytes = pdf.output(dest='S').encode('latin-1')

    return Response(pdf_bytes, mimetype="application/pdf")


@app.route('/grafico')
def grafico():

    cur = con.cursor()

    cur.execute("""
        SELECT ano_publicacao, COUNT(*)
        FROM livro
        GROUP BY ano_publicacao
        ORDER BY ano_publicacao
    """)

    dados = cur.fetchall()

    cur.close()

    grafico = pygal.Bar()

    grafico.title = "Livros por ano"

    for d in dados:
        grafico.add(str(d[0]), d[1])

    return Response(
        grafico.render(),
        mimetype='image/svg+xml'
    )


def gerar_token(id_usuario):

    payload = {
        "id_usuario": id_usuario,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=30)
    }

    token = jwt.encode(
        payload,
        app.config['SECRET_KEY'],
        algorithm="HS256"
    )

    return token


def remover_bearer(token):

    if token.startswith("Bearer "):
        return token[7:]

    return token


