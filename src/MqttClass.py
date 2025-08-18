import paho.mqtt.client as mqtt
import time
import asyncio
import socket
import msgpack
import json
import os
import threading
import pandas as pd
from datetime import datetime
import base64


MAX_CHAR_LIMIT = 12


class MQTT_Agent:
    def __init__(self, broker, port=1883, client_id=None, topics_subscribe=None,
                 on_message_callback=None, keep_alive=60, username=None, password=None,
                 clean_session=True, debug_prints=False,
                 enable_ping=False, enable_pong=False, enable_file_transfer=True, ping_period=30, write_period = 5):
        
        self.enable_ping = enable_ping
        self.enable_pong = enable_pong
        self.ping_period = ping_period

        self.enable_file_transfer = enable_file_transfer

        self._ping_task = None

        self.broker = broker
        self.port = port
        
        # Log da truncagem do client_id no init
        if client_id and len(client_id) > MAX_CHAR_LIMIT and debug_prints:
            print(f"[DEBUG] '{client_id}' -> '{client_id[:MAX_CHAR_LIMIT]}'.")
            
        self.client_id = client_id or "mqtt_agent_" + str(int(time.time()))
        self.client_id = self.client_id[:MAX_CHAR_LIMIT]

        self.topics_subscribe = topics_subscribe or ["devices/+/data"]
        self.on_message_callback = on_message_callback
        self.keepalive = keep_alive
        self.username = username
        self.password = password
        self.clean_session = clean_session
        self.debug = debug_prints

        self.write_period = write_period


        self.known_devices = set()
        
        self.file_bin = {}
        
        self.commands_registry = {}
        self.client = mqtt.Client(client_id=self.client_id, clean_session=self.clean_session)

        # CORREÇÃO: Adicionada a configuração de utilizador e palavra-passe aqui.
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)

        self.client.on_message = self._internal_on_message
        
        if self.enable_pong:
            self.commands_registry["ping"] = self._handle_ping_command

        if self.enable_file_transfer:
            self.commands_registry["bg_t"] = self._handle_begin_transfer
            self.commands_registry["ap_t"] = self._handle_append_transfer
            self.commands_registry["end_t"] = self._handle_end_transfer

        # Inicializa o lock para proteger recursos partilhados
        self.lock = threading.Lock()
        
        # CORREÇÃO: Altere as colunas do DataFrame para refletir as novas chaves (id, cmd)
        self.message_log = pd.DataFrame(columns=["id", "cmd", "topic", "msg"])

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
            enable_file_transfer=config.get("ENABLE_FILE_TRANSFER", True),
            ping_period=config.get("PING_PERIOD", 30)
        )

    def command(self, name):
        """Decorator para registar comandos que recebem dados."""
        def decorator(func):
            if self.debug and len(name) > MAX_CHAR_LIMIT:
                print(f"[DEBUG] '{name}' -> '{name[:MAX_CHAR_LIMIT]}' ")
            truncated_name = name[:MAX_CHAR_LIMIT]
            self.commands_registry[truncated_name] = func
            return func
        return decorator

    def _internal_on_message(self, client, userdata, msg):
        """
        Processa mensagens MQTT, suportando o formato MessagePack e fallback para JSON.
        """
        # print(f"{client=}, {userdata=}, {msg=}")  # CORREÇÃO: Desativei esta linha de debug.
        try:
            # Tenta descodificar como MessagePack primeiro
            payload_dict = msgpack.unpackb(msg.payload, raw=False)
            
            # CORREÇÃO: Use as novas chaves `id` e `cmd`.
            original_sender_id = payload_dict.get("id", "unknown")
            original_command = payload_dict.get("cmd", "none")

            if self.debug and len(original_sender_id) > MAX_CHAR_LIMIT:
                print(f"[DEBUG] '{original_sender_id}' -> '{original_sender_id[:MAX_CHAR_LIMIT]}'.")
            if self.debug and len(original_command) > MAX_CHAR_LIMIT:
                print(f"[DEBUG] '{original_command}' -> '{original_command[:MAX_CHAR_LIMIT]}'.")


            sender_id = original_sender_id[:MAX_CHAR_LIMIT]
            command = original_command[:MAX_CHAR_LIMIT]

            self._log_message(msg.topic, payload_dict)

            message = payload_dict.get("msg", "")

            if sender_id != "unknown" and sender_id != self.client_id:
                if self.debug and sender_id not in self.known_devices:
                    print(f"[INFO] Novo dispositivo detetado: {sender_id}")
                
                with self.lock:
                    self.known_devices.add(sender_id)

            if self.on_message_callback:
                # CORREÇÃO: Passa os argumentos corretos para o callback (id, cmd, msg).
                self.on_message_callback(sender_id, command, message)
            
            if command in self.commands_registry:
                self.commands_registry[command](sender_id, message)

        except msgpack.exceptions.UnpackException:
            # Fallback para JSON
            try:
                payload_dict = json.loads(msg.payload.decode("utf-8"))
                
                # CORREÇÃO: Adicionado fallback para as chaves antigas de JSON (sender_id, command, message).
                original_sender_id = payload_dict.get("id", payload_dict.get("sender_id", "unknown"))
                original_command = payload_dict.get("cmd", payload_dict.get("command", "none"))

                if self.debug and len(original_sender_id) > MAX_CHAR_LIMIT:
                    print(f"[DEBUG] '{original_sender_id}' -> '{original_sender_id[:MAX_CHAR_LIMIT]}'.")
                if self.debug and len(original_command) > MAX_CHAR_LIMIT:
                    print(f"[DEBUG] '{original_command}' -> '{original_command[:MAX_CHAR_LIMIT]}'.")


                sender_id = original_sender_id[:MAX_CHAR_LIMIT]
                command = original_command[:MAX_CHAR_LIMIT]

                self._log_message(msg.topic, payload_dict)
                message = payload_dict.get("msg", payload_dict.get("message", ""))
                
                
                if command in self.commands_registry:
                    self.commands_registry[command](sender_id, message)
                
                if self.on_message_callback:
                    self.on_message_callback(sender_id, command, message)

                if self.debug:
                    print("[INFO] Fallback para JSON bem-sucedido.")
            except json.JSONDecodeError:
                # CORREÇÃO: Adicionado um segundo fallback para mensagens de texto simples.
                text_message = msg.payload.decode("utf-8", "ignore")
                self._log_message(msg.topic, text_message)
                if self.on_message_callback:
                    self.on_message_callback("unknown", "text_message", text_message)
                if self.debug:
                    print(f"[ERRO] Mensagem inválida (não JSON ou MessagePack) no tópico: {msg.topic}")

        except Exception as e:
            if self.debug:
                print(f"[ERRO] Erro ao processar mensagem: {e}")

    def _log_message(self, topic, payload):
        """Adiciona uma entrada ao log de mensagens."""
        new_entry = {}
        if isinstance(payload, dict):
            new_entry = {
                "id": payload.get("id", payload.get("sender_id", "unknown"))[:MAX_CHAR_LIMIT],
                "cmd": payload.get("cmd", payload.get("command", ""))[:MAX_CHAR_LIMIT],
                "topic": topic,
                "msg": payload.get("msg", payload.get("message", ""))
            }
        else:
            new_entry = {
                "id": "unknown"[:MAX_CHAR_LIMIT],
                "cmd": "text_message"[:MAX_CHAR_LIMIT],
                "topic": topic,
                "msg": str(payload)
            }
        
        with self.lock:
            # CORREÇÃO: Use `pd.concat` de forma correta e mais eficiente.
            self.message_log = pd.concat([self.message_log, pd.DataFrame([new_entry])], ignore_index=True)


    def default_on_message(self, device_id, topic, payload, password=None):
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
        """Publica uma mensagem no tópico, convertendo o dicionário para MessagePack."""
        if isinstance(message, dict):
            # CORREÇÃO: Usar `use_bin_type=True` é crucial para dados binários.
            payload = msgpack.packb(message, use_bin_type=True)
            self.client.publish(topic, payload)
        else:
            self.client.publish(topic, message)

    def publish_to_device(self, device_id, message_data):
        topic = f"devices/{device_id}/cmd"
        message_data["id"] = self.client_id
        self.publish(topic, message_data)
        if self.debug:
            # Copiar para evitar modificar o original
            debug_msg = dict(message_data)
            # Se o 'msg' for bytes, substituir por string legível para JSON
            if isinstance(debug_msg.get("msg"), (bytes, bytearray)):
                debug_msg["msg"] = f"<{len(debug_msg['msg'])} bytes>"
            print(f"[ENVIO] Para {device_id}: {json.dumps(debug_msg)}")

    def publish_to_device_formatted(self, device_id, command, message):
        
        original_id = self.client_id
        original_command = command

        if self.debug and len(original_id) > MAX_CHAR_LIMIT:
            print(f"[DEBUG] '{original_id}' -> '{original_id[:MAX_CHAR_LIMIT]}'.")
        if self.debug and len(original_command) > MAX_CHAR_LIMIT:
            print(f"[DEBUG] '{original_command}' -> '{original_command[:MAX_CHAR_LIMIT]}'.")
    
        payload = {
            "id": original_id[:MAX_CHAR_LIMIT],
            "cmd": original_command[:MAX_CHAR_LIMIT],
            "msg": message
        }
        self.publish_to_device(device_id, payload)

    def get_known_devices(self):
        with self.lock:
            return list(self.known_devices)
    
    async def _send_ping(self):
        while True:
            # O payload do ping também é formatado e pode ser truncado
            original_id = self.client_id
            original_command = "ping"

            if self.debug and len(original_id) > MAX_CHAR_LIMIT:
                print(f"[DEBUG] '{original_id}' -> '{original_id[:MAX_CHAR_LIMIT]}'.")
            
            payload = {
                "cmd": original_command[:MAX_CHAR_LIMIT],
                "id": original_id[:MAX_CHAR_LIMIT],
            }
            # CORREÇÃO: O tópico de ping estava incorreto na versão antiga do git.
            self.publish("devices/all/data", payload)
            if self.debug:
                print(f"[PING] Enviado ping broadcast")
            await asyncio.sleep(self.ping_period)
    
    def _handle_ping_command(self, sender_id, message):
        self.publish_to_device_formatted(sender_id, "pong", f"{self.client_id} manda pong")
        if self.debug:
            print(f"[PONG] Respondido pong para {sender_id}")

    def _handle_begin_transfer(self, sender_id, message, ):
        with self.lock:
            self.file_bin[sender_id] = {
                "id": sender_id,
                "name": str(message),
                "data": b"",
                "isDone": False
            }

        if self.debug:
            print(f"[FILE] Iniciada transferência de '{message}' de {sender_id}.")

    def _handle_append_transfer(self, sender_id, message):
        with self.lock:
            if sender_id not in self.file_bin:
                if self.debug:
                    print(f"[FILE] Recebido chunk de {sender_id} sem BEGIN. Ignorado.")
                return

            # CORREÇÃO: Adiciona verificação para dados binários ou string
            chunk_data = message if isinstance(message, (bytes, bytearray)) else str(message).encode("utf-8")
            self.file_bin[sender_id]["data"] += chunk_data

        if self.debug:
            print(f"[FILE] {sender_id} -> chunk {len(chunk_data)} bytes acumulados ({len(self.file_bin[sender_id]['data'])} no total).")

    
    def _handle_end_transfer(self, sender_id, message):
        with self.lock:
            if sender_id not in self.file_bin:
                if self.debug:
                    print(f"[FILE] Recebido END de {sender_id} sem BEGIN. Ignorado.")
                return

            if message:
                # CORREÇÃO: Adiciona verificação para dados binários
                extra_data = message if isinstance(message, (bytes, bytearray)) else str(message).encode("utf-8")
                self.file_bin[sender_id]["data"] += extra_data

            self.file_bin[sender_id]["isDone"] = True
            
        if self.debug:
            fname = self.file_bin[sender_id]["name"]
            total = len(self.file_bin[sender_id]["data"])
            print(f"[FILE] Transferência concluída de {sender_id}: '{fname}' ({total} bytes).")

    def transfer_file(self, destination_id, file_path_or_data, is_raw_data=False, total_chunk_size_of_msgpack = 512):
        if not self.enable_file_transfer:
            if self.debug:
                print("[FILE] Transferência de ficheiros desativada.")
            return
        
        if is_raw_data:
            file_data = file_path_or_data if isinstance(file_path_or_data, (bytes, bytearray)) else bytes(file_path_or_data)
            file_name = f"raw_data_{int(time.time())}.dat"
        else:
            if not os.path.exists(file_path_or_data):
                if self.debug:
                    print(f"[FILE] Ficheiro não encontrado: {file_path_or_data}")
                return
            file_name = os.path.basename(file_path_or_data)
            with open(file_path_or_data, "r") as f:
                file_data = f.read()

        payload_begin = {
            "id": self.client_id[:MAX_CHAR_LIMIT],
            "cmd": "bg_t",
            "msg": file_name
        }

        self.publish_to_device(destination_id, payload_begin)
        if self.debug:
            print(f"[FILE] BEGIN enviado para {destination_id} ({file_name})")

        test_payload = {
            "id": self.client_id[:MAX_CHAR_LIMIT],
            "cmd": "ap_t",
            "msg": ""
        }

        fixed_overhead = len(msgpack.packb(test_payload, use_bin_type=True))
        max_chunk_size = total_chunk_size_of_msgpack - fixed_overhead
        if max_chunk_size <= 0:
            raise ValueError(f"Chunk size demasiado pequeno para suportar cabeçalho MQTT. Mínimo necessário: {fixed_overhead + 1} bytes.")

        offset = 0
        while offset < len(file_data):
            chunk = file_data[offset: (offset + max_chunk_size)]
            self.publish_to_device_formatted(destination_id, "ap_t", chunk)

            if self.debug:
                print(f"[FILE] Chunk enviado ({len(chunk)} bytes) para {destination_id}")
            offset += len(chunk)     

        payload_end = {
            "id": self.client_id[:MAX_CHAR_LIMIT],
            "cmd": "end_t",
            "msg": ""
        }

        self.publish_to_device(destination_id, payload_end)
        if self.debug:
            print(f"[FILE] END enviado para {destination_id} ({file_name})")

    def extractFile(self, from_device_id, read_as):
        with self.lock:
            if from_device_id not in self.file_bin:
                if self.debug:
                    print(f"[EXTRACT] Ficheiro de {from_device_id} não encontrado.")
                return None
            
            if not self.file_bin[from_device_id]["isDone"]:
                if self.debug:
                    print(f"[EXTRACT] Ficheiro de {from_device_id} ainda não está pronto.")
                return None
            
            file_name = self.file_bin[from_device_id]["name"]
            file_data = self.file_bin[from_device_id]["data"]

        # Retorna string se pedido, senão bytes
        if read_as and read_as.lower() == "str":
            try:
                file_data = file_data.decode("utf-8")
            except UnicodeDecodeError:
                if self.debug:
                    print(f"[EXTRACT] Erro a descodificar o ficheiro de {from_device_id} como string. A devolver bytes.")
                # mantém em bytes
        return file_name, file_data

    def create_file(self, from_device_id):
        with self.lock:
            if from_device_id not in self.file_bin:
                if self.debug:
                    print(f"[CREATE_FILE] Nenhum ficheiro encontrado de '{from_device_id}'.")
                return False  # <-- retorna False se não existir

            file_name = os.path.basename(self.file_bin[from_device_id]["name"])
            file_data = self.file_bin[from_device_id]["data"]

        try:
            with open(file_name, "wb") as f:
                f.write(file_data)
            if self.debug:
                print(f"[CREATE_FILE] Ficheiro '{file_name}' criado com sucesso a partir de '{from_device_id}'.")

            with self.lock:
                del self.file_bin[from_device_id]

            if self.debug:
                print(f"[CREATE_FILE] Dados de '{from_device_id}' removidos da memória.")

            return True  # <-- sucesso na criação

        except Exception as e:
            if self.debug:
                print(f"[CREATE_FILE] Erro ao criar o ficheiro '{file_name}': {e}")
            return False  # <-- erro na criação


    def _write_first_ready_file(self):
        with self.lock:
            # Get a list of device IDs with completed file transfers
            completed_devices = [device_id for device_id, file_info in self.file_bin.items() if file_info["isDone"]]
            
            if not completed_devices:
                if self.debug:
                    print("[FILE] Nenhum ficheiro concluído para escrever.")
                return False, ""
            
            from_device_id = completed_devices[0]
            file_info = self.file_bin[from_device_id]
            file_name = file_info["name"]
            file_data = file_info["data"]
            
            # Define the output directory and ensure it exists
            output_dir = "received_files"
            os.makedirs(output_dir, exist_ok=True)
            file_path = os.path.join(output_dir, file_name)

            try:
                # Write the file in binary mode
                with open(file_path, "wb") as f:
                    f.write(file_data)
                
                if self.debug:
                    print(f"[FILE] Ficheiro '{file_name}' de '{from_device_id}' escrito com sucesso.")
                
                # Clean up the in-memory data after successful write
                del self.file_bin[from_device_id]
                if self.debug:
                    print(f"[FILE] Dados de '{from_device_id}' removidos da memória.")
                
                return True, file_path
            
            except Exception as e:
                if self.debug:
                    print(f"[ERRO] Erro ao escrever o ficheiro '{file_name}': {e}")
                return False, ""

    async def _file_writing_loop(self):
        """
        Periodicamente verifica e escreve ficheiros recebidos.
        """
        while True:
            try:
                success, file_path = self._write_first_ready_file()
                if success:
                    if self.debug:
                        print(f"[FILE] Ficheiro {file_path} escrito.")
            except Exception as e:
                if self.debug:
                    print(f"[ERRO] Erro no loop de escrita: {e}")
            await asyncio.sleep(self.write_period)

    def run(self):
        try:
            self.connect()
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # Start the ping task if enabled
            if self.enable_ping:
                self._ping_task = self.loop.create_task(self._send_ping())

            # New: Start the file writing task
            self.loop.create_task(self._file_writing_loop())
            
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
        with self.lock:
            return self.message_log.copy()
