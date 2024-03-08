import os, shutil, re, requests
import zipfile, tempfile
def download_image(url):
    try:
        # Send a GET request to the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for 4xx and 5xx status codes

        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()

        # Create a temporary file to save the image
        temp_file_path = os.path.join(temp_dir, 'image.jpg')

        # Write the image content to the temporary file
        with open(temp_file_path, 'wb') as f:
            f.write(response.content)

        # Return the path of the downloaded image and the temporary directory
        return temp_file_path, temp_dir
    except requests.exceptions.RequestException as e:
        print("Error downloading image:", e)
        return None, None
    
def substitute_values(stringdata, dictdata):
            # regex pattern to find placeholder and replace with the value
            for placeholder, value in dictdata.items():
                # dealing with adding multi line value to the variable in xml using heavy regex
                # if False:
                if '\n' in value:
                    values = value.split('\n')

                    main_search_string = f'&lt;{placeholder}&gt;'
                    
                    occurrences = re.finditer(rf'(<w:p(?:(?!<w:p )(?!<w:p>).)*?)(<w:r>(?:(?!<w:r>).)*?)<w:t>[^<>]*?({main_search_string})', stringdata)
                    

                    for count, occurrence in enumerate(occurrences):    
                        # pretext to add new line
                        # condition to check if placeholder is in bullet point then add new <w:p>
                        if '<w:numPr><w:ilvl w:val="0"/>' in occurrence.group(1):   
                            # This is just like pressing enter in docx
                            # print('list found!')
                            pretext = occurrence.group(1) + occurrence.group(2) + '<w:t>'
                            posttext = '</w:t></w:r></w:p>'
                        # if not bullet point then to keep the consistent style just do <w:br>
                        else:
                            # This is just like pressing shift + enter in docx
                            pretext = occurrence.group(2) + '<w:br w:type="textWrapping"/></w:r>' + occurrence.group(2) + '<w:t>'
                            posttext = '</w:t></w:r>'
                            

                        data_multiline = ''
                        for i, val in enumerate(values):
                            if i == 0:
                                data_multiline += f"{val}{posttext}"
                            elif i == len(values) - 1:
                                data_multiline += f'{pretext}{val}'
                            else:
                                data_multiline += f'{pretext}{val}{posttext}'

                        stringdata = re.sub(re.escape(occurrence.group(3)), data_multiline, stringdata, count=count+1)
                else:
                    stringdata = re.sub(rf'&lt;{placeholder}&gt;', value, stringdata)
            return stringdata

