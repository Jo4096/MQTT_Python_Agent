Agente Python MQTT
AgentMQTT: Uma Biblioteca Python para Comunicação Robusta em IoT

O AgentMQTT é um wrapper de alto nível para a biblioteca Paho MQTT, concebido para simplificar a comunicação em projetos de Internet das Coisas (IoT). Com uma arquitetura de mensagens flexível baseada em JSON e um mecanismo de descoberta automática de dispositivos, a biblioteca permite que os seus agentes Python e dispositivos ESP32 comuniquem de forma simples e eficaz. Ideal para domótica, o AgentMQTT garante que os dispositivos se encontram e interagem dinamicamente, sem a necessidade de configurações manuais complicadas.

Como Funciona
A biblioteca AgentMQTT baseia-se num protocolo de comunicação simples mas robusto, que assenta em três pilares principais:

1. Mensagens Estruturadas (Payload JSON)
Em vez de enviar dados brutos, a biblioteca padroniza cada mensagem numa estrutura JSON consistente. Esta estrutura inclui:
sender_id: O identificador único do dispositivo que enviou a mensagem. Isto é crucial para a auto-descoberta e para filtrar as próprias mensagens.
command: A intenção da mensagem (por exemplo, "ligar_luz", "ler_sensor", "settings"). É o que o agente recetor usa para decidir qual ação tomar.
message: O payload real da mensagem. Este campo é sempre uma string, mas pode conter dados formatados, como um JSON aninhado, permitindo uma flexibilidade ilimitada.

2. Descoberta Automática de Dispositivos (Ping-Pong)
A biblioteca elimina a necessidade de configurar manualmente a lista de dispositivos. O processo é simples:
Um agente envia periodicamente um comando "ping" para um tópico de transmissão (devices/all/data).
Todos os outros dispositivos que estão a ouvir nesse tópico recebem o ping.
Quando um dispositivo recebe um ping, ele responde com um "pong" para o sender_id do dispositivo que enviou o ping.

Desta forma, cada agente constrói dinamicamente a sua própria lista de dispositivos online. Este mecanismo garante que, assim que um novo dispositivo se liga à rede, todos os outros agentes ficam a saber da sua existência, tornando a sua rede escalável e resiliente.

3. Abstração e Simplicidade
A complexidade da comunicação MQTT e da serialização JSON é completamente abstraída. Como utilizador, você interage apenas com métodos de alto nível que esperam strings simples. A biblioteca cuida de todos os detalhes nos bastidores:
Na Publicação: Recebe o command e a message e converte-os num payload JSON completo antes da publicação.
Na Receção: Analisa o JSON recebido, extrai o command e a message e encaminha-os para a sua lógica de aplicação.
Isto permite-lhe concentrar-se na lógica da sua aplicação em vez de lidar com os detalhes técnicos de análise e formatação de mensagens.
