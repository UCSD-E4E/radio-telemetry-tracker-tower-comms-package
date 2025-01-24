# Radio Telemetry Tracker Tower Communications Package (Comms Package)

The **Radio Telemetry Tracker Tower Communications Package** is a Python-based library designed to facilitate mesh network communication between radio telemetry towers using Meshtastic devices. It provides a robust framework for configuration management, ping data transmission, and error handling between towers in a distributed network.

> Note: This package is intended as a shared component for tower-based radio telemetry systems. It provides the communication infrastructure between towers but is not meant for standalone use.

## Table of Contents
- [Radio Telemetry Tracker Tower Communications Package (Comms Package)](#radio-telemetry-tracker-tower-communications-package-comms-package)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Usage](#usage)
  - [Message Types](#message-types)
  - [Development](#development)
  - [License](#license)

## Overview

This package provides:

- **Mesh Network Communication**: Interface with Meshtastic devices for tower-to-tower communication
- **Message Types**: Protobuf-defined messages for configuration, pings, and errors
- **Acknowledgments**: Built-in support for message acknowledgments and retries
- **Position Tracking**: Integration with GPS data from Meshtastic devices
- **Simulation Support**: Simulated mesh interface for development and testing

## Prerequisites

- Python 3.13
- Poetry for dependency management
- Meshtastic-compatible device for real deployment
- Protocol Buffers compiler for development

## Installation

1. Add as a dependency to your project:
    ```bash
    poetry add git+https://github.com/UCSD-E4E/radio-telemetry-tracker-tower-comms-package.git
    ```
2. Or clone for development:
    ```bash
    bash
    git clone https://github.com/UCSD-E4E/radio-telemetry-tracker-tower-comms-package.git

    cd radio-telemetry-tracker-tower-comms-package

    poetry install
    ```

## Configuration

The library supports two interface types:

1. **Meshtastic Interface**:
   ```python
    from radio_telemetry_tracker_tower_comms_package import NodeConfig, TowerComms
    
    config = NodeConfig(
    interface_type="meshtastic",
    device="/dev/ttyUSB0", # Serial port for Meshtastic device
    )
    ```
2. **Simulated Interface** (for testing):
    ```python
    from radio_telemetry_tracker_tower_comms_package import NodeConfig, TowerComms

    config = NodeConfig(
    interface_type="simulated",
    numeric_id=1, # Unique node ID
    user_id="Tower1" # Human-readable name
    )

    ```

## Usage

Basic usage pattern:

1. **Initialize communications**:
    ```python
    from radio_telemetry_tracker_tower_comms_package import TowerComms, NodeConfig

    def on_ack_success(packet_id: int):
        print(f"Packet {packet_id} acknowledged")
    
    def on_ack_failure(packet_id: int):
        print(f"Packet {packet_id} failed")
    
    config = NodeConfig(interface_type="meshtastic", device="/dev/ttyUSB0")
    comms = TowerComms(config, on_ack_success, on_ack_failure)
    ```
2. **Register message handlers**:
    ```python
    def handle_ping(data: PingData):
        print(f"Ping received from {data.node_id} at freq {data.frequency}")
    
    comms.register_ping_handler(handle_ping)
    ```
3. **Start communication**:
    ```python
    comms.start() # Opens the mesh interface
    ```
4. **Send messages**:
    ```python
    comms.send_request_config(destination=2, want_ack=True)
    
    ping_data = PingData(frequency=915000000, amplitude=0.8, latitude=32.7, longitude=-117.1, altitude=100)
    comms.send_ping(ping_data, destination=None) # Broadcast

    ```
5. **Stop communication**:
    ```python
    comms.stop() # Closes the mesh interface
    ```


## Message Types

- **ConfigData**: Tower configuration parameters
- **PingData**: Radio ping detection data with GPS coordinates
- **ErrorData**: Error messages and diagnostics
- **RequestConfigData**: Configuration request messages

## Development

1. Install development dependencies:
    ```bash
    poetry install --with dev
    ```
2. Run tests:
    ```bash
    poetry run pytest
    ```
3. Check code style:
    ```bash
    poetry run ruff check . --fix
    ```

## License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.