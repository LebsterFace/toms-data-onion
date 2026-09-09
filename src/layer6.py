from base64 import a85decode
from pathlib import Path

PAYLOAD_HEADER = "==[ Payload ]==============================================="

text = Path("parts/6.txt").read_text().replace("\r", "").replace("\n", "")
start = text.find("<~", text.find(PAYLOAD_HEADER))
end = text.find("~>", start) + 2
encoded = text[start:end]
PROGRAM = a85decode(encoded, adobe=True)

# ==[ Spec: Registers ]=======================================
# The Tomtel Core i69 is a register machine. It has six 8-bit
# registers and another six 32-bit registers for a total of 12 registers.
# All registers are initialized to zero when the machine starts.
# All registers hold unsigned integers.

class Reg8:
	def __init__(self):
		self._value = 0

	@property
	def value(self):
		return self._value

	@value.setter
	def value(self, value):
		if type(value) != int: raise TypeError(f"Cannot set Reg8 to {type(value)}")
		self._value = value & 0xFF

class Reg32:
	def __init__(self):
		self._value = 0

	@property
	def value(self):
		return self._value

	@value.setter
	def value(self, value):
		if type(value) != int: raise TypeError(f"Cannot set Reg32 to {type(value)}")
		self._value = value & 0xFFFFFFFF

# The 8-bit registers are:
# Accumulation register -- Used to store the result of various instructions.
a = Reg8()
# Operand register -- This is 'right hand side' of various operations.
b = Reg8()
# Count/offset register -- Holds an offset or index value that is used when reading memory.
c = Reg8()
# General purpose register
d = Reg8()
# General purpose register
e = Reg8()
# Flags register -- Holds the result of the comparison instruction (CMP), and is used by conditional jump instructions (JEZ, JNZ).
f = Reg8()

# The 32-bit registers are:
# General purpose register
la = Reg32()
# General purpose register
lb = Reg32()
# General purpose register
lc = Reg32()
# General purpose register
ld = Reg32()
# Pointer to memory -- holds a memory address which is used by instructions that read or write memory.
ptr = Reg32()
# Program counter -- holds a memory address that points to the next instruction to be executed.
pc = Reg32()

# In addition to these 12 registers, there is an 8-bit
# pseudo-register used to read and write memory. This is only
# used by the 8-bit move instructions (MV, MVI).
# (ptr+c)`  Memory cursor -- Used to access one byte of
#           memory. Using this pseudo-register as the
#           {dst} of a move instruction will write to
#           memory. Using this as the {src} of a move
#           instruction will read from memory. The memory
#           address of the byte to be read/written is the
#           sum of the `ptr` and `c` registers.
class CursorReg:
	@property
	def value(self):
		return memory[ptr.value + c.value]

	@value.setter
	def value(self, value):
		if type(value) != int: raise TypeError(f"Cannot set cursor to {type(value)}")
		memory[ptr.value + c.value] = value & 0xFF

cursor = CursorReg()

# ==[ Spec: Memory ]==========================================
# The Tomtel Core i69 has a fixed amount of memory. Whatever
# the size of this layer's payload is, that's how much memory
# is needed.
# Memory is mutable. Any byte of memory can be read, written,
# or executed as an instruction.
# Output is not stored in memory.
memory = bytearray(PROGRAM)
def fetch(bytecount):
	result = 0
	for i in range(bytecount):
		result |= (memory[pc.value] << (8 * i))
		pc.value += 1
	return result

# --[ ADD a <- b ]--------------------------------------------
#   8-bit addition
#   Opcode: 0xC2 (1 byte)
#   Sets `a` to the sum of `a` and `b`, modulo 256.

def ADD(opcode):
	a.value += b.value

# --[ APTR imm8 ]---------------------------------------------
#   Advance ptr
#   Opcode: 0xE1 0x__ (2 bytes)
#   Sets `ptr` to the sum of `ptr` and `imm8`. Overflow behaviour is undefined.

def APTR(opcode):
	imm8 = fetch(1)
	ptr.value += imm8

# --[ CMP ]---------------------------------------------------
#   Compare
#   Opcode: 0xC1 (1 byte)
#   Sets `f` to zero if `a` and `b` are equal, otherwise sets `f` to 0x01.

def CMP(opcode):
	if a.value == b.value:
		f.value = 0
	else:
		f.value = 1

# --[ HALT ]--------------------------------------------------
#   Halt execution
#   Opcode: 0x01 (1 byte)
#   Stops the execution of the virtual machine. Indicates that the program has finished successfully.

def HALT(opcode):
	exit(0)

# --[ JEZ imm32 ]---------------------------------------------
#   Jump if equals zero
#   Opcode: 0x21 0x__ 0x__ 0x__ 0x__ (5 bytes)
#   If `f` is equal to zero, sets `pc` to `imm32`. Otherwise does nothing.
def JEZ(opcode):
	imm32 = fetch(4)
	if f.value == 0:
		pc.value = imm32

# --[ JNZ imm32 ]---------------------------------------------
#   Jump if not zero
#   Opcode: 0x22 0x__ 0x__ 0x__ 0x__ (5 bytes)
#   If `f` is not equal to zero, sets `pc` to `imm32`. Otherwise does nothing.
def JNZ(opcode):
	imm32 = fetch(4)
	if f.value != 0:
		pc.value = imm32

