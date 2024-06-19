from flask import Flask, render_template, request, redirect, url_for, flash, jsonify,session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from openai import OpenAI

app = Flask(__name__)

client = OpenAI(api_key)

app.config['SECRET_KEY'] = 'sua_chave_secreta'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///minhabase.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'






class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_usuario = db.Column(db.String(150), nullable=False, unique=True)
    senha = db.Column(db.String(150), nullable=False)
    funcao = db.Column(db.String(50), nullable=False)  # 'funcionario' ou 'cliente'

class VeiculoBase:
    def __init__(self, marca, modelo, ano, preco_por_dia):
        self.marca = marca
        self.modelo = modelo
        self.ano = ano
        self.preco_por_dia = preco_por_dia

    def tipo_veiculo(self):
        pass

class Carro(VeiculoBase):
    def tipo_veiculo(self):
        return 'Carro'

class Moto(VeiculoBase):
    def tipo_veiculo(self):
        return 'Moto'

class Caminhao(VeiculoBase):
    def tipo_veiculo(self):
        return 'Caminhão'

class FabricaVeiculo:
    @staticmethod
    def criar_veiculo(tipo_veiculo, marca, modelo, ano, preco_por_dia):
        if tipo_veiculo == 'carro':
            return Carro(marca, modelo, ano, preco_por_dia)
        elif tipo_veiculo == 'moto':
            return Moto(marca, modelo, ano, preco_por_dia)
        elif tipo_veiculo == 'caminhao':
            return Caminhao(marca, modelo, ano, preco_por_dia)
        else:
            raise ValueError('Tipo de veículo desconhecido')

