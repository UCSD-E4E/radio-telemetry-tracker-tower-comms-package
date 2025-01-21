"""High-level TowerComms class for user-facing interaction with mesh network packet communication."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, TypeVar

from radio_telemetry_tracker_tower_comms_package.data_models import (
    ConfigData,
    ErrorData,
    NoConfigData,
    NoPingData,
    PingData,
    RequestConfigData,
    RequestPingData,
)
from radio_telemetry_tracker_tower_comms_package.interfaces import (
    MeshtasticMeshInterface,
    SimulatedMeshInterface,
)
from radio_telemetry_tracker_tower_comms_package.proto import MeshPacket
from radio_telemetry_tracker_tower_comms_package.transceiver import (
    Transceiver,
    current_timestamp_us,
)

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")
logger = logging.getLogger(__name__)


@dataclass
class NodeConfig:
    """Configuration for mesh network node."""

    interface_type: Literal["meshtastic", "simulated"]
    device: str | None = None


class TowerComms(Transceiver):
    """High-level class for managing mesh network communication between radio telemetry towers.

    Handles sending and receiving configuration, ping data, and other messages between towers
    using either Meshtastic devices or a simulated mesh network.
    """

    def __init__(
        self,
        config: NodeConfig,
        on_ack_success: Callable[[int], None],
        on_ack_failure: Callable[[int], None],
    ) -> None:
        """Initialize TowerComms with mesh network configuration and callbacks.

        Args:
            config: Configuration for the mesh network node
            on_ack_success: Callback when message acknowledgment succeeds
            on_ack_failure: Callback when message acknowledgment fails

        Raises:
            ValueError: If interface_type is invalid
        """
        if config.interface_type == "serial":
            self.interface = MeshtasticMeshInterface(config.device)
        elif config.interface_type == "simulated":
            self.interface = SimulatedMeshInterface()
        else:
            msg = f"Invalid interface type: {config.interface_type}"
            raise ValueError(msg)

        super().__init__(self.interface, on_ack_success, on_ack_failure)

        self._packet_handlers = {
            "config": (self._extract_config, self._handle_config),
            "no_config": (self._extract_no_config, self._handle_no_config),
            "ping": (self._extract_ping, self._handle_ping),
            "no_ping": (self._extract_no_ping, self._handle_no_ping),
            "request_config": (
                self._extract_request_config,
                self._handle_request_config,
            ),
            "request_ping": (self._extract_request_ping, self._handle_request_ping),
            "error": (self._extract_error, self._handle_error),
        }

        self._config_handlers: list[tuple[Callable[[ConfigData], None], bool]] = []
        self._no_config_handlers: list[tuple[Callable[[NoConfigData], None], bool]] = []
        self._ping_handlers: list[tuple[Callable[[PingData], None], bool]] = []
        self._no_ping_handlers: list[tuple[Callable[[NoPingData], None], bool]] = []
        self._request_config_handlers: list[
            tuple[Callable[[RequestConfigData], None], bool]
        ] = []
        self._request_ping_handlers: list[
            tuple[Callable[[RequestPingData], None], bool]
        ] = []
        self._error_handlers: list[tuple[Callable[[ErrorData], None], bool]] = []

    def on_packet_received(self, packet: MeshPacket) -> None:
        """Handle received packets by delegating to appropriate type-specific handlers.

        Args:
            packet: The received mesh packet to process
        """
        field = packet.WhichOneof("msg")
        handler_entry = self._packet_handlers.get(field)
        if not handler_entry:
            logger.debug("Received an unhandled packet type: %s", field)
            return

        extractor, handler = handler_entry
        data_object = extractor(getattr(packet, field))
        handler(data_object)

    def register_config_handler(
        self,
        handler: Callable[[ConfigData], None],
        *,
        one_time: bool = False,
    ) -> None:
        """Register a handler for configuration data packets.

        Args:
            handler: Function to call when config data is received
            one_time: If True, handler is removed after first invocation
        """
        self._config_handlers.append((handler, one_time))

    def unregister_config_handler(self, handler: Callable[[ConfigData], None]) -> bool:
        """Unregister a previously registered config handler.

        Args:
            handler: The handler function to remove

        Returns:
            True if handler was found and removed, False otherwise
        """
        for cb, once in self._config_handlers:
            if cb == handler:
                self._config_handlers.remove((cb, once))
                return True
        return False

    def register_no_config_handler(
        self,
        handler: Callable[[NoConfigData], None],
        *,
        one_time: bool = False,
    ) -> None:
        """Register a handler for no-config response packets.

        Args:
            handler: Function to call when no-config response is received
            one_time: If True, handler is removed after first invocation
        """
        self._no_config_handlers.append((handler, one_time))

    def unregister_no_config_handler(
        self,
        handler: Callable[[NoConfigData], None],
    ) -> bool:
        """Unregister a previously registered no-config handler.

        Args:
            handler: The handler function to remove

        Returns:
            True if handler was found and removed, False otherwise
        """
        for cb, once in self._no_config_handlers:
            if cb == handler:
                self._no_config_handlers.remove((cb, once))
                return True
        return False

    def register_ping_handler(
        self,
        handler: Callable[[PingData], None],
        *,
        one_time: bool = False,
    ) -> None:
        """Register a handler for ping data packets.

        Args:
            handler: Function to call when ping data is received
            one_time: If True, handler is removed after first invocation
        """
        self._ping_handlers.append((handler, one_time))

    def unregister_ping_handler(self, handler: Callable[[PingData], None]) -> bool:
        """Unregister a previously registered ping handler.

        Args:
            handler: The handler function to remove

        Returns:
            True if handler was found and removed, False otherwise
        """
        for cb, once in self._ping_handlers:
            if cb == handler:
                self._ping_handlers.remove((cb, once))
                return True
        return False

    def register_no_ping_handler(
        self,
        handler: Callable[[NoPingData], None],
        *,
        one_time: bool = False,
    ) -> None:
        """Register a handler for no-ping response packets.

        Args:
            handler: Function to call when no-ping response is received
            one_time: If True, handler is removed after first invocation
        """
        self._no_ping_handlers.append((handler, one_time))

    def unregister_no_ping_handler(self, handler: Callable[[NoPingData], None]) -> bool:
        """Unregister a previously registered no-ping handler.

        Args:
            handler: The handler function to remove

        Returns:
            True if handler was found and removed, False otherwise
        """
        for cb, once in self._no_ping_handlers:
            if cb == handler:
                self._no_ping_handlers.remove((cb, once))
                return True
        return False

    def register_request_config_handler(
        self,
        handler: Callable[[RequestConfigData], None],
        *,
        one_time: bool = False,
    ) -> None:
        """Register a handler for config request packets.

        Args:
            handler: Function to call when config request is received
            one_time: If True, handler is removed after first invocation
        """
        self._request_config_handlers.append((handler, one_time))

    def unregister_request_config_handler(
        self,
        handler: Callable[[RequestConfigData], None],
    ) -> bool:
        """Unregister a previously registered request-config handler.

        Args:
            handler: The handler function to remove

        Returns:
            True if handler was found and removed, False otherwise
        """
        for cb, once in self._request_config_handlers:
            if cb == handler:
                self._request_config_handlers.remove((cb, once))
                return True
        return False

    def register_request_ping_handler(
        self,
        handler: Callable[[RequestPingData], None],
        *,
        one_time: bool = False,
    ) -> None:
        """Register a handler for ping request packets.

        Args:
            handler: Function to call when ping request is received
            one_time: If True, handler is removed after first invocation
        """
        self._request_ping_handlers.append((handler, one_time))

    def unregister_request_ping_handler(
        self,
        handler: Callable[[RequestPingData], None],
    ) -> bool:
        """Unregister a previously registered request-ping handler.

        Args:
            handler: The handler function to remove

        Returns:
            True if handler was found and removed, False otherwise
        """
        for cb, once in self._request_ping_handlers:
            if cb == handler:
                self._request_ping_handlers.remove((cb, once))
                return True
        return False

    def register_error_handler(
        self,
        handler: Callable[[ErrorData], None],
        *,
        one_time: bool = False,
    ) -> None:
        """Register a handler for error packets.

        Args:
            handler: Function to call when error packet is received
            one_time: If True, handler is removed after first invocation
        """
        self._error_handlers.append((handler, one_time))

    def unregister_error_handler(self, handler: Callable[[ErrorData], None]) -> bool:
        """Unregister a previously registered error handler.

        Args:
            handler: The handler function to remove

        Returns:
            True if handler was found and removed, False otherwise
        """
        for cb, once in self._error_handlers:
            if cb == handler:
                self._error_handlers.remove((cb, once))
                return True
        return False

    def _validate_destination(self, destination: int | None) -> bool:
        """Validate if a destination ID is valid for sending messages.

        Args:
            destination: The destination node ID to validate, or None for broadcast

        Returns:
            True if the destination is valid (None or exists in neighbors)

        Raises:
            ValueError: If the destination is invalid
        """
        if destination is None:
            return True

        neighbors = self.get_neighbors()
        if destination not in neighbors:
            msg = f"Invalid destination {destination}. Node must be in neighbors: {neighbors}"
            raise ValueError(msg)

        return True

    def send_config(self, data: ConfigData, destination: int | None = None) -> None:
        """Send configuration data to a specific node or broadcast.

        Args:
            data: Configuration data to send
            destination: Optional destination node ID. If None, broadcast to all neighbors.

        Raises:
            ValueError: If the destination is invalid
        """
        self._validate_destination(destination)
        packet = MeshPacket()
        packet.config.base_packet.timestamp = current_timestamp_us()
        packet.config.gain = data.gain
        packet.config.sampling_rate = data.sampling_rate
        packet.config.center_frequency = data.center_frequency
        packet.config.run_num = data.run_num
        packet.config.enable_test_data = data.enable_test_data
        packet.config.ping_width_ms = data.ping_width_ms
        packet.config.ping_min_snr = data.ping_min_snr
        packet.config.ping_max_len_mult = data.ping_max_len_mult
        packet.config.ping_min_len_mult = data.ping_min_len_mult
        packet.config.target_frequencies.extend(data.target_frequencies)
        self.enqueue_packet(packet, destination)

    def send_no_config(
        self,
        destination: int | None = None,
    ) -> None:
        """Send no-config response to a specific node or broadcast.

        Args:
            destination: Optional destination node ID. If None, broadcast to all neighbors.

        Raises:
            ValueError: If the destination is invalid
        """
        self._validate_destination(destination)
        packet = MeshPacket()
        packet.no_config.base_packet.timestamp = current_timestamp_us()
        self.enqueue_packet(packet, destination)

    def send_ping(self, data: PingData, destination: int | None = None) -> None:
        """Send ping data to a specific node or broadcast.

        Args:
            data: Ping data to send
            destination: Optional destination node ID. If None, broadcast to all neighbors.

        Raises:
            ValueError: If the destination is invalid
        """
        self._validate_destination(destination)
        packet = MeshPacket()
        packet.ping.base_packet.timestamp = current_timestamp_us()
        packet.ping.frequency = data.frequency
        packet.ping.amplitude = data.amplitude
        packet.ping.latitude = data.latitude
        packet.ping.longitude = data.longitude
        packet.ping.altitude = data.altitude
        self.enqueue_packet(packet, destination)

    def send_no_ping(self, destination: int | None = None) -> None:
        """Send no-ping response to a specific node or broadcast.

        Args:
            destination: Optional destination node ID. If None, broadcast to all neighbors.

        Raises:
            ValueError: If the destination is invalid
        """
        self._validate_destination(destination)
        packet = MeshPacket()
        packet.no_ping.base_packet.timestamp = current_timestamp_us()
        self.enqueue_packet(packet, destination)

    def send_request_config(
        self,
        data: RequestConfigData,
        destination: int | None = None,
    ) -> None:
        """Send config request to a specific node or broadcast.

        Args:
            data: Request config data to send
            destination: Optional destination node ID. If None, broadcast to all neighbors.

        Raises:
            ValueError: If the destination is invalid
        """
        self._validate_destination(destination)
        packet = MeshPacket()
        packet.request_config.node_id = data.node_id
        packet.request_config.base_packet.timestamp = current_timestamp_us()
        self.enqueue_packet(packet, destination)

    def send_request_ping(
        self,
        data: RequestPingData,
        destination: int | None = None,
    ) -> None:
        """Send ping request to a specific node or broadcast.

        Args:
            data: Request ping data to send
            destination: Optional destination node ID. If None, broadcast to all neighbors.

        Raises:
            ValueError: If the destination is invalid
        """
        self._validate_destination(destination)
        packet = MeshPacket()
        packet.request_ping.node_id = data.node_id
        packet.request_ping.base_packet.timestamp = current_timestamp_us()
        self.enqueue_packet(packet, destination)

    def send_error(self, data: ErrorData, destination: int | None = None) -> None:
        """Send error data to a specific node or broadcast.

        Args:
            data: Error data to send
            destination: Optional destination node ID. If None, broadcast to all neighbors.

        Raises:
            ValueError: If the destination is invalid
        """
        self._validate_destination(destination)
        packet = MeshPacket()
        packet.error.base_packet.timestamp = current_timestamp_us()
        packet.error.error_message = data.error_message
        self.enqueue_packet(packet, destination)

    def _extract_config(self, packet: MeshPacket.Config) -> ConfigData:
        """Extract config data from a mesh packet.

        Args:
            packet: Config packet to extract data from

        Returns:
            Extracted ConfigData object
        """
        return ConfigData(
            gain=packet.gain,
            sampling_rate=packet.sampling_rate,
            center_frequency=packet.center_frequency,
            run_num=packet.run_num,
            enable_test_data=packet.enable_test_data,
            ping_width_ms=packet.ping_width_ms,
            ping_min_snr=packet.ping_min_snr,
            ping_max_len_mult=packet.ping_max_len_mult,
            ping_min_len_mult=packet.ping_min_len_mult,
            target_frequencies=list(packet.target_frequencies),
            timestamp=packet.timestamp,
        )

    def _extract_no_config(self, packet: MeshPacket.NoConfig) -> NoConfigData:
        """Extract no-config data from a mesh packet.

        Args:
            packet: No-config packet to extract data from

        Returns:
            Extracted NoConfigData object
        """
        return NoConfigData(timestamp=packet.timestamp)

    def _extract_ping(self, packet: MeshPacket.Ping) -> PingData:
        """Extract ping data from a mesh packet.

        Args:
            packet: Ping packet to extract data from

        Returns:
            Extracted PingData object
        """
        return PingData(
            frequency=packet.frequency,
            amplitude=packet.amplitude,
            latitude=packet.latitude,
            longitude=packet.longitude,
            altitude=packet.altitude,
            timestamp=packet.timestamp,
        )

    def _extract_no_ping(self, packet: MeshPacket.NoPing) -> NoPingData:
        """Extract no-ping data from a mesh packet.

        Args:
            packet: No-ping packet to extract data from

        Returns:
            Extracted NoPingData object
        """
        return NoPingData(timestamp=packet.timestamp)

    def _extract_request_config(
        self,
        packet: MeshPacket.RequestConfig,
    ) -> RequestConfigData:
        """Extract request config data from a mesh packet.

        Args:
            packet: Request config packet to extract data from

        Returns:
            Extracted RequestConfigData object
        """
        return RequestConfigData(timestamp=packet.timestamp)

    def _extract_request_ping(self, packet: MeshPacket.RequestPing) -> RequestPingData:
        """Extract request ping data from a mesh packet.

        Args:
            packet: Request ping packet to extract data from

        Returns:
            Extracted RequestPingData object
        """
        return RequestPingData(timestamp=packet.timestamp)

    def _extract_error(self, packet: MeshPacket.Error) -> ErrorData:
        """Extract error data from a mesh packet.

        Args:
            packet: Error packet to extract data from

        Returns:
            Extracted ErrorData object
        """
        return ErrorData(
            error_message=packet.error_message,
            timestamp=packet.timestamp,
        )

    def _handle_config(self, data: ConfigData) -> None:
        """Handle received config data by invoking registered handlers.

        Args:
            data: Received config data
        """
        self._invoke_handlers(self._config_handlers, data)

    def _handle_no_config(self, data: NoConfigData) -> None:
        """Handle received no-config data by invoking registered handlers.

        Args:
            data: Received no-config data
        """
        self._invoke_handlers(self._no_config_handlers, data)

    def _handle_ping(self, data: PingData) -> None:
        """Handle received ping data by invoking registered handlers.

        Args:
            data: Received ping data
        """
        self._invoke_handlers(self._ping_handlers, data)

    def _handle_no_ping(self, data: NoPingData) -> None:
        """Handle received no-ping data by invoking registered handlers.

        Args:
            data: Received no-ping data
        """
        self._invoke_handlers(self._no_ping_handlers, data)

    def _handle_request_config(self, data: RequestConfigData) -> None:
        """Handle received request config data by invoking registered handlers.

        Args:
            data: Received request config data
        """
        self._invoke_handlers(self._request_config_handlers, data)

    def _handle_request_ping(self, data: RequestPingData) -> None:
        """Handle received request ping data by invoking registered handlers.

        Args:
            data: Received request ping data
        """
        self._invoke_handlers(self._request_ping_handlers, data)

    def _handle_error(self, data: ErrorData) -> None:
        """Handle received error data by invoking registered handlers.

        Args:
            data: Received error data
        """
        self._invoke_handlers(self._error_handlers, data)

    @staticmethod
    def _invoke_handlers(
        handlers_list: list[tuple[Callable[[T], None], bool]],
        data: T,
    ) -> None:
        """Invoke all registered handlers for a given data type.

        Args:
            handlers_list: List of (handler, one_time) tuples
            data: Data to pass to handlers
        """
        to_remove = []
        for i, (callback, one_time) in enumerate(handlers_list):
            callback(data)
            if one_time:
                to_remove.append(i)
        for i in reversed(to_remove):
            handlers_list.pop(i)
