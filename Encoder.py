import numpy as np
import os
from PIL import Image
import struct
import sys
import time

# define encoding method tags
QOI_OP_RUN   = 0xc0
QOI_OP_INDEX = 0x00
QOI_OP_DIFF  = 0x40
QOI_OP_LUMA  = 0x80
QOI_OP_RGB   = 0xfe
QOI_OP_RGBA  = 0xff

# determine image attributes
# set file names and relative paths
# set up color_stream rgb(a) array
output_file_name = 'qoi_output.qoi'
output_rel_path = 'images/'
output_path = os.path.join(output_rel_path, output_file_name)
image_rel_path = 'images/'
image_name = 'monument.jpg'
image_path = os.path.join(image_rel_path, image_name)
image = Image.open(image_path)
image_array = np.array(image)
height, width, channels = image_array.shape
raw_image_bytes = width * height * channels
color_stream = np.reshape(image_array, np.size(image_array))
max_size = 14 + 8 + (height * width * (channels + 1)) # shows worst case bytes if full rgb(a) encoded

# build header
fmt_string = '>4sIIBB'
magic = b'qoif'
colorspace = 0 # 0 - sRGB with linear alpha channel; 1 - all channels linear
descriptors = (magic, width, height, channels, colorspace)
QOI_HEADER = struct.pack(fmt_string, *descriptors)

# build end marker
QOI_END_MARKER = bytearray([0,0,0,0,0,0,0,1])

# custom classes
class Pixel:
    def __init__(self,*values):
        if len(values) == 3:
            r, g, b = values
            a = 255
        elif len(values) == 4:
            r, g, b, a = values
        else:
            print("Error - pixel class missing channel value")
            sys.exit()
        self.r = r
        self.g = g
        self.b = b
        self.a = a
    def __eq__(self, other):
        if isinstance(other, Pixel):
            return (self.r == other.r and
                    self.g == other.g and
                    self.b == other.b and
                    self.a == other.a)
        return False

# custom functions
def index_position(pixel):
    hash = (pixel.r * 3 + pixel.g * 5 + pixel.b * 7 + pixel.a * 11) % 64
    return hash

def color_diff(pixel,prev_pixel):
    dr = int(pixel.r) - int(prev_pixel.r)
    dg = int(pixel.g) - int(prev_pixel.g)
    db = int(pixel.b) - int(prev_pixel.b)
    # this function is only called when da = 0, return only other 3 diffs as tuple
    diff = (dr, dg, db)
    return diff

# copies rgba values from one pixel object to another to prevent them from becoming the same object.
# Encoder.py should only ever have a total of 64 index pixel objects + 2 cur/prev pixel objects = 66.
def pixel_store(pixel_from, pixel_to):
    pixel_to.r = pixel_from.r
    pixel_to.g = pixel_from.g
    pixel_to.b = pixel_from.b
    pixel_to.a = pixel_from.a

# initial conditions, set up byte stream array
# write QOI Header to byte stream array
# set color stream offset at beginning off stream
previous_pixel = Pixel(0,0,0,255)
current_pixel = Pixel(0,0,0,255)
run_count = 0
index = np.empty(64,dtype='O')
for i in range(len(index)):
    index[i] = Pixel(0,0,0,255)
byte_stream = bytearray()
byte_stream += QOI_HEADER

# write main code here iterating through all pixels
start_time = time.time()
for offset in range(height * width):
    # update current pixel to current offset in color stream
    current_pixel.r = color_stream[offset * channels]
    current_pixel.g = color_stream[offset * channels + 1]
    current_pixel.b = color_stream[offset * channels + 2]
    if channels == 4: current_pixel.a = color_stream[offset * channels + 3]
    
    # check for run that is ready to be written
    if current_pixel == previous_pixel:
        run_count += 1
        if run_count == 62 or offset == (height * width):
            byte_stream += bytes([QOI_OP_RUN | run_count -1])
            run_count = 0
    # if not then check for other methods
    else:
        # check if a stored run needs to be written
        if run_count > 0:
            byte_stream += bytes([QOI_OP_RUN | run_count - 1])
            run_count = 0
        # now determine if pixel is in index
        pixel_hash = index_position(current_pixel)
        if current_pixel == index[pixel_hash]:
            byte_stream += bytes([QOI_OP_INDEX | pixel_hash])
        else:
            # there is no index, so store it, and move on to other methods
            pixel_store(current_pixel, index[pixel_hash])
            if current_pixel.a != previous_pixel.a:
                byte_stream += bytes([QOI_OP_RGBA, current_pixel.r, current_pixel.g, current_pixel.b, current_pixel.a])
            else:
                # alpha value is the same, there are 3 possible ways to encode from here, but we need differences
                # call colordiff function to get int 32 dr dg db tuple (da is 0 do not compute)
                dr, dg, db = color_diff(current_pixel, previous_pixel)
                if (dr >= -2 and dr <= 1) and (dg >= -2 and dg <= 1) and (db >= -2 and db <= 1):
                    byte_stream += bytes([QOI_OP_DIFF | np.uint8(dr + 2) << 4 | np.uint8(dg + 2) << 2 | np.uint8(db + 2)])
                elif (dg >= -32 and dg <= 31) and ((dr-dg) >= -8 and (dr-dg) <= 7) and ((db-dg) >= -8 and (db-dg) <= 7):
                    byte_stream += bytes([QOI_OP_LUMA | np.uint8(dg + 32), np.uint8(dr-dg + 8) << 4 | np.uint(db-dg + 8)])
                else:
                    byte_stream += bytes([QOI_OP_RGB, current_pixel.r, current_pixel.g, current_pixel.b])

    # save current pixel
    pixel_store(current_pixel, previous_pixel)

# write end marker bytes and write byte_stream to file
byte_stream += QOI_END_MARKER
with open(output_path, 'wb') as f:
    f.write(byte_stream)
end_time = time.time()
encode_time = end_time - start_time
# print compression stats to terminal
print("Compressed " + str(raw_image_bytes) + " bytes raw image to " + str(len(byte_stream)) + " bytes at " + str(output_path) + " in " + str(round(encode_time,4)) + " seconds")
print("True compression -- " + str(round((raw_image_bytes/(len(byte_stream))),1)) + ":1")
print("QOI Optimization Factor (worst case QOI compressed bytes:actual compressed bytes) -- " + str(round((max_size/(len(byte_stream))),1)) + ":1")