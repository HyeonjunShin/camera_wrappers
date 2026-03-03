import zenoh
import time

# 1. Zenoh 세션 열기
conf = zenoh.Config()
session = zenoh.open(conf)

# 2. 데이터를 보낼 키 설정
key = "demo/example/test"
data = "Hello, Zenoh from Python!"

print(f"Publishing data on {key}...")

try:
    while True:
        # 3. 데이터 게시 (put)
        session.put(key, data)
        print(f"Sent: {data}")
        time.sleep(1)
except KeyboardInterrupt:
    pass

# 4. 세션 종료
session.close()
