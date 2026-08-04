use std::fs;
use std::str;

pub const MARKER: &str = "==[ Payload ]===============================================";

/**
 * Reads the next stage's payload from the data onion
 */
fn read() -> String {
    let mut onion = fs::read_to_string("./parts/0.txt").unwrap();
    let index = onion.find(MARKER).unwrap() + MARKER.len();
    onion
        .split_off(index)
        .replace("\r", "")
        .replace("\n", "")
        .replace(" ", "")
        .replace("\t", "")
        .to_owned()
}

/**
 * Pads an array of u8 with 'u' bytes until the length == 5
 * Returns the padded chunk and the number of bytes added
 */
fn pad_chunk(chunk: &[u8]) -> ([u8; 5], usize) {
    let mut result: [u8; 5] = [b'u'; 5];
    let amount_to_pad = 5 - chunk.len();
    for i in 0..chunk.len() {
        result[i] = chunk[i];
    }

    (result, amount_to_pad)
}

/**
 * Converts the raw Ascii85 input into the chunks
 * Automatically applies padding to the final chunk
 * Returns the chunks and the number of 'u' bytes added as padding
 */
fn split_to_chunks(input: String) -> (Vec<[u8; 5]>, usize) {
    let expanded = input.replace("z", "!!!!!");
    let data = expanded
        .strip_prefix("<~")
        .unwrap()
        .strip_suffix("~>")
        .unwrap();
    let (chunks, last) = data.as_bytes().as_chunks::<5>();
    let mut result = chunks.to_vec();

    // no padding needed; already multiple of 5
    if last.is_empty() {
        return (result, 0);
    }

    let (padded, padding_characters) = pad_chunk(last);
    result.push(padded);
    (result, padding_characters)
}

fn ascii85(input: String) -> Vec<u8> {
    let (chunks, padding) = split_to_chunks(input);
    let mut result: Vec<u8> = Vec::with_capacity(chunks.len() * 4);

    for chunk in chunks.iter() {
        let large = ((chunk[0] - b'!') as u32) * (85_u32).pow(4) + 
                    ((chunk[1] - b'!') as u32) * (85_u32).pow(3) + 
                    ((chunk[2] - b'!') as u32) * (85_u32).pow(2) + 
                    ((chunk[3] - b'!') as u32) * (85_u32).pow(1) + 
                    ((chunk[4] - b'!') as u32) * (85_u32).pow(0);
        result.extend_from_slice(&large.to_be_bytes());
    }

    // remove padding
    result.truncate(result.len() - padding);
    result
}

fn main() {
    let data = read();
    fs::write("./parts/1.txt", ascii85(data)).unwrap();
}
