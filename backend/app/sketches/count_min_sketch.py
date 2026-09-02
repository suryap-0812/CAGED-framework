"""
Count-Min Sketch Implementation for Memory-Efficient Frequency Estimation.
"""

import hashlib
import math
import struct
from typing import Any, Dict, List, Optional
import numpy as np


class CountMinSketch:
    """
    Count-Min Sketch (CMS) probabilistic data structure.
    
    Provides sub-linear space frequency estimation for high-volume event streams.
    Guarantees:
        - Never underestimates: estimate(x) >= exact_count(x)
        - Error bound: estimate(x) <= exact_count(x) + epsilon * total_count
          with probability 1 - delta.
    """

    def __init__(
        self,
        width: Optional[int] = None,
        depth: Optional[int] = None,
        epsilon: Optional[float] = None,
        delta: Optional[float] = None,
        seed: int = 42,
    ):
        """
        Initializes Count-Min Sketch using either explicit (width, depth)
        or error bounds (epsilon, delta).
        """
        self.seed = seed
        
        if epsilon is not None and delta is not None:
            # Formula: width = e / epsilon, depth = ln(1 / delta)
            self.epsilon = float(epsilon)
            self.delta = float(delta)
            self.width = int(math.ceil(math.e / self.epsilon))
            self.depth = int(math.ceil(math.log(1.0 / self.delta)))
        elif width is not None and depth is not None:
            self.width = int(width)
            self.depth = int(depth)
            self.epsilon = math.e / self.width
            self.delta = math.exp(-self.depth)
        else:
            # Default configuration: width=272 (epsilon ~ 0.01), depth=5 (delta ~ 0.01)
            self.width = 272
            self.depth = 5
            self.epsilon = 0.01
            self.delta = 0.01

        if self.width < 1 or self.depth < 1:
            raise ValueError("Width and depth must be positive integers.")

        # Matrix: depth x width array of float64 counters
        self.matrix = np.zeros((self.depth, self.width), dtype=np.float64)
        self.total_count: float = 0.0
        
        # Precompute row hash seeds for deterministic hashing
        self._hash_seeds: List[bytes] = [
            struct.pack(">I", (self.seed + i * 10007) & 0xFFFFFFFF) for i in range(self.depth)
        ]

    def _hash(self, item: str, row: int) -> int:
        """
        Computes deterministic hash column index for a given item and matrix row.
        """
        item_bytes = item.encode("utf-8")
        h = hashlib.md5(self._hash_seeds[row] + item_bytes).digest()
        # Extract 32-bit int from md5 digest
        val = struct.unpack(">I", h[:4])[0]
        return val % self.width

    def update(self, item: str, count: float = 1.0) -> None:
        """
        Increments the frequency of an item across all depth rows.
        
        Args:
            item: String key to track.
            count: Amount to increment (default: 1.0).
        """
        if count < 0:
            raise ValueError("Count-Min Sketch update count must be non-negative.")

        for r in range(self.depth):
            c = self._hash(item, r)
            self.matrix[r, c] += count

        self.total_count += count

    def estimate(self, item: str) -> float:
        """
        Estimates the frequency of an item.
        
        Returns:
            Minimum count observed across all row hashes (upper-bound estimate).
        """
        min_val = float("inf")
        for r in range(self.depth):
            c = self._hash(item, r)
            val = self.matrix[r, c]
            if val < min_val:
                min_val = val
        return min_val if min_val != float("inf") else 0.0

    def reset(self) -> None:
        """Zeroes out the sketch matrix and total count."""
        self.matrix.fill(0.0)
        self.total_count = 0.0

    def memory_bytes(self) -> int:
        """Returns total memory consumption of the sketch matrix in bytes."""
        return self.matrix.nbytes

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the sketch state to a JSON-serializable dictionary."""
        return {
            "width": self.width,
            "depth": self.depth,
            "epsilon": self.epsilon,
            "delta": self.delta,
            "seed": self.seed,
            "total_count": self.total_count,
            "matrix": self.matrix.tolist(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CountMinSketch":
        """Instantiates a CountMinSketch object from a serialized dictionary."""
        cms = cls(
            width=data["width"],
            depth=data["depth"],
            seed=data.get("seed", 42),
        )
        cms.epsilon = data["epsilon"]
        cms.delta = data["delta"]
        cms.total_count = float(data["total_count"])
        cms.matrix = np.array(data["matrix"], dtype=np.float64)
        return cms
