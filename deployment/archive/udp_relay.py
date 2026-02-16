#!/usr/bin/env python3
"""
Transparent bidirectional UDP relay using select() for reliability.

Usage:
    python3 udp_relay.py <listen_port> <target_host> <target_port>
"""

import select
import socket
import sys


def log(msg):
    print(msg, flush=True)


def relay(listen_port: int, target_host: str, target_port: int) -> None:
    # Socket for receiving from clients
    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_sock.bind(("0.0.0.0", listen_port))
    listen_sock.setblocking(False)

    # Socket for communicating with target
    target_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    target_sock.setblocking(False)

    target_addr = (target_host, target_port)
    client_addr = None

    log(f"[udp_relay] :{listen_port} <-> {target_host}:{target_port}")

    while True:
        readable, _, _ = select.select([listen_sock, target_sock], [], [], 1.0)

        for sock in readable:
            if sock is listen_sock:
                # Data from client -> forward to target
                data, addr = listen_sock.recvfrom(65535)
                client_addr = addr
                target_sock.sendto(data, target_addr)
                log(f"[>] {len(data)}B from client {addr} -> target")

            elif sock is target_sock:
                # Response from target -> forward back to client
                data, addr = target_sock.recvfrom(65535)
                if client_addr:
                    listen_sock.sendto(data, client_addr)
                    log(f"[<] {len(data)}B from target -> client {client_addr}")
                else:
                    log(f"[!] {len(data)}B from target but no client yet")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <listen_port> <target_host> <target_port>")
        sys.exit(1)
    relay(int(sys.argv[1]), sys.argv[2], int(sys.argv[3]))
