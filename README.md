
# MHZ ERP Cloud — Fase 1

## Entregas
- Login
- Dashboard executivo
- Cadastro e edição de produtos
- Custos, preços, margem e estoque mínimo
- Banco SQLite criado automaticamente no primeiro acesso
- Layout responsivo
- PWA para adicionar à tela inicial do iPhone
- Configuração básica para Render

## Acesso inicial
E-mail: `admin@mhz.local`
Senha: `MHZ@2026`

Altere a senha inicial antes de cadastrar dados reais. Defina também uma
`SECRET_KEY` forte no ambiente de produção; o arquivo `render.yaml` gera essa
chave automaticamente no Render.

## Rodar no computador
```bash
pip install -r requirements.txt
python app.py
```
Abra: `http://127.0.0.1:5000`

## Testes
```bash
python -m unittest discover -s tests
```

## Banco de dados no Render
O SQLite funciona para demonstração, mas o arquivo local pode ser perdido em
reinicializações do serviço. Para uso real, configure `DATABASE_PATH` em um
disco persistente ou migre o banco para PostgreSQL.

## Usar no iPhone
Primeiro publique o sistema em um servidor como Render. Depois:
Safari → Compartilhar → Adicionar à Tela de Início.

## Próxima fase
Fornecedores, compras, estoque automático, CRM, vendas, financeiro, importação do Excel, backup e usuários por perfil.
