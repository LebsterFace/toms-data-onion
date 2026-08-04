import java.io.IOException;
import java.nio.charset.Charset;
import java.util.Arrays;
import java.util.function.IntBinaryOperator;

String readRawData() {
	try {
		final String result = Files.readString(Path.of("parts/1.txt"));
		return result
				.replaceAll("\r?\n", "")
				.split("<~|~>")[1];
	} catch (IOException e) {
		throw new Error(e);
	}
}

byte[] ascii85(String input) {
	input = input.replace("z", "!!!!!");
	final int padding = (5 - (input.length() % 5)) % 5;
	input += "u".repeat(padding);

	final byte[] bytes = new byte[(input.length() / 5) * 4];
	int byte_count = 0;
	for (int i = 0; i < input.length(); i += 5) {
		final String chunk = input.substring(i, i + 5);
		final char[] chars = chunk.toCharArray();
		long result = ((long) (chars[0] - '!')) * Math.powExact(85, 4) +
				      ((long) (chars[1] - '!')) * Math.powExact(85, 3) +
				      ((long) (chars[2] - '!')) * Math.powExact(85, 2) +
				      ((long) (chars[3] - '!')) * Math.powExact(85, 1) +
				      ((long) (chars[4] - '!')) * Math.powExact(85, 0);
		bytes[byte_count++] = (byte) ((result & 0xFF000000L) >>> (8 * 3));
		bytes[byte_count++] = (byte) ((result & 0x00FF0000L) >>> (8 * 2));
		bytes[byte_count++] = (byte) ((result & 0x0000FF00L) >>> (8 * 1));
		bytes[byte_count++] = (byte) ((result & 0x000000FFL) >>> (8 * 0));
	}

	// remove padding
	return Arrays.copyOf(bytes, bytes.length - padding);
}


int process(byte input) {
	int result = input;
	// 1. Flip every second bit
	result = (result ^ 0b01010101);

	// 2. Rotate the bits one position to the right
	int lsb = result & 1;
	lsb <<= 7;
	result = (result >>> 1);
	result = (result & 0b01111111) | lsb;
	result = result | lsb;
	return result;
}


void main() throws IOException {
	final byte[] input = ascii85(readRawData());

	StringBuilder output = new StringBuilder(input.length);

	for (byte b : input) {
		output.append((char) process(b));
	}

	output.trimToSize();
	Files.writeString(Path.of("parts/2.txt"), output.toString().trim(), Charset.forName("utf8"));
}