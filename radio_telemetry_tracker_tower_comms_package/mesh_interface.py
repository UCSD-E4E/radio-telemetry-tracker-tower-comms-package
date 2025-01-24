"""Interface definitions for mesh network communication."""

import abc
from collections.abc import Callable
from typing import Any


class MeshNetworkError(Exception):
    """Base exception for mesh network related errors."""


class MeshConnectionError(MeshNetworkError):
    """Raised when connection to mesh device fails."""


class SendError(MeshNetworkError):
    """Raised when sending a message fails."""


class MeshInterface(abc.ABC):
    """Abstract base class defining the interface for mesh network communication.

    Provides a common API for different mesh networking implementations,
    supporting both real hardware and simulated networks.
    """

    MESH_PORT_NUM = 0

    def __init__(self) -> None:
        """Initialize mesh interface with default callback handlers.

        Sets up acknowledgment callback handlers for success and failure cases.
        """
        self._on_ack_success: Callable[[int], None] | None = None
        self._on_ack_failure: Callable[[int], None] | None = None

    @property
    def on_ack_success(self) -> Callable[[int], None] | None:
        """Get the success acknowledgment callback function."""
        return self._on_ack_success

    @on_ack_success.setter
    def on_ack_success(self, callback: Callable[[int], None]) -> None:
        """Set the success acknowledgment callback function.

        Args:
            callback: Function to call when message acknowledgment succeeds
        """
        self._on_ack_success = callback

    @property
    def on_ack_failure(self) -> Callable[[int], None] | None:
        """Get the failure acknowledgment callback function."""
        return self._on_ack_failure

    @on_ack_failure.setter
    def on_ack_failure(self, callback: Callable[[int], None]) -> None:
        """Set the failure acknowledgment callback function.

        Args:
            callback: Function to call when message acknowledgment fails
        """
        self._on_ack_failure = callback

    @abc.abstractmethod
    def connect(self) -> None:
        """Establish connection to the mesh network."""

    @abc.abstractmethod
    def close(self) -> None:
        """Close the connection to the mesh network."""

    @abc.abstractmethod
    def get_numeric_node_id(self) -> int | None:
        """Get this node's numeric ID."""

    @abc.abstractmethod
    def get_user_id(self) -> str:
        """Get this node's user-friendly ID."""

    @abc.abstractmethod
    def get_neighbors(self) -> list[int]:
        """Get list of neighboring node IDs."""

    @abc.abstractmethod
    def get_node_position(self) -> dict[str, Any] | None:
        """Get the geographic position of this node in the mesh network."""

    @abc.abstractmethod
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

    @abc.abstractmethod
    def register_packet_callback(self, callback: Callable[[bytes], None]) -> None:
        """Register a callback for received packets.

        Args:
            callback: Function to call when a packet is received
        """

