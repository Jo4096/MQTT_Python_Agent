import paho.mqtt.client as mqtt
import time
import asyncio
import socket
import json
import os
import threading
import pandas as pd
from datetime import datetime


class MQTT_Agent:
    def __init__(self, broker, port=1883, client_id=None, topics_subscribe=None,
             on_message_callback=None, keep_alive=60, username=None, password=None,
             clean_session=True, debug_prints=False,
             enable_ping=False, enable_pong=False, ping_period=30):
        
        self.enable_ping = enable_ping
        self.enable_pong = enable_pong
        self.ping_period = ping_period
        self._ping_task = None

        self.broker = broker
        self.port = port
        self.client_id = client_id or "mqtt_agent_" + str(int(time.time()))
        self.topics_subscribe = topics_subscribe or ["devices/+/data"]
        self.on_message_callback = on_message_callback
        self.keepalive = keep_alive
        self.username = username
        self.password = password
        self.clean_session = clean_session
        self.debug = debug_prints
        self.known_devices = set()
        self.commands_registry = {}
        self.client = mqtt.Client(client_id=self.client_id, clean_session=self.clean_session)

        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
        self.client.on_message = self._internal_on_message
        
        if self.enable_pong:
            self.commands_registry["ping"] = self._handle_ping_command


        self.message_log = pd.DataFrame(columns=["timestamp_received", "sender_id", "command", "timestamp_sent", "topic", "message"])


    @classmethod
    def from_json(cls, json_path):
        """Cria uma instância de MQTT_Agent a partir de um ficheiro de configuração JSON"""
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"[ERRO] Ficheiro JSON não encontrado: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        return cls(
            broker=config.get("BROKER_ADDRESS", "localhost"),
            port=config.get("BROKER_PORT", 1883),
            client_id=config.get("CLIENT_ID"),
            topics_subscribe=config.get("TOPICS_SUBSCRIBE", ["devices/+/data"]),
            keep_alive=config.get("KEEP_ALIVE", 60),
            username=config.get("USERNAME"),
            password=config.get("PASSWORD"),
            clean_session=config.get("CLEAN_SESSION", True),
            debug_prints=config.get("DEBUG", False),
            enable_ping=config.get("ENABLE_PING", False),
            enable_pong=config.get("ENABLE_PONG", False),
            ping_period=config.get("PING_PERIOD", 30)
        )

    def command(self, name):
        """Decorator para registar comandos que recebem JSON"""
        def decorator(func):
            self.commands_registry[name] = func
            return func
        return decorator

    def _internal_on_message(self, client, userdata, msg):
        try:
            payload_dict = json.loads(msg.payload.decode("utf-8"))
            self._log_message(msg.topic, payload_dict)

            sender_id = payload_dict.get("sender_id", "unknown")
            command = payload_dict.get("command", "none")
            message = payload_dict.get("message", "")

            if sender_id != "unknown" and sender_id != self.client_id:
                if self.debug and sender_id not in self.known_devices:
                    print(f"[INFO] Novo dispositivo detetado: {sender_id}")
                self.known_devices.add(sender_id)

            if self.on_message_callback:
                self.on_message_callback(sender_id, command, message)
            
            if command in self.commands_registry:
                self.commands_registry[command](sender_id, message)

        except json.JSONDecodeError:
            self._log_message(msg.topic, msg.payload.decode("utf-8"))
            if self.on_message_callback:
                self.on_message_callback("unknown", "text_message", msg.payload.decode("utf-8"))
            if self.debug:
                print(f"[ERRO] Mensagem inválida (não JSON) no tópico: {msg.topic}")

        except Exception as e:
            if self.debug:
                print(f"[ERRO] Erro ao processar mensagem: {e}")


    def _log_message(self, topic, payload):
        """
        Adiciona uma entrada ao log de mensagens.
        - Aceita um dicionário (JSON) ou uma string como payload.
        """
        new_entry = {}
        if isinstance(payload, dict):
            new_entry = {
                "timestamp_received": datetime.now().isoformat(),
                "sender_id": payload.get("sender_id", "unknown"),
                "command": payload.get("command", ""),
                "timestamp_sent": payload.get("timestamp", None),
                "topic": topic,
                "message": payload.get("message", "")
            }
        else:
            new_entry = {
                "timestamp_received": datetime.now().isoformat(),
                "sender_id": "unknown",
                "command": "text_message",
                "timestamp_sent": None,
                "topic": topic,
                "message": str(payload)
            }

        self.message_log = pd.concat([self.message_log, pd.DataFrame([new_entry])], ignore_index=True)


    def default_on_message(self, device_id, topic, payload):
        print(f"[{device_id}] {payload} (via {topic})")

    def connect(self):
        self.client.connect(self.broker, self.port, self.keepalive)
        for topic in self.topics_subscribe:
            self.client.subscribe(topic)
            if self.debug:
                print(f"[INFO] Subscrito a {topic}")
        self.client.loop_start()

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    def publish(self, topic, message):
        self.client.publish(topic, message)

    def publish_to_device(self, device_id, message_data):
        topic = f"devices/{device_id}/cmd"
        message_data["sender_id"] = self.client_id
        payload = json.dumps(message_data)
        self.publish(topic, payload)
        if self.debug:
            print(f"[ENVIO] Para {device_id}: {payload}")

    def publish_to_device_formatted (self, device_id, command, message):
        if isinstance(message, dict):
            message = json.dumps(message)

        payload = {
            "sender_id": self.client_id,
            "command": command,
            "timestamp": int(time.time()),
            "message": message
        }

        self.publish_to_device(device_id, payload)

    def get_known_devices(self):
        return list(self.known_devices)
    
    async def _send_ping(self):
        while True:
            payload = {
                "command": "ping",
                "sender_id": self.client_id,
                "timestamp": int(time.time())
            }
            self.publish("devices/all/data", json.dumps(payload))
            if self.debug:
                print(f"[PING] Enviado ping broadcast")
            await asyncio.sleep(self.ping_period)
    

    def _handle_ping_command(self, sender_id, message):
        """
        Processa o comando 'ping' e responde com um 'pong'.
        Esta função é chamada pelo registry de comandos.
        """
        print("")
        self.publish_to_device_formatted (sender_id, "pong", f"{self.client_id} manda pong")
        if self.debug:
            print(f"[PONG] Respondido pong para {sender_id}")



    def run(self):
        try:
            self.connect()
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            if self.enable_ping:
                self._ping_task = self.loop.create_task(self._send_ping())

            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            except Exception:
                local_ip = "127.0.0.1"
            finally:
                s.close()

            print(f"[MQTT] Agente iniciado em {local_ip}:{self.port}")
            print("[MQTT] Pressiona Ctrl+C para sair.")
            self.loop.run_forever()
        except KeyboardInterrupt:
            print("\n[MQTT] Interrupção recebida. A terminar...")
        finally:
            self.disconnect()
            print("[MQTT] Desligado com sucesso.")


    def run_on_separate_thread(self):
        """Inicia o agente MQTT numa thread separada (daemon)."""
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        if self.debug:
            print("[THREAD] MQTT Agent a correr em thread separada.")
        return thread

    def get_logs(self):
        return self.message_log.copy()
