#
# constants.py
#
# Copyright © 2020 Foundation Devices, Inc.
# Licensed under the "BSD-2-Clause Plus Patent License"
#

MAX_UINT32 = 0xffffffff
MAX_UINT64 = 0xffffffffffffffff

MAX_SEQUENCE_LENGTH = 8192
"""Maximum number of fragments accepted in a multi-part UR.

Legitimate payloads span at most a few hundred fragments, so this bound is
far above real use while preventing a hostile header's declared seq_len from
driving allocations proportional to it.
"""
