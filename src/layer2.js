import fs from "node:fs/promises";

const ascii85 = text => {
	text = text.replaceAll("z", "!!!!!");
	const padding = (5 - (text.length % 5)) % 5;
	text += "u".repeat(padding);

	const bytes = new Uint8Array((text.length / 5) * 4);
	const view = new DataView(bytes.buffer);
	let number_count = 0;

	for (let i = 0; i < text.length; i += 5) {
		const chunk = text.slice(i, i + 5);
		const value = [...chunk].map((c, j) => {
			const code = c.charCodeAt(0) - '!'.charCodeAt(0);
			const scale = 85 ** (4 - j);
			return code * scale;
		}).reduce((a, b) => a + b);

		view.setUint32(number_count, value, false);
		number_count += 4;
	}

	return bytes.slice(0, bytes.length - padding);
};

let input = await fs.readFile("./parts/2.txt", "utf-8");
input = input.slice(
	input.indexOf("<~") + 2,
	input.indexOf("~>")
).replaceAll(/\r?\n/g, "");

const valid_bytes = ascii85(input).filter(byte => {
	let one_counter = 0;

	for (let i = 0; i < 8; i++) {
		const bit = (byte & (1 << i)) >> i;
		if (bit === 1) {
			one_counter += 1;
		}
	}

	return one_counter % 2 === 0;
});

function* bits(array) {
	for (const byte of array) {
		for (let i = 7; i >= 0; i--) {
			yield (byte & (1 << i)) >> i;
		}
	}
}

// 01234567 89ABCDEF 01234...
// 01234568 9ABCDE01 ...


const result = new Uint8Array(Math.floor(valid_bytes.length * 7 / 8));
let bit_count = 0;
let byte = 0;
let byte_count = 0;

let i = 0;
for (const bit of bits(valid_bytes)) {
	i++;
	if (i % 8 === 0) continue;
	// collect it into result
	byte = (byte << 1) | bit;
	bit_count++;
	if (bit_count === 8) {
		result[byte_count++] = byte;
		bit_count = 0;
		byte = 0;
	}
}

await fs.writeFile("./parts/3.txt", Array.from(result, x => String.fromCharCode(x)).join("").trim());