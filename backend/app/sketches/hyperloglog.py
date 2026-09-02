"""
HyperLogLog Implementation for Memory-Efficient Cardinality & Unique-User Estimation.
"""

import hashlib
import math
import struct
from typing import Any, Dict, List, Optional
import numpy as np


def _alpha_m(m: int) -> float:
    """Computes the alpha bias-correction constant for m registers."""
    if m == 16:
        return 0.673
    elif m == 32:
        return 0.697
    elif m == 64:
        return 0.709
    else:
        return 0.7213 / (1.0 + 1.079 / m)


def _clz64(val: int) -> int:
    """Counts leading zeros in a 64-bit integer."""
    if val == 0:
        return 64
    return 64 - val.bit_length()


class HyperLogLog:
    """
    HyperLogLog (HLL) cardinality estimation algorithm.
    
    Provides sub-linear space estimation of unique elements (e.g. unique user hashes).
    Features:
        - Configurable precision p in range [4, 16] (default p=14 -> 16,384 registers)
        - Fixed memory consumption (e.g. ~16 KB for p=14)
        - Mergeability across parallel stream workers
    """

    def __init__(self, p: int = 14, seed: int = 42):
        """
        Args:
            p: Precision parameter (4 <= p <= 16). Number of registers m = 2^p.
            seed: Deterministic seed for hashing.
        """
        if not (4 <= p <= 16):
            raise ValueError("Precision p must be an integer between 4 and 16.")

        self.p = p
        self.m = 1 << p  # 2^p registers
        self.seed = seed
        self.alpha = _alpha_m(self.m)
        
        # Registers: array of uint8 values (0 to 64)
        self.registers = np.zeros(self.m, dtype=np.uint8)
        self._seed_bytes = struct.pack(">I", seed & 0xFFFFFFFF)

    def _hash64(self, item: str) -> int:
        """Computes deterministic 64-bit unsigned integer hash for item."""
        digest = hashlib.sha256(self._seed_bytes + item.encode("utf-8")).digest()
        # Extract first 64 bits as big-endian unsigned integer
        val = struct.unpack(">Q", digest[:8])[0]
        return val

    def add(self, item: str) -> None:
        """
        Adds an item to the HyperLogLog sketch.
        
        Args:
            item: String identifier (e.g. user_hash).
        """
        x = self._hash64(item)
        
        # Register index j is the first p bits
        j = x >> (64 - self.p)
        
        # Remaining (64 - p) bits
        w = x & ((1 << (64 - self.p)) - 1)
        
        # Count leading zeros in w within (64 - p) bit field plus 1
        rho = _clz64(w) - self.p + 1
        rho = max(1, min(rho, 64 - self.p + 1))
        
        # Update register with maximum leading zeros
        if rho > self.registers[j]:
            self.registers[j] = rho

    def estimate(self) -> float:
        """
        Estimates the cardinality (unique element count) from registers.
        
        Returns:
            Estimated unique item count as float.
        """
        # Harmonic mean of 2^(-M[j])
        inv_sum = np.sum(2.0 ** (-self.registers.astype(np.float64)))
        
        raw_est = self.alpha * (self.m ** 2) / inv_sum
        
        # Small range correction
        if raw_est <= 2.5 * self.m:
            zero_registers = np.count_nonzero(self.registers == 0)
            if zero_registers > 0:
                est = self.m * math.log(float(self.m) / float(zero_registers))
            else:
                est = raw_est
        elif raw_est > (1.0 / 32.0) * (2 ** 64):
            # Large range correction
            est = - (2 ** 64) * math.log(1.0 - (raw_est / (2 ** 64)))
        else:
            est = raw_est

        return round(est, 2)

    def merge(self, other: "HyperLogLog") -> "HyperLogLog":
        """
        Merges another HyperLogLog sketch into a new combined HyperLogLog sketch.
        Both sketches must have the same precision p.
        """
        if self.p != other.p:
            raise ValueError(f"Cannot merge HyperLogLog sketches with different precision ({self.p} vs {other.p}).")

        merged_hll = HyperLogLog(p=self.p, seed=self.seed)
        merged_hll.registers = np.maximum(self.registers, other.registers)
        return merged_hll

    def reset(self) -> None:
        """Zeroes out all registers."""
        self.registers.fill(0)

    def memory_bytes(self) -> int:
        """Returns memory occupied by register array in bytes."""
        return self.registers.nbytes

    def expected_relative_error(self) -> float:
        """Returns theoretical standard error: 1.04 / sqrt(m)."""
        return 1.04 / math.sqrt(self.m)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes sketch state to dictionary."""
        return {
            "p": self.p,
            "m": self.m,
            "seed": self.seed,
            "registers": self.registers.tolist(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HyperLogLog":
        """Reconstructs HyperLogLog sketch from dictionary."""
        hll = cls(p=data["p"], seed=data.get("seed", 42))
        hll.registers = np.array(data["registers"], dtype=np.uint8)
        return hll
