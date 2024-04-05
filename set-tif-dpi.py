# for info of the tiff file structure see:
# https://paulbourke.net/dataformats/tiff/
# https://docs.fileformat.com/image/tiff/
# for tif tag values see: https://www.awaresystems.be/imaging/tiff/tifftags.html


import sys, os



# Constants
BIG_ENDIAN_SIGNATURE = b'MM\x00\x2a' 
LITTLE_ENDIAN_SIGNATURE = b'II\x2a\x00' 

MAX_VALUE = 4294967296 # = 256^4 = 4 bytes unsigned integer (LONG)
FIELD_LENGTH = 12 #every header field is 12 bytes long

#Field tags
RESOLUTIONUNIT_TAG = 296 # 0x0128
XRESOLUTION_TAG = 282 # 0x011A
YRESOLUTION_TAG = 283 # 0x011B

# Data Types
BYTE  = 1
ASCII = 2
SHORT = 3
LONG  = 4
FRACT = 5

# lengh in bytes of the data types
DATA_TYPE_LEN = {FRACT: 1, #byte
                 ASCII: 1, #ASCII
                 SHORT: 2, #short int
                 LONG : 4, #long int
                 BYTE : 8, #fraction
                 }


# 1st command line argument: TIFF file to process
filename = sys.argv[1]



# 2nd and 3rd command line arguments: horizontal and vertical DPI
x_density = sys.argv[2]
y_density = sys.argv[3] 

# dpi in tiffs is stored as a fraction of two 4byte-long unsigned integers
def fraction(string, max_value, step=10):
    
    if '/' in string:
        density = [int(value) for value in string.split('/')]
        return density
        
        
    value = float(string) 
    if value > max_value:
        raise Exception(f"float {value} exedes the maximum possible value {max_value}")

    denominator = 1
    nominator = int(denominator*value)
    
    while(denominator * step < max_value and
          nominator * step < max_value and
          int(nominator) / int(denominator) != value):
          
        denominator *= step
        nominator = denominator*value #"nominator *= step" does the same but leads to rounding errors
      
    return (int(nominator), int(denominator),)    


x_density = fraction(x_density, MAX_VALUE)
y_density = fraction(y_density, MAX_VALUE)

for value in x_density+y_density:
    assert 0 < value < MAX_VALUE


# 4th (optional) command line argument: unit (inches or centimeters); default is 'inches'
unit = 'inches'
if len(sys.argv) > 4:
    unit = sys.argv[4]
if 'inch' in unit.lower() or 'dpi' in unit.lower() or unit == 'quiet':
    unit = 'inches'
elif 'cm' in unit.lower() or 'centim' in unit.lower():
    unit = 'centimeters'
else:
    unit = 'none'



# last (optional) command line argument: quiet processing
echo = True
if sys.argv[-1] == 'quiet':
    echo = False

def IFDs(file, byteorder, offset=0):
    """iterator of the IFD of a file"""

    file.seek(4+offset)
    index = 0

    IDF_location = int.from_bytes(file.read(4), byteorder) + offset
    
    
    while IDF_location != 0:
        file.seek(IDF_location)
        
        IDF_lengh = int.from_bytes(file.read(2), byteorder)*FIELD_LENGTH
        end = IDF_location+IDF_lengh+2

        yield index, IDF_location, end
        
            
        index+=1
        ## Find the next IDF location (it will be 0 if there are no more IDFs)
        file.seek(end)
        IDF_location = int.from_bytes(file.read(4), byteorder) 

def go_to_IDF_index(index, file, byteorder, offset):
    """points to the nth IDF in the file"""
    for IDF_index, IDF_location, IDF_end in IFDs(file, byteorder, offset):
        if index == IDF_index:
            return IDF_index, IDF_location, IDF_end


def IFD_tags(file, byteorder, IDF_location):
    """iterator of the tags of a IDF"""

        file.seek(IDF_location)
        
        start = IDF_location+2 
        IDF_lengh = int.from_bytes(file.read(2), byteorder)*FIELD_LENGTH
        end = start+IDF_lengh
        
        for field_location in range(start,end,FIELD_LENGTH):
            file.seek(field_location)
            yield field_location

def tags(file, byteorder):
    """iterator of the tags of a file"""

    for IFD_index, IFD_start, IFD_end in IFDs(file, byteorder, offset):
        for tag_start in IFD_tags(file, byteorder, IFD_start):
            yield tag_start

def is_offset(file, tag_start, byteorder):
    file.seek(tag_start)
    file.seek(tag_start+2)
    data_type = int.from_bytes(file.read(2), byteorder)
    count = int.from_bytes(file.read(4), byteorder)
    len = DATA_TYPE_LEN[data_type]*count
    return len > 4
    
