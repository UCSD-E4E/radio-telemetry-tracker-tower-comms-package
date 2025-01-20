"""Interfaces for mesh network communication in the Radio Telemetry Tracker system."""

import abc
import logging
import queue
import threading
import time
from typing import TYPE_CHECKING, ClassVar

import meshtastic
from meshtastic.serial_interface import SerialInterface as UnderlyingMesh

if TYPE_CHECKING:
    from collections.abc import Callable


logger = logging.getLogger(__name__)


class MeshInterface(abc.ABC):
    """Abstract base class defining the interface for mesh network communication.

    This interface provides a common API for different mesh networking implementations,
    supporting both real hardware (Meshtastic) and simulated networks.
    """

    MESH_PORT_NUM = 42

    def __init__(self) -> None:
        """Initialize the mesh interface."""
        self._ack_callback: Callable[[int, bool], None] | None = None
        self._ack_results: dict[int, bool | None] = {}

    @abc.abstractmethod
    def connect(self) -> None:
        """Establish connection to the mesh network."""

    @abc.abstractmethod
    def close(self) -> None:
        """Close the connection to the mesh network."""

    @abc.abstractmethod
    def get_numeric_node_id(self) -> int | None:
        """Get the numeric ID of this node."""

    @abc.abstractmethod
    def get_user_id(self) -> str:
        """Get the user-friendly ID of this node."""

    @abc.abstractmethod
    def get_neighbors(self) -> list[int]:
        """Get list of neighboring node IDs."""

    @abc.abstractmethod
    def send_message(
        self,
        data: bytes,
        destination: int | None = None,
        *,
        want_ack: bool = False,
    ) -> int | None:
        """Send a message to the specified destination or broadcast if None."""

    @abc.abstractmethod
    def receive_message(self, timeout: float = 1.0) -> bytes | None:
        """Receive a message, waiting up to timeout seconds."""


class MeshtasticMeshInterface(MeshInterface):
    """Implementation of MeshInterface using Meshtastic protocol and devices.

    This class provides mesh networking functionality using Meshtastic-compatible
    devices connected via serial interface.
    """

    def __init__(self, serial_device: str | None = None) -> None:
        """Initialize Meshtastic interface.

        Args:
            serial_device: Optional path to serial device. If None, auto-detect.
        """
        super().__init__()
        self.serial_device = serial_device
        self._interface: UnderlyingMesh | None = None
        self._rx_queue = queue.Queue()

        self._lock = threading.Lock()
        self._stop_event = threading.Event()

    def connect(self) -> None:
        """Connect to the Meshtastic device using serial interface."""
        logger.info("Connecting to Meshtastic device...")
        self._interface = meshtastic.serial_interface.SerialInterface(
            devPath=self.serial_device,
        )
        self._interface.onReceive = self._on_receive
        logger.info("Connected on %s", self.serial_device or "AUTO")

    def close(self) -> None:
        """Close the connection to the Meshtastic device."""
        if self._interface:
            try:
                self._interface.close()
            except Exception:
                logger.exception("Error closing Meshtastic interface.")
        self._interface = None
        self._stop_event.set()
        logger.info("MeshtasticMeshInterface closed.")

    def get_numeric_node_id(self) -> int | None:
        """Get the numeric ID of this node from Meshtastic device."""
        if not self._interface:
            return None
        info = self._interface.getMyNodeInfo()
        return info["num"] if info and "num" in info else None

    def get_user_id(self) -> str:
        """Get the user ID from Meshtastic device."""
        if not self._interface:
            return "UNKNOWN"
        my_user = self._interface.getMyUser()
        return my_user["id"] if my_user and "id" in my_user else "UNKNOWN"

    def get_neighbors(self) -> list[int]:
        """Get list of neighboring node IDs from Meshtastic device."""
        if not self._interface:
            return []
        my_num = self.get_numeric_node_id()
        return [num for num in self._interface.nodes if num != my_num]

    def send_message(
        self,
        data: bytes,
        destination: int | None = None,
        *,
        want_ack: bool = False,
    ) -> int | None:
        """Send a message through the Meshtastic device.

        Args:
            data: Bytes to send
            destination: Target node ID, or None for broadcast
            want_ack: Whether to request acknowledgment

        Returns:
            Packet ID if sent, None on failure
        """
        if not self._interface:
            logger.warning("No Meshtastic interface; cannot send.")
            return None

        dest_id = "^all" if destination is None else str(destination)

        def on_resp_cb(resp_packet: dict) -> None:
            self._on_ack_response(resp_packet)

        try:
            result_packet = self._interface.sendData(
                data,
                destinationId=dest_id,
                portNum=self.MESH_PORT_NUM,
                wantAck=want_ack,
                wantResponse=False,
                onResponse=on_resp_cb,
                onResponseAckPermitted=True,
            )
            if result_packet:
                pkt_id = result_packet.id
                with self._lock:
                    self._ack_results[pkt_id] = None
                return pkt_id
            logger.warning("No packet returned by sendData")
        except Exception:
            logger.exception("Failed to send data.")
            return None
        else:
            return None

    def receive_message(self, timeout: float = 1.0) -> bytes | None:
        """Receive a message from the message queue.

        Args:
            timeout: How long to wait for a message in seconds

        Returns:
            Message bytes if received, None on timeout
        """
        try:
            return self._rx_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _on_receive(self, packet: dict, _: UnderlyingMesh) -> None:
        """Handle received messages from the Meshtastic device."""
        try:
            decoded = packet.get("decoded", {})
            portnum = decoded.get("portnum")
            if portnum == self.MESH_PORT_NUM:
                payload = decoded.get("payload")
                if payload:
                    self._rx_queue.put(payload)
        except Exception:
            logger.exception("Error in _on_receive")

    def _on_ack_response(self, resp_packet: dict) -> None:
        """Called when an ack or nak is received, or the transaction ends.

        We'll see something like resp_packet with an 'id' field and
        possibly 'result': 'ACK' or 'NAK'.
        """
        try:
            pkt_id = resp_packet.get("id")
            if pkt_id is None:
                return

            result_str = resp_packet.get("result")
            ack_status: bool | None = None
            if result_str == "ACK":
                ack_status = True
            elif result_str == "NAK":
                ack_status = False

            if ack_status is not None:
                with self._lock:
                    if pkt_id in self._ack_results:
                        self._ack_results[pkt_id] = ack_status

                logger.debug(
                    "AckResponse for packet_id=%d => %s",
                    pkt_id,
                    "ACK" if ack_status else "NAK",
                )

                if self._ack_callback:
                    self._ack_callback(pkt_id, ack_status)

        except Exception:
            logger.exception("Error in _on_ack_response")


