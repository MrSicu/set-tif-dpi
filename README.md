# set-tif-dpi
This code sets or changes the DPI metadata information of a TIFF image file. It is based on specifications of TIFF image format given at https://paulbourke.net/dataformats/tiff/ and https://www.awaresystems.be/imaging/tiff/tifftags.html

Features:
- file name is (intentionally) not checked for TIFF extension;
- no re-encoding of image nor validation of TIFF format;
- although complete TIFF format validation is **not** performed, file is checked for TIFF initial signature. Therefore, malformed or corrupted TIFF images may or may not generate an error;
- TIFF image file is modified “in place”. Density metadata are **overwritten** if already present.
- no backup copy of original file is made.

Usage examples:

````
python set-tif-dpi <filename> <horizontal DPI> <vertical DPI> [unit] [quiet]

python set-tif-dpi image.tiff 150 150
python set-tif-dpi image.tiff 60 120 cm
python set-tif-dpi "my image.tif" 300 300 quiet
````

The code has been rewritter to work with TIFF files, and was largely inspired by set-png-dpi by nopria from https://github.com/nopria/set-png-dpi/tree/main

Enjoy!

