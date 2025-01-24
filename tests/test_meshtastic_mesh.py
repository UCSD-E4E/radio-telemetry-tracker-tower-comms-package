"""Tests for MeshtasticMeshInterface implementation."""

from unittest.mock import MagicMock, patch

import pytest

from radio_telemetry_tracker_tower_comms_package.mesh_interface import MeshConnectionError
from radio_telemetry_tracker_tower_comms_package.meshtastic_mesh import MeshtasticMeshInterface


@patch("meshtastic.serial_interface.SerialInterface")
def test_meshtastic_mesh_connect_success(mock_serial_interface: MagicMock) -> None:
    """Test successful connection to Meshtastic device."""
    # mock_serial_interface is a MagicMock
    mesh = MeshtasticMeshInterface(serial_device="test_device")
    # Attempt to connect
    mesh.connect()

    # Check that SerialInterface was instantiated
    mock_serial_interface.assert_called_once_with("test_device")


@pytest.mark.usefixtures("mock_serial_interface")
@patch("meshtastic.serial_interface.SerialInterface", side_effect=Exception("Port not found"))
def test_meshtastic_mesh_connect_failure() -> None:
    """Test handling of connection failure to Meshtastic device."""
    mesh = MeshtasticMeshInterface(serial_device="nonexistent")
    with pytest.raises(MeshConnectionError) as exc:
        mesh.connect()
    assert "Failed to connect" in str(exc.value)  # noqa: S101
