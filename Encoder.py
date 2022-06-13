import numpy as np
import os
from PIL import Image
import struct
import sys
import time

start_time = time.time()
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
output_file_name = 'qoi_no_classes.qoi'
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
MAGIC = b'qoif'
colorspace = 0 # 0 - sRGB with linear alpha channel; 1 - all channels linear
descriptors = (MAGIC, width, height, channels, colorspace)
QOI_HEADER = struct.pack(fmt_string, *descriptors)

# build end marker
QOI_END_MARKER = bytearray([0,0,0,0,0,0,0,1])
HASH_ARRAY = np.array([3, 5, 7, 11])

# initial conditions, set up byte stream array
# write QOI Header to byte stream array
# set color stream offset at beginning off stream
r, g, b, a = (0, 0, 0, 255)
pr, pg, pb, pa = (0, 0, 0, 255)
run_count = 0
index = np.full((64, 4), [0, 0, 0, 255], dtype='uint8')
byte_stream = bytearray()
byte_stream += QOI_HEADER


for offset in range(height * width):
    # update current pixel to current offset in color stream
    r = color_stream[offset * channels]
    g = color_stream[offset * channels + 1]
    b = color_stream[offset * channels + 2]
    if channels == 4: a = color_stream[offset * channels + 3]
    
    # check for run that is ready to be written
    if [r, g, b, a] == [pr, pg, pb, pa]:
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
        hash = (np.dot(HASH_ARRAY, [r, g, b, a])) % 64
        #.all() method is required here since index is an np array and comparing the two arrays yields
        # an array of four Trues.
        if ([r, g, b, a] == index[hash]).all():
            byte_stream += bytes([QOI_OP_INDEX | hash])

        else:
            # pixel is not in index, so store it and move on to other methods
            index[hash] = [r, g, b, a]

            if a != pa:
                byte_stream += bytes([QOI_OP_RGBA, r, g, b, a])

            else:
                # alpha value is the same get diff in other channels
                dr, dg, db = ((int(r) - int(pr)), (int(g) - int(pg)), (int(b) - int(pb)))

                if (dr >= -2 and dr <= 1) and (dg >= -2 and dg <= 1) and (db >= -2 and db <= 1):
                    byte_stream += bytes([QOI_OP_DIFF | np.uint8(dr + 2) << 4 | np.uint8(dg + 2) << 2 | np.uint8(db + 2)])

                elif (dg >= -32 and dg <= 31) and ((dr-dg) >= -8 and (dr-dg) <= 7) and ((db-dg) >= -8 and (db-dg) <= 7):
                    byte_stream += bytes([QOI_OP_LUMA | np.uint8(dg + 32), np.uint8(dr-dg + 8) << 4 | np.uint(db-dg + 8)])
                
                else:
                    byte_stream += bytes([QOI_OP_RGB, r, g, b])

    # save current pixel
    pr, pg, pb, pa = (r, g, b, a)

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