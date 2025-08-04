import time
import json
import threading
from MqttClass import MQTT_Agent

# --- PARTE 1: DEFINIR OS AGENTES E SEUS COMANDOS ---

# Agente 1 (Simula um Raspberry Pi central)
agent1 = MQTT_Agent(
    broker="localhost",
    client_id="raspberry_pi",
    debug_prints=True,
    enable_ping=True,
    enable_pong=True,
    ping_period=60,
    topics_subscribe=[
        "devices/raspberry_pi/cmd",
        "devices/all/data",
    ]
)

# ---
# Agente 2 (Simula um ESP32)
agent2 = MQTT_Agent(
    broker="localhost",
    client_id="esp32_quarto",
    debug_prints=True,
    enable_ping=True,
    enable_pong=True,
    ping_period=60,
    topics_subscribe=[
        "devices/esp32_quarto/cmd",
        "devices/all/data",
    ]
)

@agent1.command("temperatura_report")
def handle_temp_report(sender_id, message):
    print(f"\n[Agente 1: {agent1.client_id}] -> RECEBIDO relatório de temperatura de '{sender_id}'.", flush=True)
    print(f"[Agente 1: {agent1.client_id}] -> Dados recebidos: {message}\n", flush=True)


# Agente 2 regista o comando que recebe: "ligar_luz"
@agent2.command("ligar_luz")
def handle_light_on_command(sender_id, message):
    print(f"\n[Agente 2: {agent2.client_id}] -> RECEBIDO comando 'ligar_luz' de '{sender_id}'.", flush=True)
    print(f"[Agente 2: {agent2.client_id}] -> Mensagem: {message}\n", flush=True)
    
# Agente 2 regista o comando que recebe: "ler_temperatura"
# Este comando é o pedido do Agente 1 para ler a temperatura.
@agent2.command("ler_temperatura")
def handle_read_temp_command(sender_id, message):
    print(f"\n[Agente 2: {agent2.client_id}] -> RECEBIDO comando 'ler_temperatura' de '{sender_id}'.", flush=True)
    print(f"[Agente 2: {agent2.client_id}] -> A enviar a temperatura de volta para '{sender_id}'...", flush=True)
    
    # Agente 2 responde ao Agente 1 com o comando "temperatura_report"
    response_payload = {
        "command": "temperatura_report",
        "message": json.dumps({"valor": 23.5, "unidade": "C"})
    }
    agent2.publish_to_device(sender_id, response_payload)


# --- PARTE 2: INICIAR OS AGENTES E SIMULAR A COMUNICAÇÃO ---

if __name__ == "__main__":
    try:
        agent1_thread = agent1.run_on_separate_thread()
        agent2_thread = agent2.run_on_separate_thread()

        print("A iniciar os agentes. Aguardando 10 segundos para a descoberta de dispositivos...", flush=True)
        time.sleep(10)

        print("\n--- Verificação da Descoberta ---", flush=True)
        print(f"Agente '{agent1.client_id}' conhece: {agent1.get_known_devices()}", flush=True)
        print(f"Agente '{agent2.client_id}' conhece: {agent2.get_known_devices()}", flush=True)
        
        if "esp32_quarto" in agent1.get_known_devices():
            print("\n--- Comunicação entre Agentes ---", flush=True)
            
            # Passo 1: Agente 1 envia um comando 'ligar_luz' para o Agente 2.
            print(f"[{agent1.client_id}] -> A ENVIAR comando 'ligar_luz' para '{agent2.client_id}'.", flush=True)
            publish_payload_1 = {
                "command": "ligar_luz",
                "message": "true"
            }
            agent1.publish_to_device("esp32_quarto", publish_payload_1)
            
            time.sleep(2)

            # Passo 2: Agente 1 envia um comando 'ler_temperatura' para o Agente 2.
            print(f"[{agent1.client_id}] -> A ENVIAR comando 'ler_temperatura' para '{agent2.client_id}'.", flush=True)
            publish_payload_2 = {
                "command": "ler_temperatura",
                "message": ""
            }
            agent1.publish_to_device("esp32_quarto", publish_payload_2)
            
            time.sleep(2)
        else:
            print("\nErro: Agente 1 não detetou o Agente 2. A descoberta falhou.", flush=True)
        
        print("\nExemplo concluído. Pressione Ctrl+C para terminar os agentes.", flush=True)
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nEncerrando...", flush=True)
    finally:
        agent1.disconnect()
        agent2.disconnect()
        print("Agentes desligados.", flush=True)
