# A.J Solutions — Gestão de Ordens de Serviço

Aplicativo em Streamlit para cadastro e acompanhamento de ordens de serviço de:

- Celulares
- Notebooks e computadores
- Coletores Zebra
- Impressoras Zebra
- Tablets e leitores de código de barras

## Recursos

- Login por usuário e senha
- Cadastro de ordem de serviço
- Consulta e pesquisa de ordens
- Alteração de status
- Valores de peças e mão de obra
- Garantia
- Geração de ficha em PDF
- Banco de dados online pelo Supabase

## Executar localmente

```bash
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

## Configuração

Crie o arquivo local `.streamlit/secrets.toml` ou configure os Secrets no Streamlit Cloud:

```toml
SUPABASE_URL = "https://SEU-PROJETO.supabase.co"
SUPABASE_KEY = "SUA-CHAVE"

[usuarios.admin]
nome = "Administrador"
senha_hash = "HASH_SHA256_DA_SENHA"
```

Não publique o arquivo `secrets.toml` nem chaves do Supabase no GitHub.