def adding_an_image(unzippedocx_dir, img_url, img_no, content):
    # Use re.sub to replace the ID value for adding new image
    img_dir = os.path.join(unzippedocx_dir,'word','media')
    file_names = os.listdir(img_dir)

    img_pos = len(file_names) + 1
    img_name = f"image{img_pos}.png"
    image_path, temp_dir = download_image(img_url)
    shutil.copy(image_path,os.path.join(img_dir, img_name))
    shutil.rmtree(temp_dir)

    img_id_pattern = r'id="(\d+)" name="Picture (\d+)"'
    rid_pattern = r'<a:blip r:embed="rId(\d+)"/>'

    img_org_id = int(re.search(img_id_pattern, content).group(1))
    rid_num = int(re.search(rid_pattern, content).group(1))

    extracted_data = re.sub(img_id_pattern, f'id="{img_pos}" name="Picture {img_pos}"', content)
    extracted_data = re.sub(rid_pattern, f'<a:blip r:embed="rId{rid_num + (img_pos - img_org_id )}"/>', extracted_data)
    
    doc_rels_path = os.path.join(unzippedocx_dir,'word','_rels',"document.xml.rels")
    with open(doc_rels_path, 'r') as content_file:
        rels_content = content_file.read()
    
    rels_pretext_pattern = r'<\?xml version="1.0" encoding="UTF-8" standalone="yes"\?>.*?<Relationships.*?rId(\d+).*?Target="fontTable\.xml"/>'

    max_rid = int(re.search(rels_pretext_pattern, rels_content,  re.DOTALL).group(1))
    pretext = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId{max_rid+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/fontTable" Target="fontTable.xml"/>'
    new_text = pretext + f'<Relationship Id="rId{rid_num + (img_pos - img_org_id)}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image{img_pos}.png"/>'
    rels_content = re.sub(rels_pretext_pattern, "", rels_content,  flags=re.DOTALL)
    rels_content = new_text + rels_content

    with open(doc_rels_path, 'w', encoding="utf-8") as modified_file:
        modified_file.write(rels_content)
    
    return extracted_data
def reportme(tmpl_path,out_path,data_dict, img_dict=None, array=None):
    """
    fill_template(tmpl_path, out_path, data_dict, img_list):
        Fills in the fields of the template document with data and generates a result document.

    Args:
        tmpl_path (str): Path of the template document that contains the fields to be filled in.
        out_path (str): Path of the resulting document with placeholders replaced by data.
        data_dict (dict): A dictionary mapping placeholder names to their corresponding values for replacement.
        img_list (dict): A dictionary specifying the images to replace in the document. 
            Key: The position of the image, docx and odt have different positions arrangement.
            Value: The path to the image file.

    Note:
    - In ODT files: Position of Images depends on the order of adding them not the format of document.
        - if someone adds the image first but adds it to the last page still it will gonna have 0 position.
    - In DOCX files: Position of Images depends on the format of document.
        - if someone adds the image first but adds it to the last page then it will gonna have last position.

    Example:
        tmpl_path = 'template.odt'
        out_path = 'result.odt'
        data_dict = {'placeholder1': 'value1', 'placeholder2': 'value2'}
        img_list = {0: 'image1.png', 1: 'image2.png'}
        fill_template(tmpl_path, out_path, data_dict, img_list)
    """
    
    if tmpl_path.lower().endswith(".docx"):
        # Create a temporary directory to extract the DOCX contents
        temp_dir = tempfile.mkdtemp()

        # Extract the ODT contents to the temporary directory
        with zipfile.ZipFile(tmpl_path, 'r') as odt_file:
            odt_file.extractall(temp_dir)
        
        content_path = os.path.join(temp_dir, 'word','header1.xml')
        # Read the header.xml and footer.xml file for header and footer
        if  os.path.isfile(content_path):
            # header.xml
            with open(content_path, 'r') as content_file:
                content = content_file.read()
                content_file.close()
            
            # regex pattern to find placeholder and replace with the value
            for placeholder, value in data_dict.items(): 
                content = re.sub(rf'&lt;{placeholder}&gt;', value, content)

            # Write the modified content back to styles.xml
            with open(content_path, 'w', encoding="utf-8") as modified_file:
                modified_file.write(content)
                modified_file.close()

            # footer.xml
            content_path = os.path.join(temp_dir, 'word','footer1.xml')
            with open(content_path, 'r') as content_file:
                content = content_file.read()
                content_file.close()
            
            # regex pattern to find placeholder and replace with the value
            for placeholder, value in data_dict.items(): 
                content = re.sub(rf'&lt;{placeholder}&gt;', value, content)

            # Write the modified content back to styles.xml
            with open(content_path, 'w', encoding="utf-8") as modified_file:
                modified_file.write(content)
                modified_file.close()
        
        # Read the document.xml file
        content_path = os.path.join(temp_dir, 'word', 'document.xml')
        with open(content_path, 'r', encoding='utf-8') as content_file:
            content = content_file.read()
            content_file.close()
#--------------- Test --------------------------------
        if r"%array%" in content:
            matches = re.findall(r'%array%(.*?)%/array%', content, re.DOTALL)
            
            if matches:
                # Extract the first match (assuming there's only one) and strip leading/trailing whitespace
                extracted_data = matches[0].strip(r"%array%").strip(r"%/array%")
                new_data = ""
                for i, dict_data in enumerate(array):
                    img_url = dict_data.pop('Picture', None)
                    if img_url is not None:
                        new_data += substitute_values(adding_an_image(temp_dir, img_url, i, extracted_data), dict_data)
                    else:
                        new_data += substitute_values(extracted_data, dict_data)
                # Replace the original extracted data with the processed data
                content = content.replace(f'%array%{extracted_data}%/array%', new_data)

# ----------------------------------------------------------------
        content = substitute_values(content, data_dict)
                
        # replace the placeholder images
        if not img_dict == None:
            img_dir = os.path.join(temp_dir,'word','media')
            file_names = os.listdir(img_dir)
            try:
                for num, imgPath in img_dict.items():
                    shutil.copy(imgPath,os.path.join(img_dir, f'{file_names[int(num)]}'))
                    print
            except IndexError:
                print(f'You have only {len(file_names)} image/s in the doc. Index starts from 0')
                
        # Write the modified content back to content.xml
        with open(content_path, 'w', encoding="utf-8") as modified_file:
            modified_file.write(content)
            modified_file.close()
        # Create a new ODT file with the modified content
        with zipfile.ZipFile(out_path, 'w') as modified_odt:
            # Add the modified content.xml back to the ODT
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    modified_odt.write(file_path, arcname)

        # print("Modified file saved as:", out_path)
        # print(temp_dir)
        # input("press enter to continue")
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    # reportme("Microsoft_created.docx","MS_check.docx",{"Heading": "Fing Video\nnew","Description":"checking\nthis\nvideo","Lists":"checking\ntags\nwhy\nnot"},{0:"maxresdefault.jpg"})
    
    # reportme("wpscreated.docx","wpscheck.docx",{"Heading": "Fing Video\nnew","Description":"checking\nthis\nvideo","Lists":"checking\ntags\nwhy\nnot"},{0:"maxresdefault.jpg"})
    
    # reportme("openoffice.odt","test.odt",{"Heading": "Fing Video\nnew","Description":"checking\nthis\nvideo"})

    reportme("libs/test_array.docx","array_out.docx",{"heading": "Fing Video\nnew","description":"checking\nthis\nvideo"},array=[{"vid":"tester1","num":"124", "Picture":"https://yt3.googleusercontent.com/6FqcWoHZvrZixaGi1S3Re3Z90SCS3iq2_36hQSnSHQPtQVVkywH8WKka53MiBYBSP6DmqM-g9w=s176-c-k-c0x00ffffff-no-rj"},{"vid":"nice","num":"1","Picture":"https://yt3.googleusercontent.com/mHrqjdngHeZfR08mkdIcSiL7vWFLAhrrPrRutOQJYQ1RWRKPEVDsxKVfL_nIxZg5njr-lQAqQg=s176-c-k-c0x00ffffff-no-rj"},{"vid":"cat","num":"3", "Picture":"https://yt3.ggpht.com/ZeokXdjeXW_6CpcChqvVBEBcHoJ9TAaLTnQj8yT942LLV8afhmUv6zLtqzbNS1uPnernj3SPshA=s68-c-k-c0x00ffffff-no-rj"},{"vid":"crip","num":"1"}])
    # reportme("libs/test_array.docx","array_out.docx",{"heading": "Fing Video\nnew","description":"checking\nthis\nvideo"},array=[{"vid":"tester1","num":"124"},{"vid":"nice","num":"1"},{"vid":"cat","num":"3"},{"vid":"crip","num":"1"}])