class SimulatedMeshInterface(MeshInterface):
    """Implementation of MeshInterface that simulates a mesh network.

    This class provides a simulated mesh network for testing and development,
    with configurable nodes and network topology.
    """

    _nodes_data: ClassVar[dict[int, dict]] = {}
    _global_packet_id: ClassVar[int] = 1000
    _ACK_SUCCESS_PERCENT: ClassVar[int] = 80

    def __init__(self, numeric_id: int, user_id: str | None = None) -> None:
        """Initialize simulated mesh interface.

        Args:
            numeric_id: Numeric ID for this node
            user_id: Optional user-friendly ID. Defaults to "node-{numeric_id}"
        """
        super().__init__()
        self.numeric_id = numeric_id
        self.user_id = user_id or f"node-{numeric_id}"

        if numeric_id not in self._nodes_data:
            self._nodes_data[numeric_id] = {
                "user_id": self.user_id,
                "neighbors": [],
                "inbox": queue.Queue(),
            }
        else:
            self._nodes_data[numeric_id]["user_id"] = self.user_id

    def connect(self) -> None:
        """Connect the simulated node."""
        logger.info(
            "Simulated node %d connected. (user_id=%s)",
            self.numeric_id,
            self.user_id,
        )

    def close(self) -> None:
        """Disconnect the simulated node."""
        logger.info("Simulated node %d disconnected.", self.numeric_id)

    def get_numeric_node_id(self) -> int | None:
        """Get this node's numeric ID."""
        return self.numeric_id

    def get_user_id(self) -> str:
        """Get this node's user ID."""
        return self.user_id

    def get_neighbors(self) -> list[int]:
        """Get list of neighboring node IDs."""
        data = self._nodes_data.get(self.numeric_id)
        if not data:
            return []
        return list(data["neighbors"])

    def send_message(
        self,
        data: bytes,
        destination: int | None = None,
        *,
        want_ack: bool = False,
    ) -> int | None:
        """Send a message through the simulated network.

        Args:
            data: Bytes to send
            destination: Target node ID, or None for broadcast
            want_ack: Whether to request acknowledgment

        Returns:
            Packet ID if sent, None on failure
        """
        self.send_message_with_id(data, destination, want_ack=want_ack)

    def send_message_with_id(
        self,
        data: bytes,
        destination: int | None = None,
        *,
        want_ack: bool = False,
    ) -> int | None:
        """Implementation of send_message that returns packet ID."""
        node_data = self._nodes_data.get(self.numeric_id)
        if not node_data:
            logger.warning("Node %d not found; can't send.", self.numeric_id)
            return None

        pkt_id = SimulatedMeshInterface._global_packet_id
        SimulatedMeshInterface._global_packet_id += 1

        # Send data
        if destination is None:
            # broadcast
            for nbr_id in node_data["neighbors"]:
                nbr_data = self._nodes_data.get(nbr_id)
                if nbr_data:
                    nbr_data["inbox"].put(data)
            logger.debug(
                "Sim %d broadcast: %r (pkt_id=%d, want_ack=%s)",
                self.numeric_id,
                data,
                pkt_id,
                want_ack,
            )
        else:
            # unicast
            dest_data = self._nodes_data.get(destination)
            if dest_data:
                dest_data["inbox"].put(data)
                logger.debug(
                    "Sim %d -> %d: %r (pkt_id=%d, want_ack=%s)",
                    self.numeric_id,
                    destination,
                    data,
                    pkt_id,
                    want_ack,
                )
            else:
                logger.warning(
                    "Destination %d doesn't exist; failing ack...",
                    destination,
                )
                if want_ack and self._ack_callback:
                    # Immediately call user ack callback with fail
                    self._ack_callback(pkt_id, False)  # noqa: FBT003
                return pkt_id

        # If want_ack => simulate success/fail
        if want_ack:
            import secrets
            # Simulate success/fail based on configured probability
            success = secrets.randbelow(100) < self._ACK_SUCCESS_PERCENT
            logger.debug("Sim ack for pkt_id=%d => %s", pkt_id, success)
            if self._ack_callback:
                self._ack_callback(pkt_id, success)

        return pkt_id

    def receive_message(self, timeout: float = 1.0) -> bytes | None:
        """Receive a message from the simulated network.

        Args:
            timeout: How long to wait for a message in seconds

        Returns:
            Message bytes if received, None on timeout
        """
        data = self._nodes_data.get(self.numeric_id)
        if not data:
            logger.warning("No node data for %d", self.numeric_id)
            return None

        inbox = data["inbox"]
        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                return inbox.get_nowait()
            except queue.Empty:
                time.sleep(0.05)
        return None
