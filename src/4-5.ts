import fs from "node:fs/promises";

const ascii85 = (text: string) => {
	text = text.replaceAll("z", "!!!!!");
	const padding = text.length % 5;
	text += "u".repeat(padding);

	const bytes = new Uint8Array(input.length * 4 / 5);
	const view = new DataView(bytes.buffer);
	let number_count = 0;

	for (let i = 0; i < input.length - 5; i += 5) {
		const chunk = input.slice(i, i + 5);
		const value = [...chunk].map((c, i) => {
			const code = c.charCodeAt(0) - '!'.charCodeAt(0);
			const scale = 85 ** (4 - i);
			return code * scale;
		}).reduce((a, b) => a + b);

		view.setUint32(number_count, value, false);
		number_count += 4;
	}

	return bytes.slice(0, -padding);
};

let input = await fs.readFile("./parts/4.txt", "utf-8");
input = input.slice(
	input.indexOf("<~") + 2,
	input.indexOf("~>")
).replaceAll(/\r?\n/g, "");

class Streamer {
	private readonly bitstream: Generator<number>;

	constructor(data: Uint8Array) {
		this.bitstream = this.stream(data);
	}

	private *stream(array: Uint8Array): Generator<number> {
		for (const byte of array) {
			for (let i = 7; i >= 0; i--) {
				yield (byte & (1 << i)) >> i;
			}
		}
	}

	bits(bits: number): number {
		let result = 0;

		for (let i = 0; i < bits; i++) {
			result <<= 1;

			const next = this.bitstream.next();
			if (next.done) {
				throw new Error("Ran out of bits");
			}

			result |= next.value;
		}

		return result;
	}

	bytes(bytes: number): Uint8Array {
		const result = new Uint8Array(bytes);

		for (let i = 0; i < bytes; i++) {
			result[i] = this.bits(8);
		}

		return result;
	}
}


/*
0                   1                   2                   3
0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|Ver= 4 |IHL= 5 |Type of Service|       Total Length = 216      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|     Identification = 111      |Flg=0|  Fragment Offset  =  32 |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|   Time = 119  | Protocol = 6  |        Header Checksum        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                         source address                        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      destination address                      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                             data                              |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                             data                              |
\                                                               \
\                                                               \
|                             data                              |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|            data               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+


0      7 8     15 16    23 24    31
+--------+--------+--------+--------+
|     Source      |   Destination   |
|      Port       |      Port       |
+--------+--------+--------+--------+
|                 |                 |
|     Length      |    Checksum     |
+--------+--------+--------+--------+
|
|          data octets ...
+---------------- ...

- The packet was sent FROM any port of 10.1.1.10
  - Compare Source to CORRECT_SOURCE 
- The packet was sent TO port 42069 of 10.1.1.200
  - Compare Dest to CORRECT_DEST
  - Compare Dest_Port to CORRECT_PORT 
- The IPv4 header checksum is correct
  - Split into 16 bit chunks (treating checksum as 0) 
  - Represent in 4 digit hex
  - Add together into 5 digit hex
  - Add first digit to last 4 digits
  - Apply NOT
  - Compare
- The UDP header checksum is correct
*/

type IPv4Header = {
	version: number;
	ihl: number;
	type_of_service: number;
	total_length: number;
	identification: number;
	flags: number;
	fragment_offset: number;
	ttl: number;
	protocol: number;
	checksum: number;
	source: number;
	dest: number;
	bytes: Uint8Array;
};

type UDPHeader = {
	source_port: number;
	dest_port: number;
	length: number;
	checksum: number;
	bytes: Uint8Array;
};

type Packet = {
	ip: IPv4Header;
	udp: UDPHeader;
	data: Uint8Array;
};

const response = new Streamer(ascii85(input));

const ipAddress = (n: number) => [
	(n & 0xff000000) >>> (8 * 3),
	(n & 0xff0000) >>> (8 * 2),
	(n & 0xff00) >>> (8 * 1),
	(n & 0xff) >>> (8 * 0),
].join(".");

const next_packet = (): Packet => {
	const raw_ip_bytes = response.bytes(20);
	const ip_bytes = new Streamer(raw_ip_bytes);

	const ip: IPv4Header = {
		version: ip_bytes.bits(4),
		ihl: ip_bytes.bits(4),
		type_of_service: ip_bytes.bits(8),

		total_length: ip_bytes.bits(16),

		identification: ip_bytes.bits(16),

		flags: ip_bytes.bits(3),
		fragment_offset: ip_bytes.bits(13),

		ttl: ip_bytes.bits(8),
		protocol: ip_bytes.bits(8),

		// 80 bits; 5th 16-bit word in the input
		checksum: ip_bytes.bits(16),

		source: ip_bytes.bits(32),


		dest: ip_bytes.bits(32),


		bytes: raw_ip_bytes
	};

	const raw_udp_bytes = response.bytes(8);
	const udp_bytes = new Streamer(raw_udp_bytes);
	const udp: UDPHeader = {
		source_port: udp_bytes.bits(16),
		dest_port: udp_bytes.bits(16),
		length: udp_bytes.bits(16),
		checksum: udp_bytes.bits(16),
		bytes: raw_udp_bytes
	};

	const data = response.bytes(udp.length - 8);
	return { ip, udp, data };
};

const toWords = (bytes: Uint8Array) => {
	const view = new DataView(bytes.buffer);
	const words = new Uint16Array(view.byteLength / 2);
	for (let i = 0; i < words.length; i++) {
		words[i] = view.getUint16(i * 2, false);
	}

	return words;
};

const checksum = (words: Uint16Array): number => {
	let sum = 0n;
	for (const word of words) sum += BigInt(word);
	const high = sum & 0xf0000n;
	sum &= 0x0ffffn;
	sum += (high >> 16n);
	sum = (~sum) & 0xffffn;

	if (!Number.isSafeInteger(Number(sum))) throw new Error("Sum too big for float!");
	return Number(sum);
};

const calculate_ip_checksum = (ip: IPv4Header): number => {
	const words = toWords(ip.bytes);
	words[5] = 0;
	return checksum(words);
};

const calculate_udp_checksum = (packet: Packet): number => {
	const padded_data_length = Math.ceil(packet.data.length / 2) * 2;
	const data = new Uint8Array(12 + 8 + padded_data_length);
	const view = new DataView(data.buffer);

	view.setUint32(0, packet.ip.source);
	view.setUint32(4, packet.ip.dest);
	view.setUint8(8, 0);
	view.setUint8(9, 17);
	view.setUint16(10, packet.udp.length);

	data.set(packet.udp.bytes, 12);

	// zero out the udp checksum in the header
	view.setUint16(18, 0, false);
	data.set(packet.data, 20);

	return checksum(toWords(data));
};

const is_valid = (packet: Packet): boolean => {
	if (ipAddress(packet.ip.source) !== "10.1.1.10") {
		return false;
	}

	if (ipAddress(packet.ip.dest) !== "10.1.1.200") {
		return false;
	}

	if (packet.udp.dest_port !== 42069) {
		return false;
	}

	if (calculate_ip_checksum(packet.ip) !== packet.ip.checksum) {
		return false;
	}

	if (calculate_udp_checksum(packet) !== packet.udp.checksum) {
		return false;
	}

	return true;
};

const decoder = new TextDecoder();
let result = "";
for (let i = 0; i < 673; i++) {
	const packet = next_packet();
	if (is_valid(packet)) {
		result += decoder.decode(packet.data);
	}
}

await fs.writeFile("./parts/5.txt", result.trim());