import base64
import string


ALFABETO128 = ''.join(chr(i) for i in range(128))  # muito simples, cuidado com caracteres de controle

def to_base128(bytes_in: bytes) -> str:
    # trata os bytes como número grande e converte para base128 string
    num = int.from_bytes(bytes_in, 'big')
    if num == 0:
        return ALFABETO128[0]
    digits = []
    base = 128
    while num:
        digits.append(ALFABETO128[num % base])
        num //= base
    return ''.join(reversed(digits))

def from_base128(s: str) -> bytes:
    base = 128
    num = 0
    for ch in s:
        num = num*base + ALFABETO128.index(ch)
    # calcular quantos bytes precisamos
    length = (num.bit_length() + 7)//8
    return num.to_bytes(length, 'big')

def encode_simple(text: str) -> str:
    b = text.encode('utf-8')
    b64 = base64.b64encode(b)
    return to_base128(b64)

def decode_simple(encoded: str) -> str:
    b64 = from_base128(encoded)
    orig_bytes = base64.b64decode(b64)
    return orig_bytes.decode('utf-8')

if __name__ == "__main__":
    texto = "Olá! Isto é um teste."
    # texto = "aeds"
    enc = encode_simple(texto)
    print("Encodificado:", enc)
    dec = decode_simple(enc)
    print("Decodificado:", dec)
