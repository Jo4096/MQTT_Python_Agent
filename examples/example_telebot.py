from MqttClass import MQTT_Agent
from telebot import TeleBot
import time
import json
import asyncio
import threading
import os
import tempfile

mqtt_agent = MQTT_Agent.from_json("Agent.json")

arduino_responses = {}
respondeu = False
@mqtt_agent.command("telebot_response")
def teste(device_id, doc):
    print(f"{device_id=}  e  {doc=}")
    global arduino_responses, respondeu
    print("arduino respondeu")
    arduino_responses[device_id] = doc
    respondeu = True



bot = TeleBot(
    token="192381093801989123098_OBVIAMENTE_O_MEU_TOKEN"
)

@bot.message_handler(commands=["start"])
def start(message):
    user_name = message.from_user.first_name
    bot.reply_to(message, f"Olá {user_name}")

@bot.message_handler(commands=["devices"])
def list_devices(message):
    devices = mqtt_agent.get_known_devices()
    reply = "Dispositivos ligados:\n" + "\n".join(devices) if devices else "Nenhum dispositivo conhecido."
    bot.reply_to(message, reply)




#rudimentar mas serve para o que é, correr embed de lua no esp32 (se o codigo ainda nao ta no meu git vai estar eventualmente)
@bot.message_handler(commands=["Arduino"])
def tele_to_lua(message):
    global arduino_responses, respondeu
    text = message.text or ""
    parts = text.split(maxsplit=2)

    if len(parts) < 3:
        bot.reply_to(message, "Uso correto: /Arduino <device_id> <mensagem>")
        return

    device_id = parts[1]
    comando = parts[2]

    message_data = {
        "command": "telebot",
        "message": comando,
        "sender_id": mqtt_agent.client_id
    }

    mqtt_agent.publish_to_device(device_id, message_data)
    bot.reply_to(message, f"Mensagem enviada para o dispositivo `{device_id}`:\n{comando}")

    count = 0
    while not respondeu and count < 3:
        time.sleep(1)
        count += 1

    resposta = arduino_responses
    print(resposta)
    if resposta:
        bot.reply_to(message, f"Resposta do dispositivo {resposta[device_id]}")
    else:
        bot.reply_to(message, f"Sem resposta do dispositivo `{device_id}` após 3 segundos.")
    respondeu = False
    arduino_responses = {}



pending_uploads = {}
#Exemplo de enviar ficheiros por MQTT (ver o branch msgpack-protocol de https://github.com/Jo4096/MQTT_Arduino_Agent)
@bot.message_handler(commands=["Lua"])
def lua_command_start(message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        bot.reply_to(message, "Uso correto: /Lua <device_id>")
        return
    
    device_id = parts[1]

    pending_uploads[message.from_user.id] = {"device_id": device_id}
    bot.reply_to(message, "Agora, envie o ficheiro .lua para carregar.")

@bot.message_handler(content_types=['document'])
def handle_file(message):
    user_id = message.from_user.id
    if user_id not in pending_uploads:
        bot.reply_to(message, "Por favor, envia primeiro o comando /Lua com device_id.")
        return

    doc = message.document
    file_name = doc.file_name
    if not file_name.lower().endswith(".lua"): #não é necessario mas isto vem com o intuito de ser para enviar scripts longos premanentes de lua, podes alterar ou retirar a extensão
        bot.reply_to(message, "O ficheiro deve ter extensão .lua")
        return

    try:
        file_info = bot.get_file(doc.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        with open(file_name, "wb") as f:
            f.write(downloaded_file)
        
        device_id = pending_uploads[user_id]["device_id"]

        mqtt_agent.transfer_file(device_id, file_name, total_chunk_size_of_msgpack=512)
        bot.reply_to(message, f"Ficheiro '{file_name}' enviado para o dispositivo `{device_id}`.")
        os.remove(file_name)

    except Exception as e:
        bot.reply_to(message, f"Erro ao enviar ficheiro: {e}")

    del pending_uploads[user_id]


if __name__ == "__main__":
    try:
        print("[MQTT]: A Começar...")
        mqtt_agent.run_on_separate_thread()


        print("[BOT] A Começar...")
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("\nDesligando...")
