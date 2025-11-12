"""
Shared helpers for selecting BrainDrive network ports.

The installer prefers a fixed list of port pairs so non-technical users rarely
have to reason about port conflicts. This module centralizes that list and the
logic for probing availability.
"""

from __future__ import annotations

import socket
from typing import List, Sequence, Tuple, Optional

DEFAULT_PORT_PAIRS: Sequence[Tuple[int, int]] = (
    (8005, 5173),
    (8505, 5573),
    (8605, 5673),
)


def _normalize_probe_host(host: Optional[str]) -> Tuple[str, socket.AddressFamily]:
    """
    Normalize a host string into a concrete probe target and address family.
    """
    probe_host = (host or "").strip()
    if not probe_host or probe_host in {"*", "0.0.0.0", "localhost"}:
        return "127.0.0.1", socket.AF_INET
    cleaned = probe_host.strip("[]")
    if cleaned in {"::", "::1"}:
        return "::1", socket.AF_INET6
    if ":" in cleaned and cleaned.count(":") >= 2 and cleaned.count(".") == 0:
        return cleaned, socket.AF_INET6
    return cleaned, socket.AF_INET


def _can_bind(host: str, family: socket.AddressFamily, port: int) -> bool:
    """
    Attempt to bind to the given host/port to determine availability.
    """
    try:
        sock = socket.socket(family, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if family == socket.AF_INET6:
            sock.bind((host, port, 0, 0))
        else:
            sock.bind((host, port))
        sock.close()
        return True
    except OSError:
        return False


def is_port_available(port: int, host: Optional[str] = None) -> bool:
    """
    Return True when the given port appears to be free on the supplied host.
    """
    probe_host, family = _normalize_probe_host(host)
    if _can_bind(probe_host, family, port):
        return True
    # If IPv6 bind failed for localhost-style host, try IPv4 as a fallback.
    if family == socket.AF_INET6 and probe_host in {"::1"}:
        return _can_bind("127.0.0.1", socket.AF_INET, port)
    return False


def ports_available(
    backend_port: int,
    frontend_port: int,
    backend_host: Optional[str] = None,
    frontend_host: Optional[str] = None,
) -> bool:
    """
    Check whether both backend and frontend ports look available.
    """
    return (
        is_port_available(backend_port, backend_host)
        and is_port_available(frontend_port, frontend_host)
    )


def select_available_port_pair(
    preferred_pairs: Sequence[Tuple[int, int]] = DEFAULT_PORT_PAIRS,
    backend_host: Optional[str] = None,
    frontend_host: Optional[str] = None,
) -> Tuple[int, int]:
    """
    Pick the first preferred port pair whose ports both look available.
    """
    for backend_port, frontend_port in preferred_pairs:
        if ports_available(
            backend_port,
            frontend_port,
            backend_host=backend_host,
            frontend_host=frontend_host,
        ):
            return backend_port, frontend_port
    # No pair looked free; fall back to the first preference.
    return preferred_pairs[0]


def is_managed_port_pair(
    backend_port: int,
    frontend_port: int,
    preferred_pairs: Sequence[Tuple[int, int]] = DEFAULT_PORT_PAIRS,
) -> bool:
    """
    Determine whether a backend/frontend port pair belongs to the managed list.
    """
    return any(
        backend_port == cand_backend and frontend_port == cand_frontend
        for cand_backend, cand_frontend in preferred_pairs
    )


def flatten_backend_ports(
    preferred_pairs: Sequence[Tuple[int, int]] = DEFAULT_PORT_PAIRS,
) -> List[int]:
    return [backend for backend, _ in preferred_pairs]


def flatten_frontend_ports(
    preferred_pairs: Sequence[Tuple[int, int]] = DEFAULT_PORT_PAIRS,
) -> List[int]:
    return [frontend for _, frontend in preferred_pairs]
