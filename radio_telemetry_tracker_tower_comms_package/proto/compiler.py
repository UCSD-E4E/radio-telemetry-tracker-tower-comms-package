"""Proto compiler module for on-demand protobuf compilation."""

import logging
from pathlib import Path

from grpc_tools import protoc

logger = logging.getLogger(__name__)


def ensure_proto_compiled() -> None:
    """Compile the protobuf file if needed."""

    def _handle_error(msg: str) -> None:
        logger.error(msg)
        raise RuntimeError(msg)

    proto_dir = Path(__file__).parent
    proto_file = proto_dir / "packets.proto"

    try:
        result = protoc.main(
            [
                "grpc_tools.protoc",
                f"--python_out={proto_dir}",
                f"--proto_path={proto_dir}",
                str(proto_file),
            ],
        )
        if result != 0:
            _handle_error(f"protoc returned non-zero status: {result}")

        logger.info("Protobuf successfully compiled.")
    except (OSError, ImportError, RuntimeError) as e:
        _handle_error(f"Failed to compile protobuf: {e}")
