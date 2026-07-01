import requests
import time
import os

URL = "https://seu-site.render.com/health"

while True:
    try:
        response = requests.get(URL, timeout=10)
        if response.status_code != 200:
            print(f"⚠️ Health check falhou: {response.status_code}")
        else:
            data = response.json()
            print(f"✅ Servidor OK: {data['resultados_importados']} resultados")
    except Exception as e:
        print(f"❌ Erro no health check: {e}")
    
    time.sleep(300)  # A cada 5 minutos