# --[ MV {dest} <- {src} ]------------------------------------
#   Move 8-bit value
#   Opcode: 0b01DDDSSS (1 byte)
#   Sets `{dest}` to the value of `{src}`.
#   Both `{dest}` and `{src}` are 3-bit unsigned integers that
#   correspond to an 8-bit register or pseudo-register. In the
#   opcode format above, the "DDD" bits are `{dest}`, and the
#   "SSS" bits are `{src}`. Below are the possible valid
#   values (in decimal) and their meaning.
#    1 => `a`
#    2 => `b`
#    3 => `c`
#    4 => `d`
#    5 => `e`
#    6 => `f`
#    7 => `(ptr+c)`

def decode_reg8(id):
	if type(id) == int and 1 <= id <= 7:
		return [a, b, c, d, e, f, cursor][id - 1]
	else:
		raise NameError(f"Unknown Reg8 with ID {id}")	

def MV(opcode):
	DDD = (opcode & 0b00111000) >> 3
#   A zero `{src}` indicates an MVI instruction, not MV.
	SSS = (opcode & 0b00000111)
	if SSS == 0: return MVI(opcode)
	dest = decode_reg8(DDD)
	src = decode_reg8(SSS)
	dest.value = src.value


# --[ MV32 {dest} <- {src} ]----------------------------------
#   Move 32-bit value
#   Opcode: 0b10DDDSSS (1 byte)
#   Sets `{dest}` to the value of `{src}`.
#   Both `{dest}` and `{src}` are 3-bit unsigned integers that
#   correspond to a 32-bit register. In the opcode format
#   above, the "DDD" bits are `{dest}`, and the "SSS" bits are
#   `{src}`. Below are the possible valid values (in decimal)
#   and their meaning.
#    1 => `la`
#    2 => `lb`
#    3 => `lc`
#    4 => `ld`
#    5 => `ptr`
#    6 => `pc`
def decode_reg32(id):
	if type(id) == int and 1 <= id <= 6:
		return [la, lb, lc, ld, ptr, pc][id - 1]
	else:
		raise NameError(f"Unknown Reg32 with ID {id}")

def MV32(opcode):
	DDD = (opcode & 0b00111000) >> 3
	#   A zero `{src}` indicates an MVI instruction, not MV.
	SSS = (opcode & 0b00000111)
	if SSS == 0: return MVI32(opcode)
	dest = decode_reg32(DDD)
	src = decode_reg32(SSS)
	dest.value = src.value

# --[ MVI {dest} <- imm8 ]------------------------------------
#   Move immediate 8-bit value
#   Opcode: 0b01DDD000 0x__ (2 bytes)
#   Sets `{dest}` to the value of `imm8`.
#   `{dest}` is a 3-bit unsigned integer that corresponds to
#   an 8-bit register or pseudo-register. It is the "DDD" bits
#   in the opcode format above.
def MVI(opcode):
    DDD = (opcode & 0b00111000) >> 3
    imm8 = fetch(1)
    dest = decode_reg8(DDD)
    dest.value = imm8

# --[ MVI32 {dest} <- imm32 ]---------------------------------
#   Move immediate 32-bit value
#   Opcode: 0b10DDD000 0x__ 0x__ 0x__ 0x__ (5 bytes)
#   Sets `{dest}` to the value of `imm32`.
#   `{dest}` is a 3-bit unsigned integer that corresponds to a
#   32-bit register. It is the "DDD" bits in the opcode format
#   above.
def MVI32(opcode):
    DDD = (opcode & 0b00111000) >> 3
    imm32 = fetch(4)
    dest = decode_reg32(DDD)
    dest.value = imm32

# --[ OUT a ]-------------------------------------------------
#   Output byte
#   Opcode: 0x02 (1 byte)
#   Appends the value of `a` to the output stream.
def OUT(opcode):
	print(chr(a.value & 0xFF), end="")

# --[ SUB a <- b ]--------------------------------------------
#   8-bit subtraction
#   Opcode: 0xC3 (1 byte)
#   Sets `a` to the result of subtracting `b` from `a`. If
#   subtraction would result in a negative number, 256 is
#   added to ensure that the result is non-negative.
def SUB(opcode):
	result = a.value - b.value
	if result < 0: result += 256
	a.value = result

# --[ XOR a <- b ]--------------------------------------------
#   8-bit bitwise exclusive OR
#   Opcode: 0xC4 (1 byte)
#   Sets `a` to the bitwise exclusive OR of `a` and `b`.
def XOR(opcode):
	a.value ^= b.value

# -----------------------------------------------------------------------------------------------------------

while True:
	opcode = fetch(1)
	if opcode == 0xC2:         ADD(opcode)
	elif opcode == 0xE1:       APTR(opcode)
	elif opcode == 0xC1:       CMP(opcode)
	elif opcode == 0x01:       HALT(opcode)
	elif opcode == 0x21:       JEZ(opcode)
	elif opcode == 0x22:       JNZ(opcode)
	elif opcode >> 6 == 0b01:  MV(opcode)
	elif opcode >> 6 == 0b10:  MV32(opcode)
	elif opcode == 0x02:       OUT(opcode)
	elif opcode == 0xC3:       SUB(opcode)
	elif opcode == 0xC4:       XOR(opcode)
	else:
		raise TypeError(f"Unknown opcode 0x{opcode:x} (0b{opcode:08b})")