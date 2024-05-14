from flask import Flask, request, jsonify, render_template
import paho.mqtt.client as mqtt
import json
from datetime import datetime
import os

app = Flask(__name__)

# MQTT 設定
MQTT_BROKER = 'mqtt.geosupply.com.tw'
MQTT_PORT = 1886
MQTT_KEEPALIVE_INTERVAL = 60

client = mqtt.Client()

# 訂閱的 topic 與最後更新時間和消息列表
subscribed_topics = {}

# MQTT 回調函數
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    # 在連接時訂閱已存儲的 topic
    for topic in subscribed_topics:
        client.subscribe(topic)

MAX_MESSAGES = 100

def on_message(client, userdata, msg):
    topic = msg.topic
    message = msg.payload.decode()
    if 'AT+' in message:
        return
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if topic not in subscribed_topics:
        subscribed_topics[topic] = {'last_update': 'Never', 'messages': []}
    subscribed_topics[topic]['last_update'] = timestamp
    subscribed_topics[topic]['messages'].append({'timestamp': timestamp, 'message': message})
    if len(subscribed_topics[topic]['messages']) > MAX_MESSAGES:
        subscribed_topics[topic]['messages'].pop(0)
    # print(f"Message received on topic {topic}: {message}")

    # 儲存消息到對應的 .txt 文件
    filename = f"./data/{topic}.txt"
    with open(filename, 'a') as f:
        f.write(f"{timestamp}: {message}\n")


client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE_INTERVAL)
client.loop_start()

# 初始化時讀取已存儲的 .txt 文件
def initialize_subscriptions():
    files = [f for f in os.listdir('./data') if f.endswith('.txt')]
    for file in files:
        with open(f'./data/{file}', 'r') as f:
            first_line = f.readline().strip()
            if first_line.startswith("Topic: "):
                topic = first_line.split(": ")[1]
                subscribed_topics[topic] = {'last_update': 'Never', 'messages': []}
                client.subscribe(topic)

initialize_subscriptions()

# 儀器序號頁面
@app.route('/')
def index():
    return render_template('index.html', topics=subscribed_topics)

# 新增儀器序號
@app.route('/add', methods=['POST'])
def add_instrument():
    topic = request.form['topic']
    if topic not in subscribed_topics:
        subscribed_topics[topic] = {'last_update': 'Never', 'messages': []}
        client.subscribe(topic)
        # 創建對應的 .txt 文件
        filename = f"./data/{topic}.txt"
        if not os.path.exists(filename):
            with open(filename, 'w') as f:
                f.write(f"Topic: {topic}\n")
    return jsonify(subscribed_topics)

# 獲取消息列表
@app.route('/messages/<topic>', methods=['GET'])
def get_messages(topic):
    page = int(request.args.get('page', 1))
    per_page = 20
    if topic in subscribed_topics:
        messages = subscribed_topics[topic]['messages']
        start = (page - 1) * per_page
        end = start + per_page
        paginated_messages = messages[start:end]
        return jsonify(paginated_messages)
    else:
        return jsonify([])

# 發布消息
@app.route('/publish', methods=['POST'])
def publish_message():
    topic = request.form['topic']
    message = request.form['message']
    client.publish(topic, message)
    return 'Message published'

if __name__ == '__main__':
    app.run(host='0.0.0.0',  port=8080)
