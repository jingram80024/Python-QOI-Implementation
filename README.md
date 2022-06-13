# Python QOI Implementation
 Python implementation of the Quite OK Image format based on QOI encoder/decoder standards, C implementation, and typescript implementation

** Has not been through any benchmark testing, optimization, and has little error handling. **

Encoder.py reads an image specified in script by 'image_name' which should be place inside a directory called 'images' within the encoder script directory. Encoder.py outputs a binary .qoi file to the 'images' directory. All directory paths in Encoder.py are relative to the directory that holds Encoder.py.

Decoder.py takes in a qoi file and decodes into an array of RGB(A) pixels. Shows image with PIL and saves to jpg. If the file you are reading has 4 channels you must manually change the PIL save as type to png to jpg.

To use virtual environment you may need to change your security settings via windows powershell. Changing security settings can leave your computer vulnerable. Only do so if you know the limitations and dangers of changing ExecutionPolicy.
To change security to allow venv to run:
	1. Run windows powershell as an administrator
	2. use 'Set-ExecutionPolicy RemoteSigned' command.
	3. *most importantly: when you are done running venv, use 'Set-ExecutionPolicy Restricted' command to restore restricted settings.
Note: at anytime you can view your ExecutionPolicy by running 'Get-ExecutionPolicy -List' command