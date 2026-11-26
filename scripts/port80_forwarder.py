"""
Lightweight TCP Forwarder: Port 80 -> Port 8000
Allows users to visit http://kora-live.duckdns.org directly without specifying :8000
"""

import asyncio
import sys

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        target_reader, target_writer = await asyncio.open_connection("127.0.0.1", 8000)
    except Exception:
        writer.close()
        return

    async def pipe(src: asyncio.StreamReader, dst: asyncio.StreamWriter):
        try:
            while True:
                data = await src.read(65536)
                if not data:
                    break
                dst.write(data)
                await dst.drain()
        except Exception:
            pass
        finally:
            try:
                dst.close()
            except Exception:
                pass

    try:
        await asyncio.gather(pipe(reader, target_writer), pipe(target_reader, writer), return_exceptions=True)
    finally:
        try:
            writer.close()
        except Exception:
            pass

async def main():
    server = await asyncio.start_server(handle_client, "0.0.0.0", 80)
    print("[✓] Port 80 Forwarder is listening on 0.0.0.0:80 -> 127.0.0.1:8000", flush=True)
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[*] Forwarder stopped.")
