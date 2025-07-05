import json
import sys

from libs import options

with open(sys.argv[3], 'wb') as f: 
    f.write(
        options.fernet.encrypt(
            json.dumps(
                {
                    'host': sys.argv[1], 
                    'port': int(sys.argv[2]), 
                }
            ).encode()
        )
    )
