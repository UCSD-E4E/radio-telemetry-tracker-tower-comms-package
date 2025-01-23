"""Implementation of MeshInterface using Meshtastic protocol and devices.

Provides mesh networking functionality using Meshtastic-compatible devices
connected via serial interface.
"""

import logging
from collections.abc import Callable
from typing import Any

import meshtastic.serial_interface
from pubsub import pub

from radio_telemetry_tracker_tower_comms_package.mesh_interface import (
    MeshConnectionError,
    MeshInterface,
    SendError,
)

logger = logging.getLogger(__name__)


class MeshtasticMeshInterface(MeshInterface):
    """Implementation of MeshInterface using Meshtastic protocol and devices.

    Handles mesh network communication through Meshtastic-compatible devices
    connected via serial interface, managing packet transmission, reception,
    and acknowledgments.
    """

    def __init__(self, serial_device: str | None = None) -> None:
        """Initialize Meshtastic interface.

        Args:
            serial_device: Optional path to serial device. If None, auto-detect.
        """
        super().__init__()
        self.serial_device = serial_device
        self._interface: meshtastic.serial_interface.SerialInterface | None = None
        self._packet_callback: Callable[[bytes], None] | None = None

    def connect(self) -> None:
        """Connect to the Meshtastic device using serial interface.

        Raises:
            MeshConnectionError: If connection to device fails
        """
        logger.info("Connecting to Meshtastic on %s...", self.serial_device or "AUTO")
        try:
            self._interface = meshtastic.serial_interface.SerialInterface(
                self.serial_device,
            )
        except Exception as exc:
            msg = f"Failed to connect: {exc}"
            raise MeshConnectionError(msg) from exc

        pub.subscribe(self._on_recieve, "meshtastic.recieve")
        logger.info(
            "MeshtasticMeshInterface connected on %s",
            self.serial_device or "AUTO",
        )

    def close(self) -> None:
        """Close the connection to the Meshtastic device and clean up resources."""
        if self._interface:
            try:
                self._interface.close()
            except Exception:
                logger.exception("Error closing Meshtastic interface.")
            self._interface = None
            pub.unsubscribe(self._on_recieve, "meshtastic.recieve")
            logger.info("MeshtasticMeshInterface disconnected")

    def get_numeric_node_id(self) -> int | None:
        """Get this node's numeric ID from the Meshtastic device.

        Returns:
            Node ID if available, None if not connected or ID not found
        """
        if not self._interface:
            return None
        info = self._interface.getMyNodeInfo()
        return info.get("num") if info else None

    def get_user_id(self) -> str:
        """Get this node's user-friendly ID from the Meshtastic device.

        Returns:
            User ID if available, "UNKNOWN" if not connected or ID not found
        """
        if not self._interface:
            return "UNKNOWN"
        me = self._interface.getMyUser()
        if not me:
            return "UNKNOWN"
        return me.get("id", "UNKNOWN")

    def get_neighbors(self) -> list[int]:
        """Get list of neighboring node IDs from the Meshtastic device.

        Returns:
            List of numeric node IDs for all neighbors in the mesh network
        """
        if not self._interface:
            return []
        my_num = self.get_numeric_node_id()
        return [node_num for node_num in self._interface.nodes if node_num != my_num]

    def get_node_position(self) -> dict[str, Any] | None:
        """Get the geographic position of this node in the mesh network.

        Returns:
            Dictionary containing position data (lat, lon, alt, time) if available,
            None if position is not available
        """
        if not self._interface:
            return None

        info = self._interface.getMyNodeInfo()
        if info and "position" in info:
            return {
                "latitude": info["position"].get("latitude", 0.0),
                "longitude": info["position"].get("longitude", 0.0),
                "altitude": info["position"].get("altitude", 0.0),
                "time": info["position"].get("time", 0),
            }
        return None

    def send_message(
        self,
        data: bytes,
        destination: int | None = None,
        *,
        want_ack: bool = False,
    ) -> int | None:
        """Send a message through the Meshtastic device.

        Args:
            data: Message bytes to send
            destination: Target node ID, or None for broadcast
            want_ack: Whether to request acknowledgment

        Returns:
            Packet ID if sent, None on failure

        Raises:
            SendError: If sending fails or no interface is connected
        """
        if not self._interface:
            msg = "No Meshtastic interface; cannot send."
            raise SendError(msg)

        dest_id = "^all" if destination is None else str(destination)

        def on_resp_cb(resp_packet: dict[str, Any]) -> None:
            try:
                pkt_id = resp_packet.get("id")
                result = resp_packet.get("result")  # "ACK", "NACK", etc.
                if result == "ACK" and self.on_ack_success:
                    self.on_ack_success(pkt_id)
                elif result == "NACK" and self.on_ack_failure:
                    self.on_ack_failure(pkt_id)
            except Exception:
                logger.exception("Error in Meshtastic onResponse callback:")

        try:
            pkt = self._interface.sendData(
                data,
                destinationId=dest_id,
                portNum=self.MESH_PORT_NUM,
                wantAck=want_ack,
                wantResponse=False,
                onResponse=on_resp_cb,
                onResponseAckPermitted=True,
            )
            if pkt:
                return pkt.id
        except Exception as exc:
            msg = f"Failed to send data: {exc}"
            raise SendError(msg) from exc
        return None

    def register_packet_callback(self, callback: Callable[[bytes], None]) -> None:
        """Register a callback for received packets.

        Args:
            callback: Function to call when a packet is received
        """
        self._packet_callback = callback

    def _on_recieve(self, packet: dict[str, Any]) -> None:
        try:
            decoded = packet.get("decoded", {})
            portnum = decoded.get("portnum")
            if portnum == self.MESH_PORT_NUM and self._packet_callback:
                payload = decoded.get("payload")
                if payload:
                    self._packet_callback(payload)
        except Exception:
            logger.exception("Error in _on_recieve meshtastic callback.")
