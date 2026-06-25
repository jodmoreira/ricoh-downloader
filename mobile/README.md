# Ricoh Downloader App

App Android em Flutter para baixar fotos de uma Ricoh GR IIIx (via Wi-Fi).

Assim como no `ped-admin`, este repositório guarda apenas o código principal em Flutter (`lib/` e `pubspec.yaml`), para evitar versionar os gigabytes de binários gerados pelo Gradle no diretório `android/`.
A Action do GitHub cria a estrutura do Android no momento do build e já injeta as permissões necessárias.

## Funcionalidades
- Input do SSID e da Senha do Wi-Fi da câmera.
- Conecta-se automaticamente à rede Wi-Fi fornecida.
- Lista e compara o histórico de fotos baixadas (evita baixar duplicatas).
- Faz o download de fotos para a galeria pública do Android (`Pictures/Ricoh`).

## CI/CD e Obtainium

1. **Obtainium**: Instale no celular e aponte para este repositório do Github. O Obtainium acompanhará as **Releases** geradas automaticamente quando o código for atualizado.
2. **Build Automático**: Ao enviar commits (push) que modifiquem `mobile/` ou `build-apk.yml`, o Github Actions construirá o `.apk` e criará uma Release.

### Assinatura (para Atualizações automáticas do Obtainium)

Para que o Android permita atualizações sem precisar desinstalar o app (mantendo as configurações gravadas), é preciso que as versões sejam assinadas com o mesmo Keystore. 

Vá em **Settings -> Secrets and variables -> Actions** e crie os Secrets de repositório:
- `ANDROID_KEYSTORE_BASE64`: A base64 do seu keystore `.p12` ou `.jks` (`base64 keystore.jks`)
- `ANDROID_KEYSTORE_PASSWORD`: A senha do seu keystore
- `ANDROID_KEY_ALIAS`: O alias da sua chave (ex: `ricoh-dl`)

Se esses secrets não estiverem presentes, o Github Actions ainda vai buildar e fazer upload de um APK debug, mas as atualizações via Obtainium poderão não substituir o app antigo com sucesso.
