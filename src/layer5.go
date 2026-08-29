package main

import (
	"bytes"
	"crypto/aes"
	"crypto/cipher"
	"encoding/ascii85"
	"fmt"
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

type Payload struct {
	// First 32 bytes: The 256-bit key encrypting key (KEK).
	kek [32]byte
	// Next 8 bytes: The 64-bit initialization vector (IV) for the wrapped key.
	kiv [8]byte
	// Next 40 bytes: The wrapped (encrypted) key. When decrypted, this will become the 256-bit encryption key.
	key [40]byte
	// Next 16 bytes: The 128-bit initialization vector (IV) for the encrypted payload.
	iv [16]byte
	// All remaining bytes: The encrypted payload.
	payload []byte
}

const (
	kekLen    = 32
	kivLen    = 8
	keyLen    = 40
	ivLen     = 16
	headerLen = kekLen + kivLen + keyLen + ivLen
)

func newPayload(input []byte) *Payload {
	p := &Payload{
		payload: input[headerLen:],
	}

	copy(p.kek[:], input[:kekLen])
	copy(p.kiv[:], input[kekLen:kekLen+kivLen])
	copy(p.key[:], input[kekLen+kivLen:kekLen+kivLen+keyLen])
	copy(p.iv[:], input[kekLen+kivLen+keyLen:headerLen])

	return p
}

func readInput() []byte {
	b, err := os.ReadFile("./parts/5.txt")
	if err != nil {
		fmt.Println("Could not read input: ")
		fmt.Print(err)
		os.Exit(1)
	}

	contents := string(b)

	_, contents, found := strings.Cut(contents, "<~")
	if !found {
		fmt.Println("Could not find prefix <~")
		os.Exit(1)
	}

	contents, _, found = strings.CutLast(contents, "~>")
	if !found {
		fmt.Println("Could not find suffix ~>")
		os.Exit(1)
	}

	return []byte(contents)
}

func decode(rawData []byte) []byte {
	dest := make([]byte, len(rawData))
	ndst, nsrc, err := ascii85.Decode(dest, rawData, true)
	if err != nil {
		fmt.Println("Error when decoding ASCII85: ")
		fmt.Print(err)
		os.Exit(1)
	}

	if nsrc != len(rawData) {
		fmt.Println("Error when decoding ASCII85: did not read all bytes")
		os.Exit(1)
	}

	dest = dest[:ndst]
	return dest
}

func main() {
	rawData := readInput()
	decoded := decode(rawData)
	payload := newPayload(decoded)

	key, err := aesKeyUnwrap(payload.kek[:], payload.kiv[:], payload.key[:])
	if err != nil {
		fmt.Println("Error unwrapping key:", err)
		os.Exit(1)
	}

	block, err := aes.NewCipher(key)
	if err != nil {
		fmt.Println("Error when creating cipher:", err)
		os.Exit(1)
	}

	stream := cipher.NewCTR(block, payload.iv[:])

	dest := make([]byte, len(payload.payload))
	stream.XORKeyStream(dest, payload.payload)
	os.WriteFile("parts/6.txt", dest, 0644)
}