class Veiculo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    marca = db.Column(db.String(100), nullable=False)
    modelo = db.Column(db.String(100), nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    preco_por_dia = db.Column(db.Float, nullable=False)
    esta_disponivel = db.Column(db.Boolean, default=True)
    tipo = db.Column(db.String(50), nullable=False)  # 'carro', 'moto', 'caminhao'

class Aluguel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    veiculo_id = db.Column(db.Integer, db.ForeignKey('veiculo.id'), nullable=False)
    data_inicio = db.Column(db.DateTime, nullable=False)
    data_fim = db.Column(db.DateTime, nullable=False)
    pago = db.Column(db.Boolean, default=False)
    usuario = db.relationship('Usuario', backref='alugueis')
    veiculo = db.relationship('Veiculo', backref='alugueis')

class Pagamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluguel_id = db.Column(db.Integer, db.ForeignKey('aluguel.id'), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    endereco_entrega = db.Column(db.String(200), nullable=False)
    aluguel = db.relationship('Aluguel', backref='pagamento')



@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nome_usuario = request.form.get('nome_usuario')
        senha = request.form.get('senha')
        funcao = request.form.get('funcao')

        usuario = Usuario.query.filter_by(nome_usuario=nome_usuario, senha=senha, funcao=funcao).first()

        if usuario:
            login_user(usuario)
            if funcao == 'cliente':
                return redirect(url_for('alugar_veiculo'))
            elif funcao == 'funcionario':
                return redirect(url_for('gerenciar_veiculos'))
            else:
                flash('Função de usuário inválida. Entre em contato com o suporte.')
        else:
            flash('Login inválido. Verifique suas credenciais e tente novamente.')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/gerenciar_veiculos', methods=['GET', 'POST'])
@login_required
def gerenciar_veiculos():
    if current_user.funcao != 'funcionario':
        flash('Acesso negado')
        return redirect(url_for('index'))

    editar = None

    if request.method == 'POST':
        action = request.form.get('action')
        veiculo_id = request.form.get('veiculo_id')

        if action == 'delete' and veiculo_id:
            veiculo = Veiculo.query.get_or_404(veiculo_id)
            db.session.delete(veiculo)
            db.session.commit()
            flash('Veículo deletado com sucesso')
            return redirect(url_for('gerenciar_veiculos'))

        if action == 'edit' and veiculo_id:
            editar = Veiculo.query.get_or_404(veiculo_id)

        if not action or action == 'add' or (action == 'edit' and not veiculo_id):
            tipo_veiculo = request.form.get('tipo_veiculo')
            marca = request.form.get('marca')
            modelo = request.form.get('modelo')
            ano = request.form.get('ano')
            preco_por_dia = request.form.get('preco_por_dia')

            if veiculo_id:
                veiculo = Veiculo.query.get(veiculo_id)
                if veiculo:
                    veiculo.marca = marca
                    veiculo.modelo = modelo
                    veiculo.ano = ano
                    veiculo.preco_por_dia = preco_por_dia
                    veiculo.tipo = tipo_veiculo
                    db.session.commit()
                    flash('Veículo atualizado com sucesso')
                else:
                    flash('Veículo não encontrado')
            else:
                novo_veiculo = FabricaVeiculo.criar_veiculo(tipo_veiculo, marca, modelo, ano, preco_por_dia)
                veiculo = Veiculo(
                    marca=novo_veiculo.marca,
                    modelo=novo_veiculo.modelo,
                    ano=novo_veiculo.ano,
                    preco_por_dia=novo_veiculo.preco_por_dia,
                    tipo=novo_veiculo.tipo_veiculo().lower(),
                    esta_disponivel=True
                )
                db.session.add(veiculo)
                db.session.commit()
                flash('Veículo adicionado com sucesso')

    veiculos = Veiculo.query.filter_by(esta_disponivel=True).all()  # Somente veículos disponíveis
    return render_template('gerenciar_veiculos.html', veiculos=veiculos, editar=editar)

@app.route('/alugar_veiculo', methods=['GET', 'POST'])
@login_required
def alugar_veiculo():
    if current_user.funcao != 'cliente':
        flash('Acesso negado')
        return redirect(url_for('index'))

    if request.method == 'POST':
        veiculo_id = request.form.get('veiculo_id')
        data_fim_str = request.form.get('data_fim')
        if veiculo_id and data_fim_str:
            veiculo = Veiculo.query.get_or_404(veiculo_id)



            veiculo.esta_disponivel = False
            data_inicio = datetime.now()
            try:
                data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d')
            except ValueError:
                flash('Formato de data inválido. Use o formato YYYY-MM-DD.')
                return redirect(url_for('alugar_veiculo'))

            if data_fim <= data_inicio:
                flash('A data de término deve ser posterior à data de início.')
                return redirect(url_for('alugar_veiculo'))



            aluguel = Aluguel(usuario_id=current_user.id, veiculo_id=veiculo.id, data_inicio=data_inicio, data_fim=data_fim)
            db.session.add(aluguel)
            db.session.commit()
            flash('Veículo alugado com sucesso')
            return redirect(url_for('pagamento', aluguel_id=aluguel.id))
        else:
            flash('Veículo ou data de término não especificados.')

    veiculos = Veiculo.query.filter_by(esta_disponivel=True).all()
    return render_template('alugar_veiculo.html', veiculos=veiculos)

class EstrategiaPagamento(ABC):
    @abstractmethod
    def pagar(self, valor, endereco_entrega):
        pass

class PagamentoCartaoCredito(EstrategiaPagamento):
    def pagar(self, valor, endereco_entrega):
        return f"Pagamento de R${valor} realizado com cartão de crédito. Endereço de entrega: {endereco_entrega}"

class PagamentoPayPal(EstrategiaPagamento):
    def pagar(self, valor, endereco_entrega):
        return f"Pagamento de R${valor} realizado com PayPal. Endereço de entrega: {endereco_entrega}"

@app.route('/pagamento/<int:aluguel_id>', methods=['GET', 'POST'])
@login_required
def pagamento(aluguel_id):
    aluguel = Aluguel.query.get_or_404(aluguel_id)
    dias_alugados = (aluguel.data_fim - aluguel.data_inicio).days
    valor_total = dias_alugados * aluguel.veiculo.preco_por_dia  # Calcula o valor total do aluguel

    if request.method == 'POST':
        valor = valor_total  # Usando o valor calculado
        endereco_entrega = request.form.get('endereco_entrega')
        metodo_pagamento = request.form.get('metodo_pagamento')

        if metodo_pagamento == 'cartao_credito':
            estrategia_pagamento = PagamentoCartaoCredito()
        elif metodo_pagamento == 'paypal':
            estrategia_pagamento = PagamentoPayPal()
        else:
            flash('Método de pagamento inválido.')
            return redirect(url_for('pagamento', aluguel_id=aluguel_id))

        mensagem_pagamento = estrategia_pagamento.pagar(valor, endereco_entrega)
        pagamento = Pagamento(aluguel_id=aluguel_id, valor=valor, endereco_entrega=endereco_entrega)
        aluguel.pago = True
        db.session.add(pagamento)
        db.session.commit()
        flash(mensagem_pagamento)
        return redirect(url_for('chatgpt'))

    return render_template('pagamento.html', aluguel=aluguel, valor_total=valor_total)



@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome_usuario = request.form['nome_usuario']
        senha = request.form['senha']
        funcao = request.form['funcao']
        if nome_usuario and senha:
            novo_usuario = Usuario(nome_usuario=nome_usuario, senha=senha, funcao=funcao)
            db.session.add(novo_usuario)
            db.session.commit()
            return redirect(url_for('login'))
        else:
            flash('Nome de usuário e senha são obrigatórios.')
    return render_template('cadastro.html')


def perguntar(prompt):
    response = client.chat.completions.create(
    model="gpt-3.5-turbo-0125",
    response_format={ "type": "text" },
    messages=[
         {"role": "system", "content": "Responda mostrando as especificações do veiculo e falando seus pontos positivos e negativos"},
         {"role": "user", "content": prompt}
          ]
    )
    return response.choices[0].message.content

@app.route("/chatgpt", methods=['POST', 'GET'])
def chatgpt():

	if request.method == 'POST':
		prompt = request.form['modelo']
		resposta = perguntar(prompt)
		return render_template('chatgpt.html', resposta = resposta)
	return render_template('chatgpt.html')


db.create_all()

if __name__ == '__main__':
    app.run(debug=True)



