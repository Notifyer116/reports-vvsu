
import socket
import struct
import sys

HOST = "0.0.0.0"                 # слушаем на всех сетевых интерфейсах
DEFAULT_PORT = 5000
EXIT_COMMAND = "/exit"
HEADER = struct.Struct("!I")     # 4 байта - длина сообщения
MAX_MESSAGE_SIZE = 1024 * 1024   # защита от некорректных заголовков


# ---------- протокол: сообщение = [длина (4 байта)] + [текст в UTF-8] ----------
# TCP - потоковый протокол и не сохраняет границы сообщений,
# поэтому границы задаём сами с помощью префикса длины.

def recv_exact(sock: socket.socket, size: int):
    """Читает ровно size байт. Возвращает None, если соединение закрыто."""
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            return None
        data.extend(chunk)
    return bytes(data)


def send_message(sock: socket.socket, text: str) -> None:
    payload = text.encode("utf-8")
    sock.sendall(HEADER.pack(len(payload)) + payload)


def recv_message(sock: socket.socket):
    """Возвращает текст сообщения или None, если собеседник закрыл соединение."""
    header = recv_exact(sock, HEADER.size)
    if header is None:
        return None
    (length,) = HEADER.unpack(header)
    if length > MAX_MESSAGE_SIZE:
        raise ValueError("Слишком большое сообщение")
    payload = recv_exact(sock, length)
    if payload is None:
        return None
    return payload.decode("utf-8", errors="replace")


# ---------- вспомогательные функции ----------

def ask(prompt: str) -> str:
    """Запрашивает непустую строку у пользователя. Ctrl+D/Ctrl+Z = выход."""
    while True:
        try:
            text = input(prompt).strip()
        except EOFError:
            return EXIT_COMMAND
        if text:
            return text


def local_ip() -> str:
    """Определяет IP-адрес сервера в локальной сети (пакеты при этом не отправляются)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


# ---------- обслуживание клиента ----------

def serve_client(conn: socket.socket, addr) -> None:
    peer = f"{addr[0]}:{addr[1]}"          # идентификатор клиента: IP:порт
    print(f"\n[+] Подключился клиент {peer}")
    print(f"    Ожидание сообщения от клиента... (для завершения введите {EXIT_COMMAND} вместо ответа)")
    try:
        while True:
            # 1) принимаем сообщение от клиента
            message = recv_message(conn)
            if message is None:
                print(f"[-] Клиент {peer} завершил соединение")
                return
            # 2) выводим его пользователю вместе с идентификатором отправителя
            print(f"[{peer}] {message}")

            # 3) предоставляем пользователю возможность ответить
            reply = ask("Ваш ответ: ")
            if reply == EXIT_COMMAND:
                print("[-] Обмен сообщениями завершён по инициативе сервера")
                return
            send_message(conn, reply)
            print("    Ожидание сообщения от клиента...")
    except (ConnectionError, ValueError) as e:
        print(f"[!] Ошибка соединения с {peer}: {e}")
    finally:
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        conn.close()


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, port))
        server.listen(1)
        print(f"Сервер запущен. Адрес для подключения: {local_ip()}:{port}")
        print("Остановка сервера: Ctrl+C")

        try:
            while True:
                conn, addr = server.accept()   # ждём подключения клиента
                serve_client(conn, addr)
                print("\nОжидание нового подключения...")
        except KeyboardInterrupt:
            print("\nСервер остановлен")


if __name__ == "__main__":
    main()
