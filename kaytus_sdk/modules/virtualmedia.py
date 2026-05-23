"""Virtual Media streaming over Kaytus VMM WebSocket protocol.

Usage:
    with KaytusClient("192.168.40.100", "admin", "password") as bmc:
        # Set boot source, reboot, and stream ISO (blocks until BMC disconnects)
        bmc.virtualmedia.boot_cd("/path/to/image.iso")

    # Or step-by-step:
    with KaytusClient(...) as bmc:
        bmc.virtualmedia.set_boot_cd()
        bmc.system.force_reboot()
        bmc.virtualmedia.stream("/path/to/image.iso")

Requires: websockets>=14  (pip install websockets)
"""
from __future__ import annotations

import asyncio
import logging
import os
import ssl
import struct
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import KaytusClient

log = logging.getLogger(__name__)

# ── VMM protocol constants ────────────────────────────────────────────────────
_MAGIC    = 19523   # 0x4C43 little-endian header magic
_HDR_SIZE = 10

_PKT_CONNECT    = 80
_PKT_AUTH       = 81
_PKT_AUTH_ACK   = 82
_PKT_KEEPALIVE  = 83
_PKT_KA_RES     = 84
_PKT_INFO       = 85
_PKT_DISCONNECT = 86
_PKT_DATA_REQ   = 88
_PKT_DATA_RES   = 89

_VMEDIA_READ  = 0xF1   # 241
_VMEDIA_CD    = 1
_CLIENT_H5KVM = 2
_CD_BLOCK     = 2048
_FNAME_LEN    = 128
_INFO_BODY    = 13 + _FNAME_LEN   # 141 bytes


def _hdr(pkt_type: int, body_len: int) -> bytes:
    return struct.pack("<HBBHI", _MAGIC, pkt_type, 0, 0, body_len)


def _pkt_info(iso_path: str) -> bytes:
    size         = os.path.getsize(iso_path)
    total_blocks = (size + _CD_BLOCK - 1) // _CD_BLOCK
    fname        = os.path.basename(iso_path).encode("UTF-8")[:_FNAME_LEN]
    body  = struct.pack("B",  _CLIENT_H5KVM)
    body += struct.pack("B",  _VMEDIA_CD)
    body += struct.pack("<H", _CD_BLOCK)
    body += struct.pack("<I", total_blocks)
    body += struct.pack("<I", 0)           # reserved
    body += struct.pack("B",  0)           # read-only flag
    body += fname.ljust(_FNAME_LEN, b"\x00")
    return _hdr(_PKT_INFO, _INFO_BODY) + body


def _pkt_keepalive_res() -> bytes:
    return _hdr(_PKT_KA_RES, 0)


def _pkt_data_response(data: bytes) -> bytes:
    body  = struct.pack("<H", _VMEDIA_READ)
    body += struct.pack("<I", len(data))
    return _hdr(_PKT_DATA_RES, len(body) + len(data)) + body + data


class _MsgParser:
    """Reassembles fragmented WebSocket binary frames into VMM packets."""

    def __init__(self):
        self._buf = b""
        self._hdr = None

    def feed(self, data: bytes):
        self._buf += data
        pkts = []
        while True:
            if self._hdr is None:
                if len(self._buf) < _HDR_SIZE:
                    break
                magic, pkt_type, _, _, length = struct.unpack_from("<HBBHI", self._buf)
                if magic != _MAGIC:
                    log.warning("VMM: bad magic %#x, skipping 1 byte", magic)
                    self._buf = self._buf[1:]
                    continue
                self._hdr = (pkt_type, length)
                self._buf = self._buf[_HDR_SIZE:]
            pkt_type, length = self._hdr
            if len(self._buf) < length:
                break
            pkts.append((pkt_type, self._buf[:length]))
            self._buf = self._buf[length:]
            self._hdr = None
        return pkts


