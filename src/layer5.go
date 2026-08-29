package main

import (
	"bytes"
	"crypto/aes"
	"crypto/cipher"
	"encoding/ascii85"
	"fmt"
	"log"
	"os"
	"strings"
)

// Authored by Claude; human implementation tbc.
func aesKeyUnwrap(kek, iv, wrapped []byte) ([]byte, error) {
	if len(wrapped)%8 != 0 || len(wrapped) < 16 {
		return nil, fmt.Errorf("invalid wrapped key length")
	}
	n := len(wrapped)/8 - 1

	block, err := aes.NewCipher(kek)
	if err != nil {
		return nil, err
	}

	A := make([]byte, 8)
	copy(A, wrapped[:8])

	R := make([][]byte, n+1)
	for i := 1; i <= n; i++ {
		R[i] = make([]byte, 8)
		copy(R[i], wrapped[i*8:(i+1)*8])
	}

	buf := make([]byte, 16)
	dec := make([]byte, 16)
	for j := 5; j >= 0; j-- {
		for i := n; i >= 1; i-- {
			t := uint64(n*j + i)
			AT := make([]byte, 8)
			copy(AT, A)
			for k := 0; k < 8; k++ {
				AT[7-k] ^= byte(t >> (8 * k))
			}
			copy(buf[:8], AT)
			copy(buf[8:], R[i])
			block.Decrypt(dec, buf)
			A = append([]byte{}, dec[:8]...)
			R[i] = append([]byte{}, dec[8:]...)
		}
	}

	if !bytes.Equal(A, iv) {
		return nil, fmt.Errorf("key unwrap integrity check failed")
	}

	out := make([]byte, n*8)
	for i := 1; i <= n; i++ {
		copy(out[(i-1)*8:i*8], R[i])
	}
	return out, nil
}

const (
	// First 32 bytes: The 256-bit key encrypting key (KEK).
	kekLen    = 32
	// Next 8 bytes: The 64-bit initialization vector (IV) for the wrapped key.
	kivLen    = 8
	// Next 40 bytes: The wrapped (encrypted) key. When decrypted, this will become the 256-bit encryption key.
	keyLen    = 40
	// Next 16 bytes: The 128-bit initialization vector (IV) for the encrypted payload.
	ivLen     = 16
	// All remaining bytes: The encrypted payload.
	headerLen = kekLen + kivLen + keyLen + ivLen
)

func readInput() []byte {
	b, err := os.ReadFile("./parts/5.txt")
	if err != nil { log.Fatalf("could not read input: %v", err) }
	contents := string(b)

	_, contents, found := strings.Cut(contents, "<~")
	if !found { log.Fatal("could not find prefix <~") }
	contents, _, found = strings.CutLast(contents, "~>")
	if !found { log.Fatal("could not find suffix ~>") }

	return []byte(contents)
}

func decode(rawData []byte) []byte {
	dest := make([]byte, len(rawData))

	ndst, nsrc, err := ascii85.Decode(dest, rawData, true)
	if err != nil { log.Fatalf("ascii85 decode: %v", err) }
	if nsrc != len(rawData) { log.Fatalf("ascii85 decode: read %d of %d bytes", nsrc, len(rawData)) }

	return dest[:ndst]
}

func main() {
	rawData := readInput()
	decoded := decode(rawData)

	kek := decoded[:kekLen]
	kiv := decoded[kekLen : kekLen+kivLen]
	wrappedKey := decoded[kekLen+kivLen : kekLen+kivLen+keyLen]
	iv := decoded[kekLen+kivLen+keyLen : headerLen]
	payload := decoded[headerLen:]

	key, err := aesKeyUnwrap(kek, kiv, wrappedKey)
	if err != nil { log.Fatalf("unwrapping key: %v", err) }

	block, err := aes.NewCipher(key)
	if err != nil { log.Fatalf("creating cipher: %v", err) }

	stream := cipher.NewCTR(block, iv)
	dest := make([]byte, len(payload))
	stream.XORKeyStream(dest, payload)

	if err := os.WriteFile("parts/6.txt", dest, 0644); err != nil { log.Fatalf("writing output: %v", err) }
}