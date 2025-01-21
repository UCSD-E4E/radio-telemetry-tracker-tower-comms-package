"""Interfaces for mesh network communication in the Radio Telemetry Tracker system."""

import abc
import logging
import queue
import threading
import time
from collections.abc import Callable
from typing import ClassVar, TypedDict

import meshtastic
from meshtastic.serial_interface import SerialInterface as UnderlyingMesh

logger = logging.getLogger(__name__)


class PacketData(TypedDict, total=False):
    """Type definition for packet data structure."""

    id: int
    decoded: dict
    result: str
    payload: bytes


class MeshNetworkError(Exception):
    """Base exception for mesh network related errors."""


class MeshConnectionError(MeshNetworkError):
    """Raised when connection to mesh device fails."""


class SendError(MeshNetworkError):
    """Raised when sending a message fails."""



class MeshInterface(abc.ABC):
    """Abstract base class defining the interface for mesh network communication.

    This interface provides a common API for different mesh networking implementations,
    supporting both real hardware (Meshtastic) and simulated networks.

    Attributes:
        MESH_PORT_NUM: Port number used for mesh communication
        _on_ack_success: Callback function called when message acknowledgment succeeds
        _on_ack_fail: Callback function called when message acknowledgment fails
    """

    MESH_PORT_NUM = 42

    def __init__(self) -> None:
        """Initialize the mesh interface with default callback handlers."""
        self._on_ack_success: Callable[[int], None] | None = None
        self._on_ack_fail: Callable[[int], None] | None = None

    @property
    def on_ack_success(self) -> Callable[[int], None] | None:
        """Get the success acknowledgment callback."""
        return self._on_ack_success

    @on_ack_success.setter
    def on_ack_success(self, callback: Callable[[int], None] | None) -> None:
        """Set the success acknowledgment callback.

        Args:
            callback: Function to call when message acknowledgment succeeds.
                     Takes packet ID as parameter.
        """
        self._on_ack_success = callback

    @property
    def on_ack_fail(self) -> Callable[[int], None] | None:
        """Get the failure acknowledgment callback."""
        return self._on_ack_fail

    @on_ack_fail.setter
    def on_ack_fail(self, callback: Callable[[int], None] | None) -> None:
        """Set the failure acknowledgment callback.

        Args:
            callback: Function to call when message acknowledgment fails.
                     Takes packet ID as parameter.
        """
        self._on_ack_fail = callback

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
        """Connect to the Meshtastic device using serial interface.

        Raises:
            MeshConnectionError: If connection to device fails
        """
        logger.info("Connecting to Meshtastic device...")
        try:
            self._interface = meshtastic.serial_interface.SerialInterface(
                devPath=self.serial_device,
            )
            self._interface.onReceive = self._on_receive
            logger.info("Connected on %s", self.serial_device or "AUTO")
        except Exception as e:
            msg = f"Failed to connect: {e}"
            raise MeshConnectionError(msg) from e

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

        Raises:
            SendError: If sending the message fails
        """
        if not self._interface:
            msg = "No Meshtastic interface; cannot send."
            raise SendError(msg)

        dest_id = "^all" if destination is None else str(destination)

        def on_resp_cb(resp_packet: PacketData) -> None:
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
                return result_packet.id
            logger.warning("No packet returned by sendData")
        except Exception as e:
            msg = f"Failed to send data: {e}"
            raise SendError(msg) from e
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

    def _on_receive(self, packet: PacketData, _: UnderlyingMesh) -> None:
        """Handle received messages from the Meshtastic device.

        Args:
            packet: Received packet data
            _: Unused interface parameter
        """
        try:
            decoded = packet.get("decoded", {})
            portnum = decoded.get("portnum")
            if portnum == self.MESH_PORT_NUM:
                payload = decoded.get("payload")
                if payload:
                    self._rx_queue.put(payload)
                    logger.debug("Received message: %r", payload)
        except Exception:
            logger.exception("Error processing received message")

    def _on_ack_response(self, resp_packet: PacketData) -> None:
        """Called when an ack or nak is received, or the transaction ends.

        Args:
            resp_packet: Response packet containing acknowledgment info
        """
        try:
            pkt_id = resp_packet.get("id")
            if pkt_id is None:
                return

            result_str = resp_packet.get("result")
            if result_str == "ACK" and self._on_ack_success:
                self._on_ack_success(pkt_id)
            elif result_str == "NAK" and self._on_ack_fail:
                self._on_ack_fail(pkt_id)

            logger.debug(
                "AckResponse for packet_id=%d => %s",
                pkt_id,
                result_str or "UNKNOWN",
            )

        except Exception:
            logger.exception("Error processing ack response")


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
        return self.send_message_with_id(data, destination, want_ack=want_ack)

    def send_message_with_id(
        self,
        data: bytes,
        destination: int | None = None,
        *,
        want_ack: bool = False,
    ) -> int | None:
        """Implementation of send_message that returns packet ID.

        Args:
            data: Bytes to send
            destination: Target node ID, or None for broadcast
            want_ack: Whether to request acknowledgment

        Returns:
            Packet ID if sent, None on failure
        """
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
                if want_ack and self._on_ack_fail:
                    # Immediately call user ack callback with fail
                    self._on_ack_fail(pkt_id)
                return pkt_id

        # If want_ack => simulate success/fail
        if want_ack:
            import secrets

            # Simulate success/fail based on configured probability
            success = secrets.randbelow(100) < self._ACK_SUCCESS_PERCENT
            logger.debug("Sim ack for pkt_id=%d => %s", pkt_id, success)
            if success and self._on_ack_success:
                self._on_ack_success(pkt_id)
            elif not success and self._on_ack_fail:
                self._on_ack_fail(pkt_id)

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
