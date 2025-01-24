"""Tests for data model classes used in tower communications."""

from radio_telemetry_tracker_tower_comms_package.data_models import (
    ConfigData,
    ErrorData,
    PingData,
    PositionData,
    RequestConfigData,
)

# Test constants
TEST_NODE_ID = 123
TEST_LATITUDE = 32.7157
TEST_LONGITUDE = -117.1611
TEST_ALTITUDE = 100.0
TEST_TIMESTAMP = 123456789
TEST_REQUEST_TIMESTAMP = 9999999
TEST_ERROR_NODE_ID = 7
TEST_PING_NODE_ID = 99
TEST_CONFIG_NODE_ID = 42
TEST_GAIN = 1.5
TEST_SAMPLE_RATE = 1000
TEST_CENTER_FREQ = 915000000
TEST_RUN_NUM = 2
TEST_PING_WIDTH = 10.0
TEST_MIN_SNR = 3.0
TEST_MAX_LEN_MULT = 1.5
TEST_MIN_LEN_MULT = 0.5
TEST_TARGET_FREQS = [200, 250, 300]
TEST_PING_FREQ = 440.0
TEST_PING_AMP = 0.8
TEST_PING_LAT = 37.7749
TEST_PING_LON = -122.4194
TEST_PING_ALT = 10.0
TEST_PING_TIMESTAMP = 111111111
TEST_ERROR_MSG = "Something went wrong!"
TEST_ERROR_TIMESTAMP = 123


def test_position_data() -> None:
    """Test PositionData creation and attribute access."""
    pos = PositionData(
        node_id=TEST_NODE_ID,
        latitude=TEST_LATITUDE,
        longitude=TEST_LONGITUDE,
        altitude=TEST_ALTITUDE,
    )
    assert pos.node_id == TEST_NODE_ID  # noqa: S101
    assert pos.latitude == TEST_LATITUDE  # noqa: S101
    assert pos.longitude == TEST_LONGITUDE  # noqa: S101
    assert pos.altitude == TEST_ALTITUDE  # noqa: S101
    assert pos.timestamp is None  # noqa: S101


def test_request_config_data() -> None:
    """Test RequestConfigData creation and attribute access."""
    req = RequestConfigData(node_id=None, timestamp=TEST_REQUEST_TIMESTAMP)
    assert req.node_id is None  # noqa: S101
    assert req.timestamp == TEST_REQUEST_TIMESTAMP  # noqa: S101


def test_config_data() -> None:
    """Test ConfigData creation and attribute access."""
    cfg = ConfigData(
        gain=TEST_GAIN,
        sampling_rate=TEST_SAMPLE_RATE,
        center_frequency=TEST_CENTER_FREQ,
        run_num=TEST_RUN_NUM,
        enable_test_data=True,
        ping_width_ms=TEST_PING_WIDTH,
        ping_min_snr=TEST_MIN_SNR,
        ping_max_len_mult=TEST_MAX_LEN_MULT,
        ping_min_len_mult=TEST_MIN_LEN_MULT,
        target_frequencies=TEST_TARGET_FREQS,
        node_id=TEST_CONFIG_NODE_ID,
        timestamp=TEST_TIMESTAMP,
    )
    assert cfg.enable_test_data is True  # noqa: S101
    assert cfg.run_num == TEST_RUN_NUM  # noqa: S101
    assert cfg.target_frequencies == TEST_TARGET_FREQS  # noqa: S101


def test_ping_data() -> None:
    """Test PingData creation and attribute access."""
    ping = PingData(
        frequency=TEST_PING_FREQ,
        amplitude=TEST_PING_AMP,
        latitude=TEST_PING_LAT,
        longitude=TEST_PING_LON,
        altitude=TEST_PING_ALT,
        node_id=TEST_PING_NODE_ID,
        timestamp=TEST_PING_TIMESTAMP,
    )
    assert ping.frequency == TEST_PING_FREQ  # noqa: S101
    assert ping.node_id == TEST_PING_NODE_ID  # noqa: S101
    assert ping.timestamp == TEST_PING_TIMESTAMP  # noqa: S101


def test_error_data() -> None:
    """Test ErrorData creation and attribute access."""
    err = ErrorData(
        error_message=TEST_ERROR_MSG,
        node_id=TEST_ERROR_NODE_ID,
        timestamp=TEST_ERROR_TIMESTAMP,
    )
    assert err.error_message == TEST_ERROR_MSG  # noqa: S101
    assert err.node_id == TEST_ERROR_NODE_ID  # noqa: S101
    assert err.timestamp == TEST_ERROR_TIMESTAMP  # noqa: S101