def add_empty_tags(tags, index, file, byteorder):
    print('the following tags are to be added to index', index, tags)
    
    # File end offset
    file.seek(0, os.SEEK_END)
    end = file.tell() - offset
    
    number_of_tags = len(tags)
                
    fields = [tags[tag_id].to_bytes(2, byteorder) + # Tag (2 bites) +
              int(  FRACT).to_bytes(2, byteorder) + # placeholder data_type
              int(      1).to_bytes(4, byteorder) + # placeholder count
              int(tag_id*FIELD_LENGTH).to_bytes(4, byteorder) for tag_id in range(len(tags))] # offset

    fields = b''.join(fields)
    
    IDF_index, IDF_location, IDF_end = go_to_IDF_index(index, file, byteorder, offset)
    
    ## Update IDF lenght
    file.seek(IDF_location)
    lenght = int.from_bytes(file.read(2), byteorder)+number_of_tags
    file.seek(IDF_location)
    file.write(lenght.to_bytes(2, byteorder))
    
    ## add tags
    file.seek(IDF_end)
    remaining_bytes = file.read()
    file.seek(IDF_end)
    file.write(fields)
    file.write(remaining_bytes)
    
    ## fix offset
    lenght = len(fields)
    for tag_start in tags(file, byteorder):
        if is_offset(file, tag_start, byteorder):
        
            file.seek(tag_start+8)
            Offset = int.from_bytes(file.read(4), byteorder)
            if Offset < IDF_end: continue
            Offset += lenght
            
            
            file.seek(tag_start+8)
            file.write(Offset.to_bytes(4, byteorder))
    
    
    return None

def change_TIFF_dpi(filename, x_density, y_density, unit, offset=0):
  with open(filename, 'rb+') as file:
  
    filename = os.path.split(filename)[1]
  
  
    ## Read and interpret the signature
  
    file.seek(offset)
    initial_signature = file.read(4)

    if initial_signature == BIG_ENDIAN_SIGNATURE:
        byteorder = 'big'
    elif initial_signature == LITTLE_ENDIAN_SIGNATURE:
        byteorder = 'little'
    else:
        raise Exception(f"File '{os.path.split(filename)[1]}' is not a valid TIFF image: initial TIFF signature is missing.")

    


    ## Encode the values into bytes according to the signature's byteorder

    # x_density = (int(value) for value in x_density) 
    # y_density = (int(value) for value in y_density)

    x_density_b = x_density[0].to_bytes(4, byteorder) + \
                  x_density[1].to_bytes(4, byteorder) 
    y_density_b = y_density[0].to_bytes(4, byteorder) + \
                  y_density[1].to_bytes(4, byteorder) 
                  
    x_density = x_density[0]/x_density[1]
    y_density = y_density[0]/y_density[1]
                  
    
    if   unit == 'none':        unit_value = 1
    elif unit == 'inches':      unit_value = 2
    elif unit == 'centimeters': unit_value = 3
    else: raise Exception(f'Invalid unit {unit}')

                      # Type: short int
                      # Number of values: 1
                      # Value: unit_value
                      # 2-byte empy space
    unit_b          = int(SHORT).to_bytes(2, byteorder) + \
                      int(    1).to_bytes(4, byteorder) + \
                      unit_value.to_bytes(2, byteorder) + \
                      int(    0).to_bytes(2, byteorder)

    tags_missing = {}

    ## Chek for missing tags
    for index, IFD_start, IFD_end in IFDs(file, byteorder, offset):
        IFD_tags_missing = [XRESOLUTION_TAG, YRESOLUTION_TAG, RESOLUTIONUNIT_TAG, ]
      
        for tag_start in IFD_tags(file, byteorder, IFD_start):
            
            field_tag = int.from_bytes(file.read(2), byteorder)
            
            
            if field_tag == XRESOLUTION_TAG:
                IFD_tags_missing.remove(field_tag)
    
            elif field_tag == YRESOLUTION_TAG:
                IFD_tags_missing.remove(field_tag)
    
            elif field_tag == RESOLUTIONUNIT_TAG:
                IFD_tags_missing.remove(field_tag)
        
        
        if IFD_tags_missing:
            tags_missing[index] = IFD_tags_missing


    # Add missing tags
    for index in tags_missing:
        add_empty_tags(tags_missing[index], index, file, byteorder)
    
    # Update tag fields
    for tag_start in tags(file, byteorder):
            
        field_tag = int.from_bytes(file.read(2), byteorder)
    
    
        if field_tag == XRESOLUTION_TAG:
            
            # Set attributes
            file.write(int(FRACT).to_bytes(2, byteorder)+ #data_type = fraction (5)
                       int(    1).to_bytes(4, byteorder)) #count     = 1
                
            # Find offset
            X_res_location = int.from_bytes(file.read(4), byteorder)+offset
            file.seek(X_res_location)
            
            # Overwrite the value
            if echo: print(f"Setting x-density of '{filename}' to {x_density} DPI for the IDF at location {IFD_start}.")
            x_density_found = True
            file.write(x_density_b)
            


        elif field_tag == YRESOLUTION_TAG:
            
            # Set attributes
            file.write(int(FRACT).to_bytes(2, byteorder)+ #data_type = fraction (5)
                       int(    1).to_bytes(4, byteorder)) #count     = 1
                
            # Find offset
            Y_res_location = int.from_bytes(file.read(4), byteorder)
            file.seek(Y_res_location)
            
            # Overwrite the value
            if echo: print(f"Setting y-density of '{filename}' to {y_density} DPI for the IDF at location {IFD_start}.")
            y_density_found = True
            file.write(y_density_b)

            

        elif field_tag == RESOLUTIONUNIT_TAG:
        
            #Overwrite unit
            if echo: print(f"Setting density unit of '{filename}' to {unit} for the IDF at location {IFD_start}.")
            unit_found = True
            file.write(unit_b)
            
        else:
            print(field_tag, file.read(2), file.read(4), file.read(4))
            
    if echo: print('Done.')
                
        


change_TIFF_dpi(filename, x_density, y_density, unit)
