# UDP DNS Resolver - Actividad 2

"""
Author Declaration

Code Author: Lady Esquivel

Acknowledgements:
- Library: dnslib
- Guidance/Assistance: Ivana Bachmann
- Other contributors: Joaquín Acosta
- AI was used for code optimization and debugging, core logic and structure were designed by the author.
"""

import socket
import time
from collections import Counter

from dnslib import DNSRecord, QTYPE

IP_VM = '127.0.0.1'
PORT_VM = 8000
ROOT_DNS = '192.33.4.12'
DNS_PORT = 53
BUFFER_SIZE = 4096
TTL_CACHE = 60

historial_consultas: list[str] = []
cache_datos: dict[str, dict] = {}


def parsear_dns(datos: bytes) -> DNSRecord | None:
    # Parse raw UDP payload into a DNS object; return None on malformed packets.
    try:
        return DNSRecord.parse(datos)
    except Exception as e:
        print(f"Error al parsear mensaje: {e}")
        return None


def obtener_tops() -> list[str]:
    # Keep only recent traffic to prioritize hot domains in cache decisions.
    conteo = Counter(historial_consultas[-20:])
    return [dominio for dominio, _ in conteo.most_common(3)]


def enviar_consulta(mensaje: bytes, ip: str) -> tuple[bytes, DNSRecord] | None:
    # One-shot UDP query to an upstream DNS server with a short timeout.
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3)
    try:
        sock.sendto(mensaje, (ip, DNS_PORT))
        respuesta_bytes, _ = sock.recvfrom(BUFFER_SIZE)
        return respuesta_bytes, DNSRecord.parse(respuesta_bytes)
    except Exception:
        return None
    finally:
        sock.close()


def resolver(mensaje_consulta: bytes, ip_objetivo: str = ROOT_DNS, ns_nombre: str = '.') -> bytes | None:
    # Iterative-style resolver: query target NS, then follow delegations until an A answer.
    query_obj = DNSRecord.parse(mensaje_consulta)
    qname = str(query_obj.q.qname)

    print(f"(debug) Consultando '{qname}' a '{ns_nombre}' con dirección IP '{ip_objetivo}'")

    # Step A: send query to current target name server.
    resultado = enviar_consulta(mensaje_consulta, ip_objetivo)
    if resultado is None:
        return None
    respuesta_bytes, res_obj = resultado

    # Step B: if the answer section already has an A record, resolution is complete.
    for record in res_obj.rr:
        if record.rtype == QTYPE.A:
            return respuesta_bytes

    # Step C: follow delegation NS records from the authority section.
    ns_records = [r for r in res_obj.auth if r.rtype == QTYPE.NS]
    if not ns_records:
        return None

    # Step C.1: prefer glue A records from additional to avoid extra lookups.
    for add_record in res_obj.ar:
        if add_record.rtype == QTYPE.A:
            return resolver(mensaje_consulta, str(add_record.rdata), str(add_record.rname))

    # Step C.2: without glue, resolve NS hostname first, then retry original query.
    for ns_record in ns_records:
        ns_domain = str(ns_record.rdata)
        ns_query = DNSRecord.question(ns_domain)
        ns_res_bytes = resolver(ns_query.pack())

        if ns_res_bytes:
            ns_res_obj = DNSRecord.parse(ns_res_bytes)
            for rr in ns_res_obj.rr:
                if rr.rtype == QTYPE.A:
                    return resolver(mensaje_consulta, str(rr.rdata), ns_domain)

    return None


def main() -> None:
    # Local DNS server endpoint that receives client queries.
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_sock.bind((IP_VM, PORT_VM))
    print(f"Resolver escuchando en {IP_VM}:{PORT_VM}...")

    while True:
        datos_cliente, addr = server_sock.recvfrom(BUFFER_SIZE)

        consulta_obj = parsear_dns(datos_cliente)
        if not consulta_obj:
            continue

        qname = str(consulta_obj.q.qname)
        historial_consultas.append(qname)

        tops = obtener_tops()
        respuesta_final = None
        ahora = time.time()

        # Cache policy: only cache domains that are currently among the hottest queries.
        if qname in tops and qname in cache_datos:
            info = cache_datos[qname]
            if ahora - info['timestamp'] < TTL_CACHE:
                print(f"(debug) [CACHE] Respondiendo '{qname}' desde memoria.")
                respuesta_final = info['datos']
            else:
                # Expired entry: refresh from upstream and replace cached value.
                print(f"(debug) [CACHE] Registro para '{qname}' expirado. Refrescando...")
                respuesta_final = resolver(datos_cliente)
                if respuesta_final:
                    cache_datos[qname] = {'datos': respuesta_final, 'timestamp': ahora}
        else:
            # Miss or non-top domain: resolve normally.
            respuesta_final = resolver(datos_cliente)
            if respuesta_final and qname in tops:
                # Only promote to cache when domain is currently frequent.
                cache_datos[qname] = {'datos': respuesta_final, 'timestamp': ahora}

        if respuesta_final:
            resp_final_obj = DNSRecord.parse(respuesta_final)
            # Keep client transaction ID so requester can match reply to query.
            resp_final_obj.header.id = consulta_obj.header.id
            server_sock.sendto(resp_final_obj.pack(), addr)


if __name__ == "__main__":
    main()