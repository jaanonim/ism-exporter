import json
import os
import time

import requests
import socketio
from dotenv import load_dotenv
from prometheus_client import Enum, Gauge, start_http_server

load_dotenv() 

sio = socketio.Client()

class AppMetrics:
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(AppMetrics, cls).__new__(cls)
            cls.instance.init()
        return cls.instance

    def init(self, ):
        self.url= os.getenv("URL", "http://localhost:5000") 
        self.polling_interval_seconds = int(os.getenv("PULL_INTERVAL", "30"))
        self.username = os.getenv("USERNAME")
        self.password = os.getenv("PASSWORD")
        self.name = os.getenv("NAME","ISMP")
        self.token = None

        # Prometheus metrics to collect
        self.temp_in = Gauge("temp_in", "Temperature outside")
        self.temp_out = Gauge("temp_out", "Temperature inside")
        self.voltage = Gauge("voltage", "Voltage")
        self.connected = Enum("connection", "Connection", states=["connected", "disconnected"])
        self.health = Enum("health", "Health", states=["ok", "error"])


    def run_metrics_loop(self):
        while True:
            self.fetch()
            time.sleep(self.polling_interval_seconds)

    def fetch(self):    
        if self.token is None:
            self.token = self.get_access_token()

        if not sio.connected:
            try:
                sio.connect(self.url, auth={"token": self.token})
            except: pass

        if not sio.connected:
            self.connected.state("disconnected")
            self.token = None
            return
        
        self.connected.state("connected")
        sio.emit("get", { "name": self.name })
        sio.sleep(2)

    def register_data(self,data):
        self.temp_in.set(data["Temp_in"])
        self.temp_out.set(data["Temp_out"])
        self.voltage.set(data["Voltage"])

    def get_access_token(self):
        try:
            r = requests.post(f"{self.url}/auth",
                data=json.dumps({
                    "username": self.username,
                    "password": self.password
                }),
                headers={"Content-Type": "application/json"})
            r.raise_for_status()
            data = r.json()
            print("[OK] Token acquired")
            return data["access_token"]
        except Exception as e:
            self.connected.state("disconnected")
            print("[ERROR] Cannot get token")
            print(e)
            return None
         


@sio.on('dis')
def dis():
    print("[ERROR] Invalid access token")
    AppMetrics().token = None

@sio.on('get')
def get(data):
    d = data["payload"].get("data")
    if(d is None):
        print("[OK] Got new error")
        AppMetrics().health.state("error")
        e = data["payload"].get("error")
        if e is not None:
            print(f"\t{e}")

    else:
        print("[OK] Got new data")
        AppMetrics().health.state("ok")
        AppMetrics().register_data(data["payload"]["data"])



start_http_server(int(os.getenv("PORT", "5950")))
AppMetrics().run_metrics_loop()
