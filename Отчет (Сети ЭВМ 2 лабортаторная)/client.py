"""
Лабораторная работа №2. Сетевое взаимодействие на протоколе TCP.
КЛИЕНТ. Используются потоковые сокеты (SOCK_STREAM) протокола TCP.

Запуск:  python client.py
Адрес сервера вводится пользователем перед подключением.
Завершить обмен со стороны клиента: ввести /exit вместо сообщения.
"""
import socket
import struct

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000
EXIT_COMMAND = "/exit"
HEADER = struct.Struct("!I")     # 4 байта - длина сообщения
MAX_MESSAGE_SIZE = 1024 * 1024


# ---------- протокол: сообщение = [длина (4 байта)] + [текст в UTF-8] ----------

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


def parse_address(text: str):
    """'host', 'host:port' или пустая строка -> (host, port)."""
    if not text:
        return DEFAULT_HOST, DEFAULT_PORT
    if ":" in text:
        host, port = text.rsplit(":", 1)
        return (host or DEFAULT_HOST), int(port)
    return text, DEFAULT_PORT


def connect_to_server() -> socket.socket:
    """Запрашивает адрес сервера у пользователя и подключается к нему."""
    while True:
        try:
            text = input(f"Введите адрес сервера [host[:port]], Enter = {DEFAULT_HOST}:{DEFAULT_PORT}: ").strip()
            host, port = parse_address(text)
        except ValueError:
            print("Некорректный порт, попробуйте ещё раз.")
            continue
        try:
            sock = socket.create_connection((host, port), timeout=10)
            sock.settimeout(None)   # дальше ждём сообщения без тайм-аута
            return sock
        except OSError as e:
            print(f"Не удалось подключиться к {host}:{port}: {e}")


def main() -> None:
    try:
        sock = connect_to_server()
    except (KeyboardInterrupt, EOFError):
        print("\nОтмена")
        return

    server_ip, server_port = sock.getpeername()[:2]
    peer = f"{server_ip}:{server_port}"        # идентификатор сервера: IP:порт
    my_ip, my_port = sock.getsockname()[:2]
    print(f"Соединение установлено: {my_ip}:{my_port} -> {peer}")
    print(f"Для завершения введите {EXIT_COMMAND}")

    try:
        while True:
            # 1) после установки соединения клиент отправляет сообщение серверу
            message = ask("Ваше сообщение: ")
            if message == EXIT_COMMAND:
                print("[-] Обмен сообщениями завершён по инициативе клиента")
                break
            send_message(sock, message)

            # 2) ждём ответ сервера (сообщения передаются попеременно)
            print("    Ожидание ответа сервера...")
            reply = recv_message(sock)
            if reply is None:
                print(f"[-] Сервер {peer} завершил соединение")
                break
            # 3) выводим ответ вместе с идентификатором отправителя
            print(f"[{peer}] {reply}")
    except (ConnectionError, ValueError) as e:
        print(f"[!] Ошибка соединения: {e}")
    except KeyboardInterrupt:
        print("\n[-] Прервано пользователем")
    finally:
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        sock.close()


if __name__ == "__main__":
    main()
