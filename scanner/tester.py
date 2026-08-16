import socket
import ssl
import asyncio
import time

async def test_tcp_connection(hostname, port, timeout=3):
    """Tests a TCP connection to a specific port."""
    try:
        loop = asyncio.get_running_loop()
        start = time.time()
        # Uses a thread pool to run blocking socket operations safely
        await loop.run_in_executor(None, lambda: socket.create_connection((hostname, port), timeout))
        latency = round((time.time() - start) * 1000, 2)
        return True, latency
    except Exception:
        return False, None

async def test_tls_sni(hostname, port, timeout=3):
    """Tests if a TLS/SNI handshake succeeds on a specific port."""
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        loop = asyncio.get_running_loop()
        start = time.time()
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        # Connect
        await loop.run_in_executor(None, sock.connect, (hostname, port))
        # Perform TLS Handshake
        ssl_sock = context.wrap_socket(sock, server_hostname=hostname)
        await loop.run_in_executor(None, ssl_sock.do_handshake)
        
        ssl_sock.close()
        latency = round((time.time() - start) * 1000, 2)
        return True, latency
    except Exception:
        return False, None

async def test_hostname(hostname):
    """Standard test (DNS, TCP 443, TLS 443, HTTPS 443). Used for /test and /monitor."""
    dns_ok = True
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: socket.gethostbyname(hostname))
    except:
        dns_ok = False

    tcp_ok, tcp_lat = await test_tcp_connection(hostname, 443)
    tls_ok, tls_lat = await test_tls_sni(hostname, 443)
    https_ok = tcp_ok and tls_ok

    status = "ERROR"
    if dns_ok and tcp_ok and tls_ok and https_ok:
        status = "ACTIVE"
        latency = tls_lat
    elif dns_ok and tcp_ok and not tls_ok:
        status = "UNSTABLE"
        latency = tcp_lat
    elif dns_ok and not tcp_ok:
        status = "DEAD"
        latency = None
    else:
        status = "ERROR"
        latency = None

    return {
        "hostname": hostname,
        "status": status,
        "dns": dns_ok,
        "tcp": tcp_ok,
        "tls": tls_ok,
        "https": https_ok,
        "latency_ms": latency,
    }

async def scan_multiport(hostname, ports=[80, 443, 8080, 8443, 3128]):
    """Scans multiple ports for connectivity and TLS/SNI support."""
    results = []
    for port in ports:
        tcp_ok, tcp_lat = await test_tcp_connection(hostname, port)
        if tcp_ok:
            tls_ok, tls_lat = await test_tls_sni(hostname, port)
            if tls_ok:
                results.append({"port": port, "type": "TLS/SNI", "latency": tls_lat, "active": True})
            else:
                results.append({"port": port, "type": "TCP-Only", "latency": tcp_lat, "active": True})
    return results
