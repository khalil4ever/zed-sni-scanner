import asyncio
import socket
import ssl
import time
from urllib.parse import urlparse

TIMEOUT = 6


async def _dns(hostname):
    try:
        infos = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: socket.getaddrinfo(
                hostname,
                443,
                type=socket.SOCK_STREAM
            )
        )
        return bool(infos)
    except Exception:
        return False


async def _tls(hostname):
    def check():
        context = ssl.create_default_context()

        with socket.create_connection(
            (hostname, 443),
            timeout=TIMEOUT
        ) as sock:
            with context.wrap_socket(
                sock,
                server_hostname=hostname
            ) as tls_sock:
                return tls_sock.version() is not None

    try:
        await asyncio.get_running_loop().run_in_executor(
            None,
            check
        )
        return True
    except Exception:
        return False


async def _https(hostname):
    def check():
        import http.client

        started = time.perf_counter()

        conn = http.client.HTTPSConnection(
            hostname,
            443,
            timeout=TIMEOUT
        )

        try:
            conn.request(
                "HEAD",
                "/",
                headers={
                    "User-Agent": "Zed-SNI-Scanner/1.0"
                }
            )

            response = conn.getresponse()

            latency = round(
                (time.perf_counter() - started) * 1000
            )

            return response.status < 600, latency

        finally:
            conn.close()

    try:
        return await asyncio.get_running_loop().run_in_executor(
            None,
            check
        )
    except Exception:
        return False, None


async def test_hostname(hostname: str):
    hostname = hostname.strip().lower()

    if "://" in hostname:
        hostname = urlparse(hostname).hostname or hostname

    dns_ok = await _dns(hostname)

    tcp_ok = False
    tls_ok = False

    if dns_ok:
        try:
            await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: socket.create_connection(
                    (hostname, 443),
                    timeout=TIMEOUT
                ).close()
            )
            tcp_ok = True
        except Exception:
            tcp_ok = False

    if tcp_ok:
        tls_ok = await _tls(hostname)

    https_ok = False
    latency = None

    if tls_ok:
        https_ok, latency = await _https(hostname)

    if https_ok:
        status = "ACTIVE"
        detail = "TLS and HTTPS connectivity succeeded."
    elif tls_ok:
        status = "UNSTABLE"
        detail = "TLS succeeded but HTTPS did not complete normally."
    else:
        status = "DEAD"
        detail = "The hostname did not pass the required connectivity checks."

    return {
        "hostname": hostname,
        "dns": dns_ok,
        "tcp": tcp_ok,
        "tls": tls_ok,
        "https": https_ok,
        "latency_ms": latency if latency is not None else "N/A",
        "status": status,
        "detail": detail,
    }
