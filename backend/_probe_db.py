import socket
print("resolve db:", socket.gethostbyname("db"))
s = socket.socket()
s.settimeout(5)
print("connect db:3306 ->", s.connect_ex(("db", 3306)))
s.close()