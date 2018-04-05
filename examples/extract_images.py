#!/usr/bin/env python

'''
usage:   extract.py <some.pdf>

Locates Form XObjects and Image XObjects within the PDF,
and creates a new PDF containing these -- one per page.

Resulting file will be named extract.<some.pdf>

'''

import sys
import os
import zlib
from PIL import Image
from pprint import pprint
import types

# --- Add pdfrw module to Python path ---
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir  = os.path.dirname(currentdir)
sys.path.insert(0, parentdir) 

# --- Import pdrfw stuff ---
from pdfrw import PdfReader, PdfWriter
from pdfrw.objects.pdfarray import PdfArray
from pdfrw.objects.pdfname import BasePdfName

# --- Main ---
inpfn, = sys.argv[1:]
reader = PdfReader(inpfn)
print('Number of pages: {0}'.format(reader.numPages))
page_list = reader.pages

for i, page in enumerate(page_list):
    # --- Iterate /Resources in page ---
    print('###### Processing page {0} ######'.format(i))
    resource_dic = page['/Resources']
    for r_name, resource in resource_dic.iteritems():
        # >> Skip non /XObject keys in /Resources
        if r_name != '/XObject': continue

        # >> DEBUG dump /XObjects dictionary
        # print('--- resource ---')
        # pprint(resource)
        # print('----------------')

        # >> Traverse /XObject dictionary data. Each page may have 0, 1 or more /XObjects
        # >> If there is more than 1 image in the page there could be more than 1 /XObject.
        # >> Some /XObjects are not images, for example, /Subtype = /Form.
        # >> NOTE Also, images may be inside the /Resources of a /From /XObject.
        img_index = 0
        for xobj_name, xobj_dic in resource.iteritems():
            xobj_type = xobj_dic['/Type']
            xobj_subtype = xobj_dic['/Subtype']
            # >> Skip XObject forms
            if xobj_subtype == '/Form':
                # >> NOTE There could be an image /XObject in the /From : /Resources dictionary.
                print('Skipping /Form /XObject')
                print('--- xobj_dic ---')
                pprint(xobj_dic)
                print('----------------')
                continue
            img_fname = 'Image_page{0:02d}_img{1:02d}.png'.format(i, img_index)

            # --- Print info ---
            print('--- Page {0:02d} Image {1:02d} ---'.format(i, img_index))
            print('xobj_name = "{0}"'.format(xobj_name))
            print('xobj_type = "{0}"'.format(xobj_type))
            print('xobj_subtype = "{0}"'.format(xobj_subtype))
            # print('--- xobj_dic ---')
            # pprint(xobj_dic)
            # print('----------------')

            # --- Get image type and parameters ---
            if type(xobj_dic['/Filter']) is PdfArray:
                num_filters = len(xobj_dic['/Filter'])
                if num_filters > 1:
                    print('Filter list = "{0}"'.format(unicode(xobj_dic['/Filter'])))
                    print('XObject has more than 1 filter. Exiting.')
                    sys.exit(1)
                filter_name = xobj_dic['/Filter'][0]
            elif type(xobj_dic['/Filter']) is BasePdfName:
                filter_name = xobj_dic['/Filter']
            elif type(xobj_dic['/Filter']) is types.NoneType:
                print('type(xobj_dic[\'/Filter\']) is types.NoneType. Skipping.')
                print('--- xobj_dic ---')
                pprint(xobj_dic)
                print('----------------')
                continue
            else:
                print('Unknown type(xobj_dic[\'/Filter\']) = "{0}"'.format(type(xobj_dic['/Filter'])))
                sys.exit(1)
            color_space = xobj_dic['/ColorSpace']
            bits_per_component = xobj_dic['/BitsPerComponent']
            height = int(xobj_dic['/Height'])
            width = int(xobj_dic['/Width'])

            # --- Print info ---
            print('/Filter = "{0}"'.format(filter_name))
            print('/ColorSpace = "{0}"'.format(color_space))
            print('/BitsPerComponent = "{0}"'.format(bits_per_component))
            print('/Height = "{0}"'.format(height))
            print('/Width = "{0}"'.format(width))

            # NOTE /Filter = /FlateDecode may be PNG images. Check for magic number.
            jpg_magic_number = '\xff\xd8'
            png_magic_number = '\x89\x50\x4E\x47'
            gif87_magic_number = '\x47\x49\x46\x38\x37\x61'
            gif89_magic_number = '\x47\x49\x46\x38\x39\x61'

            # >> Check for magic numbers
            stream_raw = xobj_dic.stream
            if stream_raw[0:2] == jpg_magic_number:
                print('JPG magic number detected!')
            elif stream_raw[0:4] == png_magic_number:
                print('PNG magic number detected!')
            elif stream_raw[0:6] == gif87_magic_number:
                print('GIF87a magic number detected!')
            elif stream_raw[0:6] == gif89_magic_number:
                print('GIF89a magic number detected!')
            else:
                print('Not known image magic number')

            # --- PNG embedded images ---
            # >> WARNING DCTDecode is JPEG, not PNG!!!
            if filter_name == '/DCTDecode':
                print('Saving JPG image')
                with open(img_fname, 'wb') as f:
                    f.write(xobj_dic.stream)

            # --- RGB images with FlateDecode ---
            elif color_space == '/DeviceRGB' and filter_name == '/FlateDecode':
                if filter_name == '/FlateDecode':
                    print('stream is compressed with /FlateDecode filter')
                    contents_comp = xobj_dic.stream
                    contents_plain = zlib.decompress(contents_comp)
                    print('len(contents_comp) = {0:,d}'.format(len(contents_comp)))
                    print('len(contents_plain) = {0:,d}'.format(len(contents_plain)))

                    # --- Save image file ---
                    img = Image.frombytes('RGB', (width, height), contents_plain)
                    img.save(img_fname, 'PNG')
                else:
                    print('Unknown filter "{0}". Exiting.'.format(filter_name))

            # --- Monochrome images ---
            elif color_space == '/DeviceGray':
                print('Saving monochrome image')
                if filter_name == '/FlateDecode':
                    print('stream is compressed with /FlateDecode filter')
                    contents_comp = xobj_dic.stream
                    contents_plain = zlib.decompress(contents_comp)
                    print('len(contents_comp) = {0:,d}'.format(len(contents_comp)))
                    print('len(contents_plain) = {0:,d}'.format(len(contents_plain)))

                    # --- Save image file ---
                    img = Image.frombytes('1', (width, height), contents_plain)
                    img.save(img_fname, 'PNG')
                else:
                    print('Unknown filter "{0}". Exiting.'.format(filter_name))
            else:
                print('Unrecognised image type. It cannot be extracted. Skipping.')

            # >> Increment image size
            img_index += 1
            print('')
