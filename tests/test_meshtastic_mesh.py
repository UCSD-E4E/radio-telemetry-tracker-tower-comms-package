"""Tests for MeshtasticMeshInterface implementation."""

from unittest.mock import MagicMock, create_autospec, patch

import pytest
from meshtastic.serial_interface import SerialInterface

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


def test_meshtastic_mesh_connect_failure() -> None:
    """Test handling of connection failure to Meshtastic device."""
    with patch("meshtastic.serial_interface.SerialInterface", create_autospec(SerialInterface)) as mock:
        mock.side_effect = Exception("Port not found")
        mesh = MeshtasticMeshInterface(serial_device="nonexistent")
        with pytest.raises(MeshConnectionError) as exc:
            mesh.connect()
        assert "Failed to connect" in str(exc.value)  # noqa: S101
