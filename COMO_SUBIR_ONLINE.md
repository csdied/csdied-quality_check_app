# 🚀 Como subir o app online (sem instalar nada)

Vamos colocar seu app no ar **em 10 minutos**, grátis, no Render.com.
Você não precisa saber programar nem usar terminal.

---

## Resultado final

Sua equipe vai acessar uma URL tipo:
```
https://quality-check-pesquisa.onrender.com
```

Funciona em qualquer computador, celular, tablet. Sem instalar nada.

---

## Passo 1 — Criar conta no GitHub (2 min)

GitHub é onde seu código fica guardado. Render lê dali.

1. Vá em https://github.com/signup
2. Crie a conta com seu email (não precisa cartão)
3. Confirme o email

---

## Passo 2 — Subir o código no GitHub (3 min)

**Sem terminal, tudo pelo navegador:**

1. Logado no GitHub, clique no botão verde **"New"** ou no **"+"** no canto superior direito → **"New repository"**
2. Em "Repository name" digite: `quality-check-pesquisa`
3. Deixe **Public** marcado
4. **NÃO marque** nenhuma das opções "Add a README", "Add .gitignore" etc.
5. Clique em **"Create repository"**

Agora você verá uma tela com instruções. Ignore tudo. Faça isso:

6. Clique no link **"uploading an existing file"** (no meio da página) — ou vá em https://github.com/SEU_USUARIO/quality-check-pesquisa/upload/main
7. Arraste **TODOS os arquivos** da pasta `quality_check_app` que você baixou:
   - `app.py`
   - `quality.py`
   - `requirements.txt`
   - `render.yaml`
   - `README.md`
   - A pasta `templates/` inteira (com `index.html` dentro)

   ⚠️ **Importante:** arraste o conteúdo da pasta, NÃO a pasta inteira. Os arquivos têm que ficar na raiz do repositório.

8. Lá embaixo da página, em "Commit changes", clique no botão verde **"Commit changes"**

Pronto, código tá no GitHub.

---

## Passo 3 — Conectar no Render (3 min)

1. Vá em https://render.com
2. Clique em **"Get Started"** → faça login com **"GitHub"** (o botão preto)
3. Autorize o Render a acessar seus repositórios
4. Na tela inicial do Render, clique em **"+ Add new"** → **"Web Service"**
5. Escolha o repositório `quality-check-pesquisa` que você acabou de criar
6. O Render vai detectar o arquivo `render.yaml` e preencher tudo automaticamente

   Ele vai mostrar:
   - Name: `quality-check-pesquisa`
   - Runtime: `Python`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app --timeout 120`
   - Plan: **Free**

7. Role até embaixo e clique em **"Create Web Service"**

---

## Passo 4 — Esperar (3 min)

O Render vai:
1. Baixar seu código
2. Instalar Flask, pandas, etc.
3. Subir o servidor

Você verá os logs em tempo real. Quando aparecer:
```
Your service is live 🎉
```

Pronto. No topo da tela tem a URL do seu app, tipo:
```
https://quality-check-pesquisa-xxxx.onrender.com
```

Compartilhe essa URL com sua equipe.

---

## Como atualizar o app no futuro

Se você quiser mudar alguma coisa (ex: adicionar uma marca à blacklist):

1. Vá no GitHub, no seu repositório
2. Clique no arquivo que quer editar (ex: `quality.py`)
3. Clique no ícone de **lápis** ✏️ (canto superior direito do arquivo)
4. Edite
5. Lá embaixo clique em **"Commit changes"**

O Render detecta a mudança e re-deploya automaticamente em ~3min.

---

## ⚠️ Importante saber sobre o plano grátis

- **Sleep após 15 min sem uso:** se ninguém acessa por 15 minutos, o app "dorme". Quando alguém acessar de novo, demora ~30 segundos pra acordar. Depois fica rápido. Não é problema pra uso ocasional.
- **750 horas/mês grátis:** mais que suficiente.
- **512 MB RAM:** processa arquivos até 50 MB sem problema. Se precisar processar arquivos enormes, dá pra subir pro plano pago de $7/mês depois.

---

## Quem vai usar

Qualquer pessoa com a URL pode usar. Se você quiser **proteger com senha**,
me avise — adiciono autenticação simples em 5 minutos.

---

## Problemas comuns

**"Build failed" no Render:**
- Verifique que `requirements.txt` está na raiz do repositório (não dentro de uma pasta)
- Verifique que o nome do arquivo está exatamente assim: `requirements.txt` (não `Requirements.txt` nem `requirements.txt.txt`)

**"App crashed" depois do deploy:**
- Veja os logs no Render. Geralmente é uma versão diferente do Python. Já configurei pra usar 3.11 que é estável.

**App tá lento na primeira vez do dia:**
- É o "sleep" do plano free, normal. Espere 30s e fica rápido.

Qualquer problema, me chama de volta no Claude e te ajudo.
