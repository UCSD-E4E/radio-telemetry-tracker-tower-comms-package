"""Implementation of MeshInterface that simulates a mesh network.

Provides a simulated mesh network for testing and development,
with configurable nodes and network topology.
"""

import logging
from collections.abc import Callable
from typing import Any, ClassVar

from radio_telemetry_tracker_tower_comms_package.mesh_interface import MeshInterface

logger = logging.getLogger(__name__)


class SimulatedMeshInterface(MeshInterface):
    """Implementation of MeshInterface that simulates a mesh network.

    Provides a simulated network environment for testing and development,
    with configurable nodes, network topology, and simulated packet loss.
    Uses in-memory message queues to simulate packet transmission.
    """

    _nodes: ClassVar[dict[int, dict[str, Any]]] = {}
    _ACK_SUCCESS_PERCENT: ClassVar[int] = 80

    def __init__(self, numeric_id: int, user_id: str | None = None) -> None:
        """Initialize simulated mesh interface.

        Args:
            numeric_id: Numeric ID for this node
            user_id: Optional user-friendly ID. Defaults to "node-{numeric_id}"
        """
        super().__init__()
        self.numeric_id = numeric_id
        self.user_id_str = user_id or f"node-{numeric_id}"

        if numeric_id not in SimulatedMeshInterface._nodes:
            SimulatedMeshInterface._nodes[numeric_id] = {
                "user_id": self.user_id_str,
                "inbox": [],
                "neighbors": [],
                "position": {},
            }
        else:
            SimulatedMeshInterface._nodes[numeric_id]["user_id"] = self.user_id_str

        self._packet_callback: Callable[[bytes], None] | None = None

    def connect(self) -> None:
        """Connect to the simulated mesh network."""
        logger.info(
            "Simulated node %d connected as '%s'.",
            self.numeric_id,
            self.user_id_str,
        )

    def close(self) -> None:
        """Disconnect from the simulated mesh network."""
        logger.info("Simulated node %d disconnected.", self.numeric_id)

    def get_numeric_node_id(self) -> int:
        """Get the numeric ID of this node."""
        return self.numeric_id

    def get_user_id(self) -> str:
        """Get the user-friendly ID of this node."""
        return self.user_id_str

    def get_neighbors(self) -> list[int]:
        """Get the list of neighboring nodes."""
        return list(SimulatedMeshInterface._nodes[self.numeric_id]["neighbors"])

    def get_node_position(self) -> dict[str, Any] | None:
        """Get the geographic position of this node."""
        nd = SimulatedMeshInterface._nodes.get(self.numeric_id)
        if not nd:
            return None
        pos = nd.get("position", {})
        if not pos:
            return None
        return {
            "latitude": pos.get("latitude", 0.0),
            "longitude": pos.get("longitude", 0.0),
            "altitude": pos.get("altitude", 0.0),
            "time": pos.get("time", 0),
        }

    def send_message(
        self,
        data: bytes,
        destination: int | None = None,
        *,
        want_ack: bool = False,
    ) -> int | None:
        """Send a message to the specified destination or broadcast if None.

        Args:
            data: The message bytes to send
            destination: Target node ID, or None for broadcast
            want_ack: Whether to request acknowledgment

        Returns:
            Packet ID if sent, None on failure
        """
        packet_id = hash((self.numeric_id, data)) & 0xFFFFFFFF

        node_data = SimulatedMeshInterface._nodes[self.numeric_id]

        if destination is None:
            # broadcast
            for nbr_id in node_data["neighbors"]:
                SimulatedMeshInterface._nodes[nbr_id]["inbox"].append(
                    (data, self.numeric_id),
                )
        elif destination in node_data["neighbors"]:
            SimulatedMeshInterface._nodes[destination]["inbox"].append(
                (data, self.numeric_id),
            )
        else:
            # not a neighbor => ack fail
            if want_ack and self.on_ack_fail:
                self.on_ack_fail(packet_id)
            return packet_id

        # Simulate ack success ~80%
        import secrets

        if want_ack:
            success = secrets.randbelow(100) < self._ACK_SUCCESS_PERCENT
            if success and self.on_ack_success:
                self.on_ack_success(packet_id)
            elif not success and self.on_ack_fail:
                self.on_ack_fail(packet_id)

        return packet_id

    def register_packet_callback(self, callback: Callable[[bytes], None]) -> None:
        """Register a callback for received packets."""
        self._packet_callback = callback

    def poll_inbox(self) -> None:
        """User can call this in a main loop to dispatch messages to the callback."""
        node_data = SimulatedMeshInterface._nodes[self.numeric_id]
        inbox = node_data["inbox"]
        while inbox:
            data, from_id = inbox.pop(0)
            if self._packet_callback:
                self._packet_callback(data)