async def _vmm_stream(host: str, token: str, iso_path: str) -> None:
    """Async VMM protocol loop — runs until BMC disconnects."""
    try:
        import websockets
    except ImportError as exc:
        raise ImportError(
            "Virtual media streaming requires websockets. "
            "Install it with: pip install 'websockets>=14'"
        ) from exc

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode    = ssl.CERT_NONE

    iso_size     = os.path.getsize(iso_path)
    total_blocks = (iso_size + _CD_BLOCK - 1) // _CD_BLOCK
    parser       = _MsgParser()
    blocks_sent  = 0

    log.info("VMM: ISO=%s  %.2f GB  %d blocks", iso_path, iso_size / 1024 ** 3, total_blocks)

    async with websockets.connect(
        f"wss://{host}/vm/image",
        ssl=ssl_ctx,
        additional_headers={"X-Auth-Token": token},
        open_timeout=20,
        max_size=None,
        ping_interval=30,
        ping_timeout=15,
    ) as ws:

        log.info("VMM: WebSocket connected to %s", host)

        with open(iso_path, "rb") as iso_file:

            async def send(pkt: bytes):
                await ws.send(pkt)

            while True:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=60)
                except asyncio.TimeoutError:
                    await send(_pkt_keepalive_res())
                    continue
                except websockets.exceptions.ConnectionClosed as exc:
                    log.info("VMM: connection closed — %s", exc)
                    break

                for pkt_type, body in parser.feed(raw):
                    if pkt_type == _PKT_CONNECT:
                        # The X-Auth-Token in the WebSocket upgrade headers
                        # pre-authenticates the connection through NGINX.
                        # Sending VMM binary auth returns ILLEGAL in this mode;
                        # go straight to media-info.
                        log.info("VMM: CONNECT received → sending media info")
                        await send(_pkt_info(iso_path))

                    elif pkt_type == _PKT_AUTH_ACK:
                        status = struct.unpack_from("B", body)[0] if body else 255
                        if status == 0:
                            log.info("VMM: AUTH ACK success → sending media info")
                            await send(_pkt_info(iso_path))
                        else:
                            log.error("VMM: AUTH ACK failed status=%d", status)
                            return

                    elif pkt_type == _PKT_INFO:
                        log.info("VMM: media info accepted by BMC")

                    elif pkt_type == _PKT_KEEPALIVE:
                        await send(_pkt_keepalive_res())

                    elif pkt_type == _PKT_DATA_REQ:
                        op, lba, count, _ = struct.unpack_from("<HIII", body)
                        if op == _VMEDIA_READ:
                            offset = lba * _CD_BLOCK
                            size   = count * _CD_BLOCK
                            iso_file.seek(offset)
                            chunk  = iso_file.read(size)
                            if len(chunk) < size:
                                chunk += b"\x00" * (size - len(chunk))
                            await send(_pkt_data_response(chunk))
                            blocks_sent += count
                            log.debug("VMM: lba=%d count=%d → %dB (total=%d blocks)",
                                      lba, count, len(chunk), blocks_sent)

                    elif pkt_type == _PKT_DISCONNECT:
                        reason = struct.unpack_from("B", body)[0] if body else 0
                        log.info("VMM: session closed by BMC (reason=%d), "
                                 "served %d blocks", reason, blocks_sent)
                        return

                    else:
                        log.debug("VMM: unknown pkt type=%d body=%dB", pkt_type, len(body))


class VirtualMediaModule:
    """Virtual media streaming via Kaytus VMM WebSocket protocol.

    Requires the ``websockets`` package (``pip install 'websockets>=14'``).
    """

    def __init__(self, client: "KaytusClient"):
        self._c = client

    # ── Public API ────────────────────────────────────────────────────────────

    def set_boot_cd(self, *, enabled: str = "Once", mode: str = "UEFI") -> None:
        """Set boot source override to CD-ROM.

        Args:
            enabled: ``"Once"`` (default) or ``"Continuous"``
            mode:    ``"UEFI"`` (default) or ``"Legacy"``
        """
        self._c.patch_with_etag("/redfish/v1/Systems/1", {
            "Boot": {
                "BootSourceOverrideTarget":  "Cd",
                "BootSourceOverrideEnabled": enabled,
                "BootSourceOverrideMode":    mode,
            }
        })

    def stream(self, iso_path: str) -> None:
        """Stream an ISO file to the BMC via the VMM WebSocket protocol.

        Blocks the calling thread until the BMC closes the session (boot
        complete or media ejected) or a ``KeyboardInterrupt`` is raised.

        The server must already be booting from virtual media — call
        :meth:`set_boot_cd` and :meth:`~kaytus_sdk.modules.system.SystemModule.force_reboot`
        (or :meth:`boot_cd`) before this method.

        Args:
            iso_path: Local path to the ISO file to serve.

        Raises:
            FileNotFoundError: If ``iso_path`` does not exist.
            ImportError: If ``websockets`` is not installed.
        """
        if not os.path.exists(iso_path):
            raise FileNotFoundError(f"ISO not found: {iso_path}")
        token = self._c._session.headers.get("X-Auth-Token", "")
        if not token:
            raise RuntimeError("No X-Auth-Token in session — re-login required")
        asyncio.run(_vmm_stream(self._c.host, token, iso_path))

    def boot_cd(
        self,
        iso_path: str,
        *,
        boot_mode: str = "UEFI",
        reboot: bool = True,
        graceful: bool = False,
    ) -> None:
        """One-shot: set boot CD, optionally reboot, then stream the ISO.

        Args:
            iso_path:   Local path to the ISO file.
            boot_mode:  ``"UEFI"`` (default) or ``"Legacy"``.
            reboot:     If ``True`` (default), trigger a server reboot first.
            graceful:   If ``True``, use GracefulRestart instead of ForceRestart.
        """
        self.set_boot_cd(mode=boot_mode)
        if reboot:
            if graceful:
                self._c.system.reboot()
            else:
                self._c.system.force_reboot()
            log.info("VMM: reboot triggered, starting ISO stream...")
        self.stream(iso_path)
