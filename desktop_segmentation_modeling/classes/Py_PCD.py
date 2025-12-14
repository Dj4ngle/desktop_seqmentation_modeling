import numpy as np
import struct


class PointCloudPCD:
    def __init__(self, metadata, pc_data):
        self._metadata = metadata
        self.pc_data = pc_data

    @classmethod
    def from_path(cls, file_path):
        metadata, offset = _parse_pcd_header(file_path)
        dtype = _fields_to_dtype(metadata)
        points = metadata['points']
        data_type = metadata['data'].lower()

        with open(file_path, "rb") as f:
            f.seek(offset)
            if data_type == 'binary':
                data = f.read()
                arr = np.frombuffer(data, dtype=dtype, count=points)
            elif data_type == 'ascii':
                lines = f.read().decode('utf-8').splitlines()
                arr = np.loadtxt(lines, dtype=dtype, max_rows=points)
            else:
                raise NotImplementedError("Only 'binary' and 'ascii' data support implemented.")
        return cls(metadata, arr)

    def get_metadata(self):
        return self._metadata.copy()

    def save_pcd(self, file_path, data_type='binary'):
                """
                Save the point cloud to a PCD file using the current metadata and pc_data.
                Only 'binary' and 'ascii' save supported.
                """
                import numpy as np
                header = []
                md = self._metadata
                header.append(f"# .PCD v{md['version']}")
                header.append(f"VERSION {md['version']}")
                header.append("FIELDS " + ' '.join(md['fields']))
                header.append("SIZE " + ' '.join(map(str, md['size'])))
                header.append("TYPE " + ' '.join(md['type']))
                header.append("COUNT " + ' '.join(map(str, md['count'])))
                header.append(f"WIDTH {md['width']}")
                header.append(f"HEIGHT {md['height']}")
                header.append("VIEWPOINT " + ' '.join(map(str, md['viewpoint'])))
                header.append(f"POINTS {md['points']}")
                header.append(f"DATA {data_type}")
                header_str = '\n'.join(header) + '\n'

                with open(file_path, 'wb') as f:
                    f.write(header_str.encode('utf-8'))
                    if data_type == 'binary':
                        f.write(self.pc_data.tobytes())
                    elif data_type == 'ascii':
                        # Convert numpy structured/record array to text rows
                        # Flatten to regular array, then format
                        arr = self.pc_data.view(np.float32).reshape(-1, len(md['fields']))
                        np.savetxt(f, arr, fmt='%f')
                    else:
                        raise NotImplementedError(f"Unsupported PCD save type: {data_type}")


def _parse_pcd_header(file_path):
    """Parse metadata from PCD header. Returns (dict, data_offset)."""
    metadata = {}
    fields = []
    count = []
    size = []
    types = []
    with open(file_path, "rb") as f:
        offset = 0
        while True:
            line = f.readline()
            if not line:
                break
            lstr = line.decode('utf-8').strip()
            offset += len(line)
            if lstr.startswith('#'):
                continue
            if lstr == 'DATA binary':
                metadata['data'] = 'binary'
                break
            if lstr == 'DATA ascii':
                metadata['data'] = 'ascii'
                break
            key, *vals = lstr.split()
            key = key.lower()
            v = vals
            if key == 'version':
                metadata['version'] = float(v[0])
            elif key == 'fields':
                fields = v
            elif key == 'size':
                size = [int(x) for x in v]
            elif key == 'count':
                count = [int(x) for x in v]
            elif key == 'type':
                types = v
            elif key == 'width':
                metadata['width'] = int(v[0])
            elif key == 'height':
                metadata['height'] = int(v[0])
            elif key == 'viewpoint':
                metadata['viewpoint'] = list(map(float, v))
            elif key == 'points':
                metadata['points'] = int(v[0])
            else:
                pass  # Ignore

        metadata['fields'] = fields
        metadata['count'] = count or [1] * len(fields)
        metadata['size'] = size
        metadata['type'] = types

    return metadata, offset


def _fields_to_dtype(metadata):
    """Convert pcd header fields/types to numpy dtype."""
    _type_map = {
        'F': {4: np.float32, 8: np.float64},
        'U': {1: np.uint8, 2: np.uint16, 4: np.uint32},
        'I': {1: np.int8, 2: np.int16, 4: np.int32}
    }

    fields = metadata['fields']
    types = metadata['type']
    sizes = metadata['size']
    counts = metadata['count'] if metadata.get('count') else [1] * len(fields)

    dtype_list = []
    for f, t, s, c in zip(fields, types, sizes, counts):
        np_type = _type_map[t][s]
        if c == 1:
            dtype_list.append((f, np_type))
        else:
            dtype_list.append((f, np_type, (c,)))
    return np.dtype(dtype_list)

