"""Tests for protobuf compilation and imports."""

import pytest


def test_proto_imports() -> None:
    """Test that protobuf modules can be imported and compilation function works."""
    try:
        from radio_telemetry_tracker_tower_comms_package.proto.compiler import (
            ensure_proto_compiled,
        )
        from radio_telemetry_tracker_tower_comms_package.proto.packets_pb2 import (
            MeshPacket,
        )

        # Verify we can instantiate a protobuf message
        msg = MeshPacket()
        assert isinstance(msg, MeshPacket)  # noqa: S101

        ensure_proto_compiled()
    except (ImportError, RuntimeError) as e:
        pytest.fail(f"Proto test failed: {e}")
