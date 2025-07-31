# umqtt/simple.py
import usocket as socket
import ustruct as struct

class MQTTClient:
    def __init__(self, client_id, server):
        self.client_id = client_id
        self.server = server

    def connect(self):
        print("MQTT connect")

    def publish(self, topic, msg):
        print("MQTT publish", topic, msg)
