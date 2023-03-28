# misc-procore-scripts

## Download/Extract Drawings
This saved a bunch of work by finding all RFI drawings and sketches involved in RFIs on Procore. It sorts them according to various details about the documents. The extract drawings *tries* to extract any drawings found in a PDF attachment, as well as OCR the typical region of interest to attain the drawing number and project name. I used a config.py file to store the client id/secret and other reused variables.

## Download RFIs
download_rfi.py goes through a RFI report Procore provides for a project. First in get_rfi_attachments.py a json file is parsed for all rfi attachments and saves it in a simpler, more ordered way in rfi_data.pickle. Then in download_rfi.py the report pdf is supplied and it parses it for links. For each link found, the corresponding url is requested and downloaded, and the filename is saved according to file matches in the rfi_data.pickle. All attachments are saved in a temporary directory. Finally, an alternative pdf is saved with all the links highlighted.



