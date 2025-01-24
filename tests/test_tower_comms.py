"""Tests for TowerComms class and mesh network communication."""

from collections.abc import Generator

import pytest

from radio_telemetry_tracker_tower_comms_package.data_models import (
    ConfigData,
    ErrorData,
    PingData,
    RequestConfigData,
)
from radio_telemetry_tracker_tower_comms_package.tower_comms import (
    NodeConfig,
    TowerComms,
)

# Test constants
NODE1_ID = 1
NODE2_ID = 2
NODE1_NAME = "NodeOne"
NODE2_NAME = "NodeTwo"
TEST_GAIN = 2.0
TEST_SAMPLE_RATE = 48000
TEST_CENTER_FREQ = 915000000
TEST_RUN_NUM = 999
TEST_PING_WIDTH = 15
TEST_MIN_SNR = 5
TEST_MAX_LEN_MULT = 2.0
TEST_MIN_LEN_MULT = 1.0
TEST_TARGET_FREQS = [100, 200, 300]
TEST_PING_FREQ = 440
TEST_PING_AMP = 0.75
TEST_PING_LAT = 37.0
TEST_PING_LON = -122.0
TEST_PING_ALT = 50.0


@pytest.fixture
def two_simulated_nodes() -> Generator[tuple[TowerComms, TowerComms]]:
    """Creates two TowerComms objects using simulated interfaces, set up as neighbors."""

    # Node 1
    def on_ack_success_1(packet_id: int) -> None:
        pass  # for demonstration, do nothing

    def on_ack_failure_1(packet_id: int) -> None:
        pass

    config1 = NodeConfig(
        interface_type="simulated",
        numeric_id=1,
        user_id="NodeOne",
    )
    tower1 = TowerComms(config1, on_ack_success_1, on_ack_failure_1)

    # Node 2
    def on_ack_success_2(packet_id: int) -> None:
        pass

    def on_ack_failure_2(packet_id: int) -> None:
        pass

    config2 = NodeConfig(
        interface_type="simulated",
        numeric_id=2,
        user_id="NodeTwo",
    )
    tower2 = TowerComms(config2, on_ack_success_2, on_ack_failure_2)

    # Configure them as neighbors
    tower1.mesh_interface.configure_neighbors([2])
    tower2.mesh_interface.configure_neighbors([1])

    # Start both
    tower1.start()
    tower2.start()

    yield tower1, tower2  # Provide them to the tests

    # Clean up
    tower1.stop()
    tower2.stop()


def test_tower_comms_request_config(
    two_simulated_nodes: tuple[TowerComms, TowerComms],
) -> None:
    """Test sending and receiving configuration request messages between towers."""
    tower1, tower2 = two_simulated_nodes

    received_data = []

    def handle_request_config(data: RequestConfigData) -> None:
        received_data.append(data)

    # tower2 will handle request_config from tower1
    tower2.register_request_config_handler(handle_request_config)

    # tower1 sends a request config -> tower2
    tower1.send_request_config(destination=2)

    # For the simulated mesh, we must poll to let the message be delivered
    tower2.mesh_interface.poll_inbox()

    assert len(received_data) == 1  # noqa: S101
    req = received_data[0]
    assert isinstance(req, RequestConfigData)  # noqa: S101
    assert req.node_id == 1  # node_id from tower1  # noqa: S101
    assert req.timestamp is not None  # the code sets a timestamp  # noqa: S101


def test_tower_comms_config(two_simulated_nodes: tuple[TowerComms, TowerComms]) -> None:
    """Test sending and receiving configuration data between towers."""
    tower1, tower2 = two_simulated_nodes

    received_data = []

    def handle_config(data: ConfigData) -> None:
        received_data.append(data)

    tower2.register_config_handler(handle_config)

    config_to_send = ConfigData(
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
    )

    tower1.send_config(config_to_send, destination=2)

    # Poll
    tower2.mesh_interface.poll_inbox()

    assert len(received_data) == 1  # noqa: S101
    cfg = received_data[0]
    assert cfg.run_num == TEST_RUN_NUM  # noqa: S101
    assert cfg.target_frequencies == TEST_TARGET_FREQS  # noqa: S101
    assert cfg.node_id == NODE1_ID  # from tower1  # noqa: S101
    assert cfg.timestamp is not None  # the code sets a timestamp  # noqa: S101


def test_tower_comms_ping(two_simulated_nodes: tuple[TowerComms, TowerComms]) -> None:
    """Test sending and receiving ping data between towers."""
    tower1, tower2 = two_simulated_nodes

    received_data = []

    def handle_ping(data: PingData) -> None:
        received_data.append(data)

    tower2.register_ping_handler(handle_ping)

    ping_to_send = PingData(
        frequency=TEST_PING_FREQ,
        amplitude=TEST_PING_AMP,
        latitude=TEST_PING_LAT,
        longitude=TEST_PING_LON,
        altitude=TEST_PING_ALT,
    )

    tower1.send_ping(ping_to_send, destination=2)

    # Poll
    tower2.mesh_interface.poll_inbox()
    assert len(received_data) == 1  # noqa: S101
    ping = received_data[0]
    assert ping.frequency == TEST_PING_FREQ  # noqa: S101
    assert ping.amplitude == TEST_PING_AMP  # noqa: S101
    assert ping.node_id == 1  # noqa: S101
    assert ping.timestamp is not None  # noqa: S101


def test_tower_comms_error(two_simulated_nodes: tuple[TowerComms, TowerComms]) -> None:
    """Test sending and receiving error messages between towers."""
    tower1, tower2 = two_simulated_nodes

    received_data = []

    def handle_error(data: ErrorData) -> None:
        received_data.append(data)

    tower2.register_error_handler(handle_error)

    error_to_send = ErrorData(
        error_message="Test error occurred",
    )

    tower1.send_error(error_to_send, destination=2)

    # Poll
    tower2.mesh_interface.poll_inbox()
    assert len(received_data) == 1  # noqa: S101
    err = received_data[0]
    assert err.error_message == "Test error occurred"  # noqa: S101
    assert err.node_id == NODE1_ID  # noqa: S101
    assert err.timestamp is not None  # noqa: S101

