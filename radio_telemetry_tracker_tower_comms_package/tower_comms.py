@dataclass
class NodeConfig:
    interface_type: Literal["meshtastic", "simulated"]
    device: str | None = None


class TowerComms(Transceiver):
    def __init__(
        self,
        config: NodeConfig,
        on_ack_success: Callable[[int], None],
        on_ack_failure: Callable[[int], None],
    ):
        if config.interface_type == "serial":
            self.interface = MeshtasticMeshInterface(config.device)
        elif config.interface_type == "simulated":
            self.interface = SimulatedMeshInterface()
        else:
            raise ValueError(f"Invalid interface type: {config.interface_type}")

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
        field = packet.WhichOneof("msg")
        handler_entry = self._packet_handlers.get(field)
        if not handler_entry:
            logger.debug("Received an unhandled packet type: %s", field)
            return

        extractor, handler = handler_entry
        data_object = extractor(getattr(packet, field))
        handler(data_object)

    def register_config_handler(
        self, handler: Callable[[ConfigData], None], one_time: bool = False
    ) -> None:
        self._config_handlers.append((handler, one_time))

    def unregister_config_handler(self, handler: Callable[[ConfigData], None]) -> bool:
        for cb, once in self._config_handlers:
            if cb == handler:
                self._config_handlers.remove((cb, once))
                return True
        return False

    def register_no_config_handler(
        self, handler: Callable[[NoConfigData], None], one_time: bool = False
    ) -> None:
        self._no_config_handlers.append((handler, one_time))

    def unregister_no_config_handler(
        self, handler: Callable[[NoConfigData], None]
    ) -> bool:
        for cb, once in self._no_config_handlers:
            if cb == handler:
                self._no_config_handlers.remove((cb, once))
                return True
        return False

    def register_ping_handler(
        self, handler: Callable[[PingData], None], one_time: bool = False
    ) -> None:
        self._ping_handlers.append((handler, one_time))

    def unregister_ping_handler(self, handler: Callable[[PingData], None]) -> bool:
        for cb, once in self._ping_handlers:
            if cb == handler:
                self._ping_handlers.remove((cb, once))
                return True
        return False

    def register_no_ping_handler(
        self, handler: Callable[[NoPingData], None], one_time: bool = False
    ) -> None:
        self._no_ping_handlers.append((handler, one_time))

    def unregister_no_ping_handler(self, handler: Callable[[NoPingData], None]) -> bool:
        for cb, once in self._no_ping_handlers:
            if cb == handler:
                self._no_ping_handlers.remove((cb, once))
                return True
        return False

    def register_request_config_handler(
        self, handler: Callable[[RequestConfigData], None], one_time: bool = False
    ) -> None:
        self._request_config_handlers.append((handler, one_time))

    def unregister_request_config_handler(
        self, handler: Callable[[RequestConfigData], None]
    ) -> bool:
        for cb, once in self._request_config_handlers:
            if cb == handler:
                self._request_config_handlers.remove((cb, once))
                return True
        return False

    def register_request_ping_handler(
        self, handler: Callable[[RequestPingData], None], one_time: bool = False
    ) -> None:
        self._request_ping_handlers.append((handler, one_time))

    def unregister_request_ping_handler(
        self, handler: Callable[[RequestPingData], None]
    ) -> bool:
        for cb, once in self._request_ping_handlers:
            if cb == handler:
                self._request_ping_handlers.remove((cb, once))
                return True
        return False

    def register_error_handler(
        self, handler: Callable[[ErrorData], None], one_time: bool = False
    ) -> None:
        self._error_handlers.append((handler, one_time))

    def unregister_error_handler(self, handler: Callable[[ErrorData], None]) -> bool:
        for cb, once in self._error_handlers:
            if cb == handler:
                self._error_handlers.remove((cb, once))
                return True
        return False
