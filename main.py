import machine
import dht
import network
import urequests
import utime
from umqtt.simple import MQTTClient

# Configurações do sensor DHT22
dht_pin = machine.Pin(15, machine.Pin.IN, machine.Pin.PULL_UP)  # Pino de dados do sensor DHT22
dht_sensor = dht.DHT22(dht_pin)

# Configurações do LED
led_pin = machine.Pin(2, machine.Pin.OUT)  # Pino do LED (D2 no ESP32)

# Configurações do WiFi
wifi_ssid = "Wokwi-GUEST"
wifi_password = ""

# Configurações do bot do Telegram
telegram_token = "Insira o Token aqui"
telegram_chats_ids = ["Insira o ID aqui"]

# Configurações do MQTT
mqtt_broker = "URL do Broker"
mqtt_port = "Porta do Broker"
mqtt_topic = "Tópico do Broker"
client = MQTTClient("esp32", mqtt_broker, mqtt_port)

# Função para enviar mensagem pelo Telegram
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    for chat_id in telegram_chats_ids:
        print(f"Enviando mensagem para id: {chat_id}")
        data = {
            "chat_id": chat_id,
            "text": f"{message}",
            "parse_mode": "HTML"
        }
        try:
            response = urequests.post(url, json=data)
            if response.status_code == 200:
                print("Mensagem enviada com sucesso")
            else:
                print("Falha ao enviar a mensagem")
                print(response.text)
            response.close()
        except Exception as e:
            print("Erro ao enviar mensagem pelo Telegram:", e)

# Função para verificar as condições climáticas baseado na temperatura e na umidade
def check_weather_conditions():
    dht_sensor.measure()
    humidity = dht_sensor.humidity()
    temperature = dht_sensor.temperature()

    utime.sleep(3)

    # Verificar se há um aumento repentino na umidade
    dht_sensor.measure()
    if dht_sensor.humidity() - humidity > 5:
        humidity = dht_sensor.humidity()
        return 1, "Indicativo de chuva. A umidade aumentou rapidamente.", humidity, temperature

    # Verificar se a umidade relativa está constantemente alta
    if humidity >= 90:
        return 2, "Indicativo de chuva. A umidade está elevada.", humidity, temperature

    # Verificar se a temperatura está próxima ao ponto de orvalho
    dew_point = temperature - ((100 - humidity) / 5)
    if temperature - dew_point <= 2.35:
        return 3, "Indicativo de chuva. Condições próximas ao ponto de orvalho.", humidity, temperature

    else:
        return 0, "Não há indicação de chuva no momento.", humidity, temperature

# Função para publicar a umidade no MQTT
def publish_mqtt(umidade, temperatura):
    client.publish(mqtt_topic, str(umidade) + "|" + str(temperatura))
    print(f"Enviado no MQTT - {umidade}|{temperatura}")

# Função principal
def main():
    # Conectar ao WiFi
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)
    wifi.connect(wifi_ssid, wifi_password)
    while not wifi.isconnected():
        pass
    print("Conectado ao WiFi")
    client.connect()

    send_msg_case_01 = 0
    send_msg_case_02 = 0
    send_msg_case_03 = 0
    time_to_sleep = 5
    while True:
        print("Verificando...")
        weather_status_code, weather_status_message, weather_humidity, weather_temperature = check_weather_conditions()
        publish_mqtt(weather_humidity, weather_temperature)  # Publica a umidade no MQTT

        if weather_status_code != 0:
            humidity_msg = f"\n\U0001F4A7  Umidade em {weather_humidity}%"
            message = "\u26A0  ATENÇÃO  \u26A0 \n \U000026C5  Recebendo atualizações climáticas  \U000026C5 \n"
            led_pin.on() # Acende o LED

            if weather_status_code == 1:
                if send_msg_case_01 < 1:
                    if send_msg_case_01 == 0:
                        send_telegram_message(message)
                        custom_messages = ["\U0001F45A  Não esqueça de retirar as roupas do varal"]
                        final_custom_message = ""
                        for msg in custom_messages:
                            final_custom_message += msg + "\n"
                        send_telegram_message(final_custom_message)
                    final_message = "\U00002602  " + weather_status_message + humidity_msg
                    send_telegram_message(final_message)
                    send_msg_case_01 += 1

            if weather_status_code == 2:
                if send_msg_case_02 < 5:
                    if send_msg_case_02 == 0:
                        send_telegram_message(message)
                        custom_messages = ["\U0001F45A  Não esqueça de retirar as roupas do varal", "\u2614  Vai sair? Não esqueça do guarda-chuva"]
                        final_custom_message = ""
                        for msg in custom_messages:
                            final_custom_message += msg + "\n"
                        send_telegram_message(final_custom_message)
                    final_message = "\U0001F327  " + weather_status_message + humidity_msg
                    send_telegram_message(final_message)
                    send_msg_case_02 += 1

            if weather_status_code == 3:
                if send_msg_case_03 < 1:
                    if send_msg_case_03 == 0:
                        send_telegram_message(message)
                        custom_messages = ["\U0001F9E3  O clima esfriou, não esqueça o casaco"]
                        final_custom_message = ""
                        for msg in custom_messages:
                            final_custom_message += msg + "\n"
                        send_telegram_message(final_custom_message)
                    final_message = "\U00002744  " + weather_status_message + humidity_msg
                    send_telegram_message(final_message)
                    send_msg_case_03 += 1

            time_to_sleep = 10
        else:
            led_pin.off()  # Apaga o LED
            send_msg_case_01 = 0
            send_msg_case_02 = 0
            send_msg_case_03 = 0
            time_to_sleep = 5

        utime.sleep(time_to_sleep)  # Intervalo entre as leituras
    client.disconnect()

# Execução do programa principal
main()
