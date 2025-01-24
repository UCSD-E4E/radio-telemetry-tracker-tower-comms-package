"""High-level interface for mesh network communication between radio telemetry towers.

Provides functionality for sending and receiving configuration, ping data, and error
messages between towers in a mesh network.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, TypeVar

from radio_telemetry_tracker_tower_comms_package.data_models import (
    ConfigData,
    ErrorData,
    PingData,
    PositionData,
    RequestConfigData,
)
from radio_telemetry_tracker_tower_comms_package.mesh_interface import MeshInterface
from radio_telemetry_tracker_tower_comms_package.meshtastic_mesh import (
    MeshtasticMeshInterface,
)
from radio_telemetry_tracker_tower_comms_package.proto import (
    ConfigPacket as PbConfigPacket,
)
from radio_telemetry_tracker_tower_comms_package.proto import (
    ErrorPacket as PbErrorPacket,
)
from radio_telemetry_tracker_tower_comms_package.proto import (
    MeshPacket as PbMeshPacket,
)
from radio_telemetry_tracker_tower_comms_package.proto import (
    PingPacket as PbPingPacket,
)
from radio_telemetry_tracker_tower_comms_package.proto import (
    RequestConfigPacket as PbRequestConfigPacket,
)
from radio_telemetry_tracker_tower_comms_package.simulated_mesh import (
    SimulatedMeshInterface,
)

T = TypeVar("T", RequestConfigData, ConfigData, PingData, ErrorData)

logger = logging.getLogger(__name__)


@dataclass
class NodeConfig:
    """Configuration for a mesh network node.

    Attributes:
        interface_type: Type of mesh interface ("meshtastic" or "simulated")
        device: Serial device path for Meshtastic interface
        numeric_id: Numeric ID for simulated nodes
        user_id: User-friendly ID for the node
    """

    interface_type: Literal["meshtastic", "simulated"]
    device: str | None = None
    numeric_id: int | None = None
    user_id: str | None = None


class TowerComms:
    """High-level class for managing mesh network communication between towers.

    Handles sending and receiving configuration, ping data, and error messages
    between towers, with support for message acknowledgments and callbacks.
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
        """
        self.config = config
        self._on_ack_success = on_ack_success
        self._on_ack_failure = on_ack_failure

        # Create the mesh interface
        self.mesh_interface = self._create_mesh_interface(config)
        if self._on_ack_success:
            self.mesh_interface.on_ack_success = self._on_ack_success
        if self._on_ack_failure:
            self.mesh_interface.on_ack_failure = self._on_ack_failure

        # Register a callback for inbound raw bytes
        self.mesh_interface.register_packet_callback(self._on_raw_packet)

        # Handler lists
        self._request_config_handlers: list[
            tuple[Callable[[RequestConfigData], None], bool]
        ] = []
        self._config_handlers: list[tuple[Callable[[ConfigData], None], bool]] = []
        self._ping_handlers: list[tuple[Callable[[PingData], None], bool]] = []
        self._error_handlers: list[tuple[Callable[[ErrorData], None], bool]] = []

        # --------------------------------------------------------------------------

    # Creating the underlying mesh interface
    # --------------------------------------------------------------------------
    def _create_mesh_interface(self, cfg: NodeConfig) -> MeshInterface:
        if cfg.interface_type == "meshtastic":
            return MeshtasticMeshInterface(serial_device=cfg.device)
        if cfg.interface_type == "simulated":
            if cfg.numeric_id is None:
                msg = "Simulated requires a numeric_id."
                raise ValueError(msg)
            return SimulatedMeshInterface(
                numeric_id=cfg.numeric_id,
                user_id=cfg.user_id,
            )
        msg = f"Unknown interface_type: {cfg.interface_type}"
        raise ValueError(msg)

    # --------------------------------------------------------------------------
    # Lifecycle: start/stop  # noqa: ERA001
    # --------------------------------------------------------------------------

    def start(self) -> None:
        """Start the mesh network interface and enable communication."""
        self.mesh_interface.connect()

    def stop(self) -> None:
        """Stop the mesh network interface and clean up resources."""
        self.mesh_interface.close()

    # --------------------------------------------------------------------------
    # Public methods: Register/Unregister handlers
    # --------------------------------------------------------------------------

    def register_request_config_handler(
        self,
        handler: Callable[[RequestConfigData], None],
        *,
        one_time: bool = False,
    ) -> None:
        """Register a handler for configuration request messages.

        Args:
            handler: Function to call when request config message is received
            one_time: If True, handler is removed after first invocation
        """
        self._request_config_handlers.append((handler, one_time))

    def unregister_request_config_handler(
        self,
        handler: Callable[[RequestConfigData], None],
    ) -> bool:
        """Unregister a previously registered request config handler.

        Args:
            handler: The handler function to remove

        Returns:
            True if handler was found and removed, False otherwise
        """
        return self._unregister_handler(self._request_config_handlers, handler)

    def register_config_handler(
        self,
        handler: Callable[[ConfigData], None],
        *,
        one_time: bool = False,
    ) -> None:
        """Register a handler for configuration messages.

        Args:
            handler: Function to call when config message is received
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
        return self._unregister_handler(self._config_handlers, handler)

    def register_ping_handler(
        self,
        handler: Callable[[PingData], None],
        *,
        one_time: bool = False,
    ) -> None:
        """Register a handler for ping messages.

        Args:
            handler: Function to call when ping message is received
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
        return self._unregister_handler(self._ping_handlers, handler)

    def register_error_handler(
        self,
        handler: Callable[[ErrorData], None],
        *,
        one_time: bool = False,
    ) -> None:
        """Register a handler for error messages.

        Args:
            handler: Function to call when error message is received
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
        return self._unregister_handler(self._error_handlers, handler)

    # --------------------------------------------------------------------------
    # Public methods: Send messages
    # --------------------------------------------------------------------------

    def send_request_config(
        self,
        destination: int | None = None,
        *,
        want_ack: bool = False,
    ) -> None:
        """Send a configuration request message.

        Args:
            destination: Target node ID, or None for broadcast
            want_ack: Whether to request acknowledgment
        """
        pkt = PbMeshPacket()
        pkt.request_config.base_packet.node_id = (
            self.mesh_interface.get_numeric_node_id() or 0
        )
        pkt.request_config.base_packet.timestamp = current_timestamp_us()
        raw = pkt.SerializeToString()
        self.mesh_interface.send_message(
            raw,
            destination=destination,
            want_ack=want_ack,
        )

    def send_config(
        self,
        data: ConfigData,
        destination: int | None = None,
        *,
        want_ack: bool = False,
    ) -> None:
        """Send a configuration message.

        Args:
            data: Configuration data to send
            destination: Target node ID, or None for broadcast
            want_ack: Whether to request acknowledgment
        """
        pkt = PbMeshPacket()
        pkt.config.base_packet.node_id = self.mesh_interface.get_numeric_node_id() or 0
        pkt.config.base_packet.timestamp = current_timestamp_us()

        pkt.config.gain = data.gain
        pkt.config.sampling_rate = data.sampling_rate
        pkt.config.center_frequency = data.center_frequency
        pkt.config.run_num = data.run_num
        pkt.config.enable_test_data = data.enable_test_data
        pkt.config.ping_width_ms = data.ping_width_ms
        pkt.config.ping_min_snr = data.ping_min_snr
        pkt.config.ping_max_len_mult = data.ping_max_len_mult
        pkt.config.ping_min_len_mult = data.ping_min_len_mult
        pkt.config.target_frequencies.extend(data.target_frequencies)

        raw = pkt.SerializeToString()
        self.mesh_interface.send_message(
            raw,
            destination=destination,
            want_ack=want_ack,
        )

    def send_ping(
        self,
        data: PingData,
        destination: int | None = None,
        *,
        want_ack: bool = False,
    ) -> None:
        """Send a ping message.

        Args:
            data: Ping data to send
            destination: Target node ID, or None for broadcast
            want_ack: Whether to request acknowledgment
        """
        pkt = PbMeshPacket()
        pkt.ping.base_packet.node_id = self.mesh_interface.get_numeric_node_id() or 0
        pkt.ping.base_packet.timestamp = current_timestamp_us()

        pkt.ping.frequency = data.frequency
        pkt.ping.amplitude = data.amplitude
        pkt.ping.latitude = data.latitude
        pkt.ping.longitude = data.longitude
        pkt.ping.altitude = data.altitude

        raw = pkt.SerializeToString()
        self.mesh_interface.send_message(
            raw,
            destination=destination,
            want_ack=want_ack,
        )

    def send_error(
        self,
        data: ErrorData,
        destination: int | None = None,
        *,
        want_ack: bool = False,
    ) -> None:
        """Send an error message.

        Args:
            data: Error data to send
            destination: Target node ID, or None for broadcast
            want_ack: Whether to request acknowledgment
        """
        pkt = PbMeshPacket()
        pkt.error.base_packet.node_id = self.mesh_interface.get_numeric_node_id() or 0
        pkt.error.base_packet.timestamp = current_timestamp_us()
        pkt.error.error_message = data.error_message

        raw = pkt.SerializeToString()
        self.mesh_interface.send_message(
            raw,
            destination=destination,
            want_ack=want_ack,
        )

    # --------------------------------------------------------------------------
    # GPS
    # --------------------------------------------------------------------------
    def get_node_position(self) -> PositionData | None:
        """Return a PositionData if found, else None."""
        pos_info = self.mesh_interface.get_node_position()
        if not pos_info:
            return None
        return PositionData(
            node_id=self.mesh_interface.get_numeric_node_id(),
            latitude=pos_info.get("latitude", 0.0),
            longitude=pos_info.get("longitude", 0.0),
            altitude=pos_info.get("altitude", 0.0),
            timestamp=pos_info.get("time"),
        )

    # --------------------------------------------------------------------------
    # Internal: Inbound message parsing
    # --------------------------------------------------------------------------

    def _on_raw_packet(self, raw_data: bytes) -> None:
        try:
            pb = PbMeshPacket()
            pb.ParseFromString(raw_data)

            which = pb.WhichOneof("msg")
            if which == "request_config":
                data = self._extract_request_config(pb.request_config)
                self._handle_request_config(data)
            elif which == "config":
                data = self._extract_config(pb.config)
                self._handle_config(data)
            elif which == "ping":
                data = self._extract_ping(pb.ping)
                self._handle_ping(data)
            elif which == "error":
                data = self._extract_error(pb.error)
                self._handle_error(data)
            else:
                logger.debug("Received unknown message type: %s", which)
        except Exception:
            logger.exception("Failed to parse inbound data as MeshPacket.")

    def _extract_request_config(self, pb: PbRequestConfigPacket) -> RequestConfigData:
        return RequestConfigData(
            node_id=pb.base_packet.node_id,
            timestamp=pb.base_packet.timestamp,
        )

    def _extract_config(self, pb: PbConfigPacket) -> ConfigData:
        return ConfigData(
            gain=pb.gain,
            sampling_rate=pb.sampling_rate,
            center_frequency=pb.center_frequency,
            run_num=pb.run_num,
            enable_test_data=pb.enable_test_data,
            ping_width_ms=pb.ping_width_ms,
            ping_min_snr=pb.ping_min_snr,
            ping_max_len_mult=pb.ping_max_len_mult,
            ping_min_len_mult=pb.ping_min_len_mult,
            target_frequencies=list(pb.target_frequencies),
            node_id=pb.base_packet.node_id,
            timestamp=pb.base_packet.timestamp,
        )

    def _extract_ping(self, pb: PbPingPacket) -> PingData:
        return PingData(
            frequency=pb.frequency,
            amplitude=pb.amplitude,
            latitude=pb.latitude,
            longitude=pb.longitude,
            altitude=pb.altitude,
            node_id=pb.base_packet.node_id,
            timestamp=pb.base_packet.timestamp,
        )

    def _extract_error(self, pb: PbErrorPacket) -> ErrorData:
        return ErrorData(
            error_message=pb.error_message,
            node_id=pb.base_packet.node_id,
            timestamp=pb.base_packet.timestamp,
        )

    def _invoke_request_config(self, data: RequestConfigData) -> None:
        self._invoke_handlers(self._request_config_handlers, data)

    def _invoke_config(self, data: ConfigData) -> None:
        self._invoke_handlers(self._config_handlers, data)

    def _invoke_ping(self, data: PingData) -> None:
        self._invoke_handlers(self._ping_handlers, data)

    def _invoke_error(self, data: ErrorData) -> None:
        self._invoke_handlers(self._error_handlers, data)

    def _invoke_handlers(
        self,
        handlers: list[tuple[Callable[[T], None], bool]],
        data: T,
    ) -> None:
        to_remove = []
        for i, (cb, one_time) in enumerate(handlers):
            cb(data)
            if one_time:
                to_remove.append(i)
        for i in reversed(to_remove):
            handlers.pop(i)

    def _unregister_handler(
        self,
        handler_list: list[tuple[Callable[[T], None], bool]],
        handler_fn: Callable[[T], None],
    ) -> bool:
        for i, (cb, _once) in enumerate(handler_list):
            if cb == handler_fn:
                handler_list.pop(i)
                return True
        return False


def current_timestamp_us() -> int:
    """Return the current timestamp in microseconds."""
    import time

    return int(time.time() * 1_000_000)
