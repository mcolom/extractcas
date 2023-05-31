#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

'''
(c) 2019 Miguel Colom
http://mcolom.info
'''

# https://www.msx.org/forum/semi-msx-talk/emulation/how-do-exactly-works-cas-format

import argparse
import sys

def read_header(f):
    '''
    Reader tape header
    '''
    data = f.read(1)
    while data != b'\x1f' and data != b'':
        data = f.read(1)
    if data == b'':
        return False # EOF
    
    data = f.read(7)
    assert data == bytes((0xA6, 0xDE, 0xBA, 0xCC, 0x13, 0x7D, 0x74)), f'Bad header: {data}'
    return True

def identify(f):
    '''
    Identify the type of block
    '''
    #print("Identify @ {}".format(hex(f.tell())))

    if not read_header(f):
        return "EOF"

    value = f.read(1)
    
    if value == b'':
        return "EOF"

    d = {b'\xd0': 'BINARY', b'\xd3': 'BASIC', b'\xea': 'ASCII'}

    if value in d:
        for i in range(9):
            dup = f.read(1)
            if dup == b'' or value != dup:
                return "EOF"
        return d[value]
    
    # Data block
    return "BLOCK"
    

def read_addr(f):
    '''
    Read a 16 bit address, encoded with MSX's little endian
    '''
    return int.from_bytes(f.read(2), "little")

def read_filename(f):
    '''
    Read a file name
    '''
    filename = f.read(6)
    filename = filename.decode('utf-8')
    filename = filename.strip()
    return filename

def read_ASCII(f):
    '''
    Read an ASCII file
    '''
    filename = read_filename(f)
    print("Found ASCII: {}".format(filename))
    
    if not read_header(f):
        return
    
    with open(filename, 'wb') as out: 
        b = f.read(1)
        finished = b == b'' or b == b'\x1a'
        
        counter = 1

        while not finished:
            out.write(b)
            
            if counter % 256 == 0:
                if not read_header(f):
                    return

            b = f.read(1)
            counter += 1

            finished = b == b'' or b == b'\x1a'    
    #print("READ ASCII END @ ", hex(f.tell()))
    
def read_binary(f):
    '''
    Read a binary file
    '''
    filename = f.read(6)
    filename = filename.decode('utf-8')
    filename = filename.strip()
    
    if not read_header(f):
        return
    
    start = read_addr(f)
    end = read_addr(f)
    execution = read_addr(f)

    print("Found binary: {}. Start: {}, end: {}, exec: {}".\
        format(filename, hex(start), hex(end), hex(execution)))
    
    length = end - start + 1
    data = f.read(length)
    
    with open(filename, 'wb') as out:
        out.write(data)

def read_block(f, filename):
    '''
    Read a custom data block
    '''
    print("Found {}".format(filename))

    buffer = b''
    header = bytes((0xA6, 0xDE, 0xBA, 0xCC, 0x13, 0x7D, 0x74))

    header_detected = buffer[-7:] == header
    EOF = False

    while not header_detected and not EOF:
        v = f.read(1)
        if v == b'':
            EOF = True
        else:
            buffer += v
            header_detected = buffer[-7:] == header
    
    with open(filename, 'wb') as out:
        out.write(buffer[:-8])
    
    # Undo header read
    f.seek(f.tell() - 8)

def read_basic(f):
    '''
    Read a tokenized BASIC program
    '''
    filename = f.read(6)
    filename = filename.decode('utf-8')
    filename = filename.strip()
    
    print(filename)

    if not read_header(f):
        return
    
    all_read = False
    
    buf = bytearray()
    while not all_read:
        b = f.read(1)
        if b == b'':
            return # EOF
        buf.extend(b)
        all_read = buf[-7:] == bytearray(b'\x00' * 7)

    # All read
    print(f"Found BASIC ASCII: {len(buf)} bytes")
    
    with open(filename, 'wb') as out:
        out.write(buf)


description = "Extract files from an MSX's CAS file"
epilog = '(C) Miguel Colom, GNU GPL3 license. http://mcolom.info'

parser = argparse.ArgumentParser(description=description, epilog=epilog)
parser.add_argument("input")
parser.parse_args()
args = parser.parse_args()


input_filename = args.input
block_num = 1 # Counter for the custom block file names

# Process all files
with open(input_filename, 'rb') as f:
    id = identify(f)
    while id != 'EOF':
        if id == 'ASCII':
            read_ASCII(f)
        elif id == 'BINARY':
            read_binary(f)
        elif id == 'BASIC':
            read_basic(f)
        elif id == 'BLOCK':
            read_block(f, 'BLOCK{}'.format(block_num))
            block_num += 1
        else:
            raise Exception("Unknown file ID: {}".format(id))
        
        id = identify(f)

