# Sistema de Upload de Arquivos — Protótipo AWS (Parte 1)

Este projeto é a **primeira etapa** do desenvolvimento de um sistema de upload de arquivos com integração à **AWS**, desenvolvido como parte da disciplina **Tópicos em Engenharia de Software**.  
Nesta fase inicial, o foco está na **aplicação web básica** (login, registro, edição de perfil) e na **configuração da infraestrutura na AWS** (VPC, sub-rede, tabela de rotas e instância EC2).

---

## Funcionalidades da Aplicação

A aplicação foi desenvolvida em **Flask (Python)** e conta com as seguintes operações:

- Registro de usuários  
- Login e logout  
- Edição de perfil  

> Nesta etapa, ainda **não há integração com o Amazon S3 e o Amazon RDS**. O armazenamento de arquivos e usuários é feito localmente no servidor.  
> A integração com serviços de armazenamento será implementada na **Parte 2** do projeto.

---

## Arquitetura Geral

### Aplicação
- **Framework:** Flask (Python)
- **Banco de Dados:** SQLite
- **Gerenciamento de ambiente:** virtualenv
- **Serviço de aplicação:** systemd

### Infraestrutura AWS
A aplicação foi implantada em uma instância **EC2** dentro de uma **VPC** configurada manualmente, seguindo a seguinte estrutura:

| Componente | Descrição |
|-------------|------------|
| **VPC** | Rede isolada criada para o projeto |
| **Sub-rede pública** | Sub-rede onde a instância EC2 está alocada |
| **Sub-rede privada** | Será usada posteriormente na segunda etapa para comunicação com o banco de dados, por exemplo |
| **Tabela de rotas** | Configurada para direcionar tráfego via Internet Gateway |
| **Internet Gateway** | Permite comunicação entre a VPC e a Internet |
| **Gateway NAT** | Fornecer conectividade entre as instâncias executadas na sub-rede privada da VPC e a Internet |
| **Grupo de Segurança** | Permite conexões HTTP e SSH |
| **Instância EC2** | Máquina virtual executando a aplicação Flask |
| **Tipo da instância** | t3.micro |
| **Sistema operacional** | Ubuntu 22.04 LTS |

---

## Deploy da Aplicação na EC2

### 1 - Clonar o repositório na instância

```bash
git clone https://github.com/3-du4rd4/files-app-flask.git
cd repositorio
```

### 2 - Criar e ativar o ambiente virtual

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3 - Instalar dependências

```bash
pip install -r requirements.txt
```

### 3 - Executar o app localmente (teste)

```bash
python app.py
```

### 4 - Criar o arquivo de serviço systemd
Crie o arquivo /etc/systemd/system/flask_app.service com o conteúdo abaixo e preencha os valores das variáveis de ambiente:

```bash
[Unit]
Description=Flask App Service
After=network.target

[Service]
User=root
WorkingDirectory=/home/ubuntu/caminho_do_seu_projeto/files-app-flask
Environment="SECRET_KEY="
Environment="DATABASE_URL="
Environment="FLASK_HOST="
Environment="FLASK_PORT="
Environment="FLASK_DEBUG="
ExecStart=/home/ubuntu/caminho_do_seu_projeto/files-app-flask/venv/bin/python3 run.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### 5 - Ativar e iniciar o serviço
```bash
sudo systemctl daemon-reload
sudo systemctl enable flask_app
sudo systemctl start flask_app
sudo systemctl status flask_app
```
A partir disso, a aplicação inicia automaticamente toda vez que a instância EC2 for reiniciada.

## Acesso à aplicação
A aplicação estará acessível no navegador pelo IP público da instância EC2:
```bash
http://<ip-publico-ec2>
```

## Próximos Passos (Parte 2)

- Integração com Amazon S3 para upload e armazenamento de arquivos
- Migrar SQLite para Amazon RDS
- Configuração do Gunicorn + Nginx
- Adaptar aplicação para as novas configurações
