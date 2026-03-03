import zenoh

# 콜백 함수: 데이터가 들어올 때 실행됨
def listener(sample):
    print(f">> Received {sample.kind} ('{sample.key_expr}': '{sample.payload.to_bytes().decode()}')")

# 1. Zenoh 세션 열기
conf = zenoh.Config()
session = zenoh.open(conf)

# 2. 구독 선언 (key 표현식 사용)
key = "demo/example/**"  # **는 하위 모든 경로를 포함하는 와일드카드입니다.
print(f"Declaring Subscriber on {key}...")
sub = session.declare_subscriber(key, listener)

# 3. 대기 (사용자가 중단할 때까지)
try:
    input("Press Ctrl+C to stop...\n")
except KeyboardInterrupt:
    pass

# 4. 자원 해제
sub.undeclare()
session.close()
