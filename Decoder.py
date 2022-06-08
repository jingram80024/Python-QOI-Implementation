import numpy as np
import os
from PIL import Image
import matplotlib.pyplot as plt
import struct
import sys
import time

# Decoder is built with out using the Pixel class to explore classless implementation (may circle back to encoder and revise to remove class)
# define encoding method tags
QOI_OP_RUN   = 0xc0
QOI_OP_INDEX = 0x00
QOI_OP_DIFF  = 0x40
QOI_OP_LUMA  = 0x80
QOI_OP_RGB   = 0xfe
QOI_OP_RGBA  = 0xff
MAGIC = b'qoif'
QOI_END_MARKER = bytearray([0,0,0,0,0,0,0,1])

def index_position(r_value,g_value,b_value,a_value):
    hash = (r_value * 3 + g_value * 5 + b_value * 7 + a_value * 11) % 64
    return hash

# define input and output file names and directories
input_file_name = 'qoi_output.qoi'
input_rel_path = 'images/'
input_file_path = os.path.join(input_rel_path, input_file_name)
output_image_name = 'qoi to jpg.jpg'
output_image_rel_path = 'images/'
output_image_path = os.path.join(output_image_rel_path, output_image_name)

with open(input_file_path, 'rb') as f:
    byte_stream = f.read()
# use struct to unpack 14 byte header
fmt_string = '>4sIIBB'
header_bytes = byte_stream[0:14]
magic, width, height, channels, colorspace = struct.unpack(fmt_string,header_bytes)
if (magic != MAGIC) or (channels < 3) or (channels > 4):
    print("Error -- Unexpected format")
    sys.exit()
else:
    print("qoi file read successfully from " + input_file_path)

#index is list of r,g,b,a tuples
index = []
for i in range(64):
    index.append((0,0,0,255))

# color_stream will be reshaped later using np.reshape to form 3d array for PIL to convert to image
color_stream = np.empty(width * height * channels, dtype='uint8')
color_marker = 0
offset =  14
run_count = 0
r = 0
g = 0
b = 0
a = 255
exit_flag = False

start_time = time.time()
while exit_flag != True:
    current_byte = byte_stream[offset]
    # a valid decoder must check for the presence of an 8 bit flag first
    if current_byte == QOI_OP_RGBA:
        r, g, b, a = byte_stream[offset+1:offset+5]
        offset += 5
    elif current_byte == QOI_OP_RGB:
        r, g, b = byte_stream[offset+1:offset+4]
        offset += 4
    else:
        # get first two bits of byte and determine decoding method
        tag = 0xc0 & current_byte
        pr, pg, pb = color_stream[color_marker - channels: color_marker - channels + 3]
        if tag == QOI_OP_RUN:
            run_count = (0x3F & current_byte) # run count still needs to be biased by +1 but this will be done before the color stream writing for loop
            r, g, b = (pr, pg, pb)
            offset += 1        
        elif tag == QOI_OP_INDEX and offset < (len(byte_stream)-len(QOI_END_MARKER)):
            hash = 0x3F & current_byte
            r,g,b,a = index[hash]
            offset += 1
        elif tag == QOI_OP_DIFF:
            dr = ((0x30 & current_byte) >> 4) - 2
            dg = ((0x0C & current_byte) >> 2) - 2
            db = (0x03 & current_byte) -2
            r = pr + dr
            g = pg + dg
            b = pb + db
            offset += 1
        elif tag == QOI_OP_LUMA:
            dg = (0x3F & current_byte) - 32
            dr_dg = ((0xF0 & byte_stream[offset + 1]) >> 4) - 8
            db_dg = (0x0F & byte_stream[offset + 1]) - 8
            dr = dr_dg + dg
            db = db_dg + dg
            r = pr + dr
            g = pg + dg
            b = pb + db
            offset += 2
        else:
            if byte_stream[offset:] == QOI_END_MARKER:
                exit_flag = True
                if color_marker != (width * height * channels):
                    print("bytes ended before anticipated -- color_stream may have null values at end")
                    sys.exit()
            else:
                print("uninterpretable byte encountered")
                sys.exit()
    if exit_flag != True:
        run_count += 1
        for i in range(run_count):
            if channels == 3:
                color_stream[color_marker:color_marker+3] = [r, g, b]
                color_marker += 3
            else:
                color_stream[color_marker:color_marker+4] = [r, g, b, a]
                color_marker += 4

        hash = index_position(r,g,b,a)
        index[hash] = (r,g,b,a)
        run_count = 0

output_array = np.reshape(color_stream, (height, width, channels))
if channels == 3:
    color_mode = 'RGB'
else:
    color_mode = 'RGBA'
output_image = Image.fromarray(output_array,color_mode)
end_time = time.time()
decode_time = end_time - start_time
print("completed decoding in " + str(round(decode_time,4)) + " seconds")
plt.imshow(output_image, aspect='auto')
plt.show()

output_image.save(output_image_path)
print("saved jpg output to " + output_image_path)