# O MQTT é um protocolo de mensagens super leve, ideal para a Internet das Coisas (IoT).

Imagina-o como um sistema de correio.
- Numa comunicação normal (tipo cliente-servidor), tens de pedir a carta para a receber.
- No MQTT, as cartas chegam-te automaticamente.

Isto funciona com base em três conceitos simples:
- **`Broker`**: É o centro de correio. Recebe todas as mensagens e distribui-as para quem as quer.
- **`Publisher`**: É quem envia a carta. A sua única responsabilidade é enviar a mensagem para o broker.
- **`Subscriber`**: É quem recebe a carta. Ele regista o seu interesse em "tópicos" específicos (por exemplo, "notícias sobre tecnologia") e o broker envia-lhe todas as mensagens com esse tópico.

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

# Codigo

# Construtor da classe

O construtor (__init__) da classe MQTT_Agent é o coração da tua aplicação, onde defines todas as configurações e inicializas os componentes necessários para a comunicação MQTT.

Visão Geral dos Argumentos
A classe é altamente configurável e aceita diversos argumentos para adaptar-se a diferentes cenários, desde um simples teste local até uma implementação de produção segura.
- **`broker`**: O endereço IP ou nome de domínio do servidor MQTT a que te vais ligar.
- **`port`**: A porta de comunicação do broker (a porta padrão é 1883).
- **`client_id`**: Um identificador único para o teu agente. Se não for fornecido, será gerado um ID aleatório.
- **`topics_subscribe`**: Uma lista de tópicos MQTT a que o agente irá subscrever para receber mensagens.
- **`keep_alive`**: O tempo máximo, em segundos, que o agente espera por uma resposta do broker antes de assumir que a ligação foi perdida.
- **`username`, `password`**: Credenciais para autenticação no broker, caso seja necessário.
- **`debug_prints`**: Um flag booleano para ativar ou desativar as mensagens de depuração na consola.
- **`enable_ping`, `enable_pong`, `ping_period`**: Argumentos para ativar a funcionalidade de "descoberta de dispositivos". O ping é uma mensagem enviada para encontrar outros dispositivos, e o pong é a resposta a essa mensagem.

# topics_subscribe
Muito basicamente queres te subscrever aos topicos sempre
- `devices/o_meu_device_id/cmd`  <-  usado para poderes **receber mensagens**
- `devices/all/data` <- **canal de broadcast**

**se** quiseres ouvir as mensagens todas e de todos os devices usa devices/+/data ou devices/+/cmd ou devices/# e ai tu ouves tudo e todos. Problema com isso podes te ouvir a ti proprio e começas a responder a ti proprio 

# Funcionalidade

Para a criação deste codigo inspirei-me no modo como APIs de bots funcionam (ex: Telebot do telegram e Discord.py/Nextcord.py)
Nestas APIs, usam-se decoradores para simplificar a implementação da lógica.

# Lógica dos Decoradores (@agent.command())

A classe MQTT_Agent usa a mesma filosofia para criar um sistema de eventos simples e intuitivo. O decorador @agent.command("nome_do_comando") faz a magia acontecer:
- **Registo Automático**: Ele diz à tua classe MQTT_Agent: "Associa esta função (por exemplo, handle_light_on_command) ao comando "ligar_luz"". É como se o agente mantivesse uma tabela de "tarefas" para cada comando que pode receber. Resumidamente: se receberes **ligar_luz** executa a função **handle_light_on_command**
- **Abstração de Lógica**: O decorador esconde a complexidade de teres de ler manualmente cada mensagem, analisar o seu conteúdo para encontrar o "comando" e chamar a função correta. Essa lógica está toda encapsulada dentro da tua classe MQTT_Agent.
- **Encapsulamento de Comportamento**: A tua função (handle_light_on_command) agora só precisa de saber o que fazer com os dados da mensagem (quem a enviou e qual é a mensagem). Não precisas de te preocupar com o tópico, o broker, ou qualquer outra complexidade do protocolo MQTT.


# Main Loop
A classe tem duas funções para executar o *loop* principal de processamento de mensagens.
- **`run()`**:
  - **Funcionamento**: Corre o *loop* de forma **bloqueante**.
  - **Melhor Uso**: Não é muito aconselhável se precisares de ter outros clientes a correr na mesma *thread*, como um bot do Discord ou do Telegram.
- **`run_on_separate_thread()`**:
  - **Funcionamento**: Corre o *loop* numa *thread* separada.
  - **Melhor Uso**: Isto é incrivelmente útil, pois a classe funciona em segundo plano e a tua *thread* principal fica livre para outras tarefas. Podes usá-la para enviar comandos manualmente, gerir outros clientes ou processar os logs (que são geridos automaticamente pelo agente, mas que podes querer filtrar ou exportar para um ficheiro Excel).
