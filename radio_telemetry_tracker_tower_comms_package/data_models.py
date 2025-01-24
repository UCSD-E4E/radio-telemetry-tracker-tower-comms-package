"""Data models for radio telemetry configuration and communication."""

from dataclasses import dataclass


@dataclass
class PositionData:
    """Geographic position data for a node in the mesh network."""

    node_id: int
    latitude: float
    longitude: float
    altitude: float
    timestamp: int | None = None


@dataclass
class RequestConfigData:
    """Request for configuration data."""

    node_id: int | None = None
    timestamp: int | None = None


@dataclass
class ConfigData:
    """Configuration settings for radio telemetry operation."""

    gain: float
    sampling_rate: int
    center_frequency: int
    run_num: int
    enable_test_data: bool
    ping_width_ms: int
    ping_min_snr: int
    ping_max_len_mult: float
    ping_min_len_mult: float
    target_frequencies: list[int]
    node_id: int | None = None
    timestamp: int | None = None


@dataclass
class PingData:
    """Data from a detected radio ping."""

    frequency: int
    amplitude: float
    latitude: float
    longitude: float
    altitude: float
    node_id: int | None = None
    timestamp: int | None = None


@dataclass
class ErrorData:
    """Error information with message."""

    error_message: str
    node_id: int | None = None
    timestamp: int | None = None
