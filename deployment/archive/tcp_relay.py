#!/usr/bin/env python3
"""
Simple TCP relay/proxy for Trossen arm protocol.

Usage:
    python3 tcp_relay.py <listen_port> <target_host> <target_port>
"""

import socket
import sys
import threading


def handle_client(client_sock, target_host, target_port):
    try:
        target_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target_sock.connect((target_host, target_port))

        def forward(src, dst, label):
            try:
                while True:
                    data = src.recv(65535)
                    if not data:
                        break
                    dst.sendall(data)
            except Exception:
                pass
            finally:
                try:
                    src.close()
                except Exception:
                    pass
                try:
                    dst.close()
                except Exception:
                    pass

        t1 = threading.Thread(target=forward, args=(client_sock, target_sock, "c->t"), daemon=True)
        t2 = threading.Thread(target=forward, args=(target_sock, client_sock, "t->c"), daemon=True)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
    except Exception as e:
        print(f"[tcp_relay] Connection error: {e}")
        try:
            client_sock.close()
        except Exception:
            pass


def relay(listen_port, target_host, target_port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", listen_port))
    server.listen(5)
    print(f"[tcp_relay] Listening on TCP :{listen_port} -> {target_host}:{target_port}")

    while True:
        client_sock, addr = server.accept()
        threading.Thread(
            target=handle_client,
            args=(client_sock, target_host, target_port),
            daemon=True,
        ).start()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <listen_port> <target_host> <target_port>")
        sys.exit(1)
    relay(int(sys.argv[1]), sys.argv[2], int(sys.argv[3]))
