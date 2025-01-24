"""Tests for SimulatedMeshInterface implementation."""

from radio_telemetry_tracker_tower_comms_package.simulated_mesh import SimulatedMeshInterface

# Test constants
NODE1_ID = 1
NODE2_ID = 2
NODE1_NAME = "NodeOne"
NODE2_NAME = "NodeTwo"

def test_simulated_mesh_basic() -> None:
    """Test basic functionality of simulated mesh network with two nodes."""
    # Create two simulated nodes
    node1 = SimulatedMeshInterface(numeric_id=NODE1_ID, user_id=NODE1_NAME)
    node2 = SimulatedMeshInterface(numeric_id=NODE2_ID, user_id=NODE2_NAME)

    # Configure them as neighbors
    node1.configure_neighbors([NODE2_ID])
    node2.configure_neighbors([NODE1_ID])

    node1.connect()
    node2.connect()

    assert node1.get_numeric_node_id() == NODE1_ID  # noqa: S101
    assert node2.get_numeric_node_id() == NODE2_ID  # noqa: S101
    assert node1.get_user_id() == NODE1_NAME  # noqa: S101
    assert node2.get_user_id() == NODE2_NAME  # noqa: S101

    # Register callbacks to capture received data
    received_by_node1 = []
    received_by_node2 = []

    node1.register_packet_callback(lambda data: received_by_node1.append(data))
    node2.register_packet_callback(lambda data: received_by_node2.append(data))

    # Send a message from node1 -> node2
    node1.send_message(b"Hello from Node 1", destination=NODE2_ID)
    node2.poll_inbox()  # Simulate the receiving end picking up messages

    assert len(received_by_node2) == 1  # noqa: S101
    assert received_by_node2[0] == b"Hello from Node 1"  # noqa: S101

    # Send a broadcast from node2 -> all neighbors
    node2.send_message(b"Broadcast from Node 2", destination=None)
    node1.poll_inbox()  # node1 picks up the broadcast

    assert len(received_by_node1) == 1  # noqa: S101
    assert received_by_node1[0] == b"Broadcast from Node 2"  # noqa: S101

    node1.close()
    node2.close()
