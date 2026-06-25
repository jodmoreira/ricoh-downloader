# Ricoh Downloader

Um conjunto de ferramentas para automatizar o download de fotos da câmera **Ricoh GR IIIx** via conexão Wi-Fi. 

Este projeto contém duas soluções para o mesmo objetivo:
1. **App Android (Flutter)**: Para sincronizar as fotos direto no celular.
2. **Script Python**: Para baixar as fotos via linha de comando no computador.

Ambas as versões mantêm um histórico local do que já foi baixado, permitindo rodá-las múltiplas vezes sem duplicar arquivos na galeria ou na pasta.

---

## 📱 1. App para Android (Celular)

O app permite baixar as fotos da câmera sem cabos e de forma autônoma. Basta preencher as informações do Wi-Fi na interface, e ele conectará automaticamente à câmera, baixará as novas fotos para a pasta `Pictures/Ricoh` (visível na galeria do sistema) e desconectará sozinho.

### Como instalar via Obtainium (Recomendado)
O aplicativo não está na Google Play Store. Cada atualização do código gera um arquivo instalável `.apk` automaticamente na aba de "Releases" deste GitHub. 

A melhor forma de instalar e receber atualizações é pelo [Obtainium](https://github.com/ImranR98/Obtainium):
1. Instale o **Obtainium** no seu Android.
2. Abra o Obtainium, vá em **Add App** e cole o link deste repositório:
   `https://github.com/jodmoreira/ricoh-downloader`
3. Clique em **Add**. O Obtainium vai localizar a versão mais recente na aba Releases e oferecer para instalar o aplicativo (chamado "Ricoh DL").
4. Nas próximas vezes que uma atualização do app for lançada aqui no Github, o Obtainium vai notificar você e realizar a atualização com um toque.

> **Instalação Manual:** Se não quiser usar o Obtainium, basta abrir este repositório no Github pelo celular, clicar em **Releases**, baixar o arquivo `.apk` da versão mais recente e tocar para instalar (é necessário autorizar instalação de fontes desconhecidas no Android).

### Uso básico
1. Ligue a conexão sem fio da sua Ricoh (ela criará uma rede Wi-Fi que começa com `RICOH_...`).
2. Abra o app "Ricoh DL".
3. Insira o nome da rede (SSID) e a senha (vistos na tela da sua câmera).
4. Clique em **Sincronizar Fotos**. O app vai pedir permissões para mexer no Wi-Fi e salvar arquivos nas fotos, e fará todo o processo sozinho!

Para mais detalhes técnicos da versão mobile, veja o diretório [`mobile/`](./mobile/).

---

## 💻 2. Script para Computador (Python)

Uma solução voltada para rodar em **Linux**, **Windows** ou **WSL2** para sincronizar suas fotos com um diretório do seu PC.

### Pré-requisitos
- Python 3.8+
- Estar conectado de alguma forma na rede da câmera (manualmente pelo PC, ou automaticamente se for Windows/WSL informando SSID e senha para que o script cuide do `netsh`).

### Instalação

Abra o terminal, clone o repositório e instale as dependências:
```bash
git clone https://github.com/jodmoreira/ricoh-downloader.git
cd ricoh-downloader

# Recomenda-se criar um ambiente virtual (opcional, mas boa prática)
python3 -m venv .venv
source .venv/bin/activate  # ou .venv\Scripts\activate no Windows

pip install -r requirements.txt
```

### Uso básico

**Modo Manual (Qualquer SO):**
Conecte seu computador no Wi-Fi da câmera manualmente, depois rode:
```bash
python ricoh_downloader.py --dest ~/Imagens/Ricoh
```

**Modo Automático (Windows / WSL2):**
Deixe o script gerenciar o Wi-Fi e se conectar automaticamente na câmera pra você. Passe o SSID e a senha:
```bash
python ricoh_downloader.py --ssid RICOH_XXXXXX --password A-SENHA-DA-CAMERA --dest ~/Imagens/Ricoh
```
> *Dica*: No lugar de passar a senha no comando (que fica salva no histórico do terminal), você pode usar `--password-env RICOH_WIFI_PASS` e definir a variável de ambiente.

**Opções úteis:**
- `--dry-run`: Verifica e lista quais fotos seriam baixadas, sem baixar nada.
- `--reset-history`: Ignora o banco de dados e tenta baixar tudo novamente (arquivos locais com o mesmo nome serão sobrescritos se ainda existirem, útil para forçar reparo).
- `--ext JPG --ext DNG`: Baixa apenas formatos de arquivos específicos.

O histórico de downloads fica salvo em um banquinho leve `download_history.db` no diretório onde o script rodar.
