import os
import subprocess
import sys

MOSQUITTO_INSTALL_PATH = "C:\\Program Files\\mosquitto"
MOSQUITTO_EXE_PATH = os.path.join(MOSQUITTO_INSTALL_PATH, "mosquitto.exe")
MOSQUITTO_PASSWD_EXE_PATH = os.path.join(MOSQUITTO_INSTALL_PATH, "mosquitto_passwd.exe")

def perguntar_sim_nao(pergunta, default="s"):
    """
    Função auxiliar para fazer perguntas de sim/não ao utilizador.
    """
    resposta = input(f"{pergunta} [S/n]: ").strip().lower()
    if not resposta:
        resposta = default
    return resposta == "s"

def criar_ficheiro_passwords(password_file):
    """
    Cria ou atualiza um ficheiro de passwords para o Mosquitto.
    """
    print("\n--- Criar ou atualizar ficheiro de passwords ---")
    if not os.path.exists(MOSQUITTO_PASSWD_EXE_PATH):
        print(f"[ERRO] Não foi encontrado 'mosquitto_passwd.exe' em: {MOSQUITTO_PASSWD_EXE_PATH}")
        print("Certifique-se de que o Mosquitto está instalado e o caminho está correto.")
        sys.exit(1)

    username = input("Nome de utilizador para autenticação: ").strip()
    if not username:
        print("[ERRO] Nome de utilizador inválido. A sair.")
        sys.exit(1)

    # Verifica se o ficheiro já existe para decidir qual flag usar
    if not os.path.exists(password_file):
        # Usa a flag '-c' para criar um ficheiro novo
        command = [MOSQUITTO_PASSWD_EXE_PATH, "-c", password_file, username]
    else:
        # Se o ficheiro já existe, omite a flag '-c' para adicionar ou atualizar o utilizador
        command = [MOSQUITTO_PASSWD_EXE_PATH, password_file, username]

    try:
        # O subprocess.run irá permitir que o mosquitto_passwd peça a password interativamente
        subprocess.run(command, check=True)
        print(f"[SUCESSO] Ficheiro de passwords criado/atualizado em: {password_file}")
    except subprocess.CalledProcessError:
        print("[ERRO] Falha ao criar ou atualizar o ficheiro de passwords.")
        sys.exit(1)

def gerar_config(porta, usar_auth, password_file):
    """
    Gera o conteúdo do ficheiro de configuração do Mosquitto.
    """
    config = [
        f"listener {porta}",
        f"allow_anonymous {'false' if usar_auth else 'true'}"
    ]
    if usar_auth:
        # Substitui separadores de caminho para garantir compatibilidade no ficheiro de config
        config.append(f"password_file {password_file.replace(os.sep, '/')}")
    return "\n".join(config)

def escrever_config_file(config_text, config_path):
    """
    Escreve o conteúdo da configuração num ficheiro temporário.
    """
    try:
        with open(config_path, "w") as f:
            f.write(config_text)
        print(f"[SUCESSO] Ficheiro de configuração criado em: {config_path}")
    except Exception as e:
        print(f"[ERRO] Não foi possível escrever o ficheiro de configuração: {e}")
        sys.exit(1)

def correr_mosquitto(config_path):
    """
    Inicia o broker Mosquitto usando o ficheiro de configuração gerado.
    """
    if not os.path.exists(MOSQUITTO_EXE_PATH):
        print(f"[ERRO] Não foi encontrado Mosquitto em: {MOSQUITTO_EXE_PATH}")
        sys.exit(1)

    print("\n[INFO] A iniciar o broker Mosquitto... (Pressione Ctrl+C para terminar)\n")
    try:
        # O comando é executado com o ficheiro de configuração
        subprocess.run([MOSQUITTO_EXE_PATH, "-c", config_path])
    except KeyboardInterrupt:
        print("\n[INFO] Mosquitto terminado pelo utilizador.")

def main():
    """
    Função principal que orquestra a configuração e execução do Mosquitto.
    """
    print("\n--- Configuração Mosquitto ---")
    porta = input("Porta (default 1883): ").strip() or "1883"

    usar_auth = perguntar_sim_nao("Queres usar autenticação com palavra-passe?")

    password_file = ""
    if usar_auth:
        password_file = input("Caminho para o ficheiro de passwords (Enter para usar './passwd'): ").strip() or os.path.join(os.getcwd(), "passwd")
        criar_ficheiro_passwords(password_file)

    config_text = gerar_config(porta, usar_auth, password_file)
    config_path = os.path.join(os.getcwd(), "mosquitto_temp.conf")
    escrever_config_file(config_text, config_path)

    correr_mosquitto(config_path)

if __name__ == "__main__":
    main()
