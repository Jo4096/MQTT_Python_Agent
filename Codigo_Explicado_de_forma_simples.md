# O MQTT é um protocolo de mensagens super leve, ideal para a Internet das Coisas (IoT).

Imagina-o como um sistema de correio.
- Numa comunicação normal (tipo cliente-servidor), tens de pedir a carta para a receber.
- No MQTT, as cartas chegam-te automaticamente.

Isto funciona com base em três conceitos simples:
- **Broker**: É o centro de correio. Recebe todas as mensagens e distribui-as para quem as quer.
- **Publisher**: É quem envia a carta. A sua única responsabilidade é enviar a mensagem para o broker.
- **Subscriber**: É quem recebe a carta. Ele regista o seu interesse em "tópicos" específicos (por exemplo, "notícias sobre tecnologia") e o broker envia-lhe todas as mensagens com esse tópico.

# Brokers Públicos

**Vantagens:**
- Não precisas de instalar nada.
- Ideal para testes rápidos ou pequenos projetos.

**Desvantagens:**
- Qualquer pessoa pode ouvir os teus tópicos (não é seguro).
- Qualquer pessoa pode enviar mensagens para ti.
- Normalmente são mais lentos e limitados (uso partilhado).

# Brokers Privados

Um Broker privado é instalado num servidor teu (pode ser um Raspberry Pi, um PC, ou uma cloud).

**Vantagens:**
- Total controlo sobre quem acede.
- Mais rápido, porque está na tua rede local.
- Mais seguro.

**Desvantagens:**
- Tens de o instalar e configurar.
- Requer mais conhecimento técnico.
- Fica a correr no background do teu PC.

# Desativar o Mosquitto de correr por default no Windows

O que podes fazer é desativar o serviço de arranque automático no Windows:

1. Pressiona `Win + R`, escreve `services.msc` e carrega em Enter.
2. Encontra o serviço que não queres que arranque.
3. Clica com o botão direito, escolhe "Propriedades".
4. Em "Tipo de arranque" (Startup Type), seleciona "Desativado" (Disabled).
5. Clica em OK.

# Executar o Mosquitto manualmente com um script (runBroker.py)

Se desativaste a task do Mosquitto de correr por default, podes usar o script `runBroker.py` num terminal à parte para correr o Broker com as configurações que quiseres, tornando a tua experiência mais prática em vez de estares a alterar as configurações manualmente.
Nota:
- Tens de colocar o Mosquitto como variável global de sistema 

#Codigo
