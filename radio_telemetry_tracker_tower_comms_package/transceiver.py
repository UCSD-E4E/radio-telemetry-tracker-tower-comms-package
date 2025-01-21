"""Module for handling mesh network packet transmission and reception."""

from __future__ import annotations

import logging
import queue
import threading
import time
from typing import TYPE_CHECKING

from radio_telemetry_tracker_tower_comms_package.proto import MeshPacket

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from collections.abc import Callable

    from radio_telemetry_tracker_tower_comms_package.interfaces import MeshInterface

class Transceiver:
    """Manages mesh network packet transmission and reception."""

    def __init__(
        self,
        mesh_interface: MeshInterface,
        on_ack_success: Callable[[int], None] | None = None,
        on_ack_fail: Callable[[int], None] | None = None,
    ) -> None:
        """Initialize the Transceiver.

        Args:
            mesh_interface: Interface for mesh network communication
            on_ack_success: Optional callback when packet acknowledgment succeeds
            on_ack_fail: Optional callback when packet acknowledgment fails
        """
        self.mesh_interface = mesh_interface
        self.mesh_interface.on_ack_success = on_ack_success
        self.mesh_interface.on_ack_fail = on_ack_fail

        self.send_queue: queue.Queue[tuple[int | None, bytes]] = queue.Queue()
        self._next_packet_id = 1

        # Thread control
        self._stop_event = threading.Event()
        self._send_thread = threading.Thread(target=self._send_loop, daemon=True)
        self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)

    def start(self) -> None:
        """Start send/receive threads and connect the mesh interface."""
        self.mesh_interface.connect()
        self._stop_event.clear()
        self._send_thread.start()
        self._recv_thread.start()
        logger.info("Transceiver started with node ID: %s", self.mesh_interface.get_user_id())

    def stop(self) -> None:
        """Stop send/receive threads and close the mesh interface."""
        self._stop_event.set()
        self._send_thread.join(timeout=2)
        self._recv_thread.join(timeout=2)
        self.mesh_interface.close()
        logger.info("Transceiver stopped")

    def get_node_id(self) -> int | None:
        """Get this node's numeric ID."""
        return self.mesh_interface.get_numeric_node_id()

    def get_user_id(self) -> str:
        """Get this node's user-friendly ID."""
        return self.mesh_interface.get_user_id()

    def get_node_user_id(self, node_id: int) -> str | None:
        """Get a specific node's user-friendly ID.

        Args:
            node_id: The numeric ID of the node to get the user ID for.

        Returns:
            The user-friendly ID of the node if it exists in the mesh network,
            None if the node is not found or not connected.
        """
        return self.mesh_interface.get_node_user_id(node_id)

    def get_neighbors(self) -> list[int]:
        """Get list of neighboring node IDs."""
        return self.mesh_interface.get_neighbors()

    def enqueue_packet(self, packet: MeshPacket, destination: int | None = None) -> None:
        """Enqueue a packet for transmission.

        Args:
            packet: The Packet protobuf message to send
            destination: Optional destination node ID. If None, broadcast to all neighbors.
        """
        data = packet.SerializeToString()
        self.send_queue.put((destination, data))

    def _send_loop(self) -> None:
        """Fetch packets from the queue and send them."""
        while not self._stop_event.is_set():
            try:
                destination, data = self.send_queue.get(timeout=0.1)
                want_ack = destination is not None  # Only request acks for unicast
                self.mesh_interface.send_message(data, destination, want_ack=want_ack)
            except queue.Empty:
                continue
            except Exception:
                logger.exception("Error sending packet")

    def _recv_loop(self) -> None:
        """Continuously attempt to receive packets and handle them."""
        while not self._stop_event.is_set():
            try:
                data = self.mesh_interface.receive_message()
                if data is not None:
                    self._handle_incoming_packet(data)
            except Exception:
                logger.exception("Error receiving packet")

    def _handle_incoming_packet(self, data: bytes) -> None:
        """Process incoming packet data.

        Args:
            data: Raw packet bytes
        """
        try:
            packet = MeshPacket()
            packet.ParseFromString(data)
            self.on_packet_received(packet)
        except Exception:
            logger.exception("Error handling incoming packet")

    def on_packet_received(self, packet: MeshPacket) -> None:
        """Hook for subclasses to handle received packets.

        Args:
            packet: The received Packet protobuf message
        """

    def current_timestamp_us() -> int:
        """Get the current timestamp in microseconds since the Unix epoch."""
        return int(time.time() * 1_000_000)
