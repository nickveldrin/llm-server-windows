#!/usr/bin/env python3
import struct

# This is the EXACT approach from the Linux bash version
MMPROJ_PATH = r"E:\AI\01-TextModels\Qwen3.5-27B-UD-mmproj-F16.gguf"

KV_FIXED = {0:1,1:1,2:2,3:2,4:4,5:4,6:4,7:1,10:8,11:8,12:8}

try:
    with open(MMPROJ_PATH,"rb") as f:
        if f.read(4) != b"GGUF":
            sys.exit(1)

        f.read(4)  # version
        struct.unpack("<Q", f.read(8))  # tensor count
        kvc = struct.unpack("<Q", f.read(8))[0]  # kv count


        for _i in range(kvc):
            kl = struct.unpack("<Q", f.read(8))[0]
            key = f.read(kl).decode("utf-8","replace")
            vt = struct.unpack("<I", f.read(4))[0]


            if vt == 8:  # STRING
                sl = struct.unpack("<Q", f.read(8))[0]
                val = f.read(sl).decode("utf-8","replace")
                if key == "general.name":
                    break
            elif vt == 9:  # ARRAY
                at = struct.unpack("<I", f.read(4))[0]
                al = struct.unpack("<Q", f.read(8))[0]
                if at in KV_FIXED:
                    f.read(al * KV_FIXED[at])
                elif at == 8:
                    for _ in range(al):
                        f.read(struct.unpack("<Q", f.read(8))[0])
                else:
                    break
            elif vt in KV_FIXED:
                f.read(KV_FIXED[vt])
            else:
                break
except Exception:
    import traceback
    traceback.print_exc()
