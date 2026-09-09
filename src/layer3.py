from base64 import a85decode
from pathlib import Path
import itertools as it

PAYLOAD_HEADER = "==[ Payload ]==============================================="

def ascii85(text):
    return a85decode(text, adobe=True)

text = Path("parts/3.txt").read_text().replace("\r", "").replace("\n", "")
start = text.find("<~", text.find(PAYLOAD_HEADER))
end = text.find("~>", start) + 2
encoded = text[start:end]
encrypted = ascii85(encoded)

key = list(encrypted[:32])


def known_char(index, char):
    key[index % 32] = encrypted[index] ^ ord(char)


def known(index, str):
    for i in range(len(str)):
        known_char(index + i, str[i])


beginning = "==[ Layer 4/6: "

keys = list()
for i in range(0, len(beginning)):
    known_char(i, beginning[i])

known(18, "work")
known(28, "ic ")
known(63, "h")
known(1423, "col")
known(1494, "ission")
# known(0, "==[ Layer 4/6: Network Traffic ]============================")

display_key = " ".join(f"{c:02x}" for c in key)
CORRECT = "6c 24 84 8e 42 19 a8 e1 c5 db 57 65 b9 c6 14 9e a5 19 35 96 3b 39 7f a5 65 d1 fe 01 85 7d d9 4c"
print("KEY =   ", display_key)
if display_key != CORRECT:
    print("CORRECT:", CORRECT)

with open("parts/4.txt", "wb") as f:
    for chunk in it.batched(encrypted, 32):
        decrypted = list(chunk)
        for i in range(len(decrypted)):
            decrypted[i] = decrypted[i] ^ key[i]
        f.write(bytes(decrypted))

with open("parts/4.txt", "r") as f:
    text = f.read().strip()

with open("parts/4.txt", "w") as f:
    f.write(text)
