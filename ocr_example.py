from PIL import Image
import pytesseract as tes
import cv2
import xml.etree.ElementTree as ET
import re
import json

def find_in_sentences(text, dict, **kwargs):
    sentences = text.split('\n')
    for sentence in sentences:
        for key, word in kwargs.items():
            index = sentence.find(word)
            if index != -1:
                dict[key] = sentence[index + len(word):]


def text_to_labels(label, text, dict):
    if label == 'fm1':
        find_in_sentences(text, dict, Address = 'adress: ', facilityId = 'id: ')
    if label == 'fm2':
        find_in_sentences(text, dict, contractId = 'nummer: ')
    if label == 'fm3':
        dict['kind'] = 'ElHandel'
        find_in_sentences(text, dict, period = 'Elhandel ')
    if label == 't':
        if text.find('SEK') != -1:
            find_in_sentences(text, dict, totalCost = 'Totalt')
        else:
            find_in_sentences(text, dict, totalCons = 'Totalt')
    if label == 'fd':
        dict['invoiceRows'] = []
        sentences = text.split('\n')
        non_empty_sentences = [i for i in sentences if i]
        dict['VAT'] = non_empty_sentences[-2]
        index = [i for i,x in enumerate(non_empty_sentences) if x.find('Moms')!=-1][0]
        for ind, sentence in enumerate(non_empty_sentences):
            if ind < index:
                invoice = {}
                invoice['text'] = sentence
                invoice['spec'] = non_empty_sentences[ind+index+1] + " "+ non_empty_sentences[ind+2*index+1]
                invoice['value'] = non_empty_sentences[ind+3*index+1]
                dict['invoiceRows'].append(invoice)
    if label == 'ms':
        sentences = text.split('\n')
        data_points = []
        for sentence in sentences:
            index = sentence.find('nummer: ')
            if index != -1:
                dict['meterNumber'] = ''.join([word for word in sentence if word.isdigit()])
            a = re.findall(r"[\d]{4}—[\d]{1,2}—[\d]{1,2}", sentence)
            if a != []:
                words = sentence.split()
                data_points.append({'date':a[0], 'value': words[2] + words[3]})
        dict['datapoints'] = data_points


def get_coordinates(i):
    for coordinate in i:
        if coordinate.tag == 'xmin':
            xmin = coordinate.text
        if coordinate.tag == 'ymin':
            ymin = coordinate.text
        if coordinate.tag == 'xmax':
            xmax = coordinate.text
        if coordinate.tag == 'ymax':
            ymax = coordinate.text
    return xmin, ymin, xmax, ymax

def image_to_dict(img, root, main_dict):
    dict = {}
    results = ""
    objects = root.findall('object')
    for object in objects:
        for i in object:
            if i.tag == 'name':
                label = i.text
            if i.tag == 'bndbox':
                xmin, ymin, xmax, ymax = get_coordinates(i)
                crop_img = img[int(ymin):int(ymax), int(xmin):int(xmax)]
                results = tes.image_to_string(crop_img, lang='lat')
                if label == 'h':
                    find_in_sentences(results, main_dict, customerId = 'Kundnr ',
                                      invoiceNumber = '/OCR—nr')
                if label == 'fm1':
                    if bool(dict):
                        main_dict['invoiceSections'].append(dict)
                    dict = {}
                text_to_labels(label, results, dict)

    main_dict['invoiceSections'].append(dict)
    return main_dict

if __name__=="__main__":
        tree = ET.parse('/home/apurva/annotaions/faktura-30156425016_(1)0001-2.xml')
        img = cv2.imread("/home/apurva/annotaions/faktura-30156425016_(1)0001-2.jpg")
        root = tree.getroot()
        main_dict = {}
        main_dict['invoiceSections'] = []
        invoices_dict = image_to_dict(img, root, main_dict)
        print(invoices_dict)
        json_object = json.dumps(invoices_dict, indent = 4, ensure_ascii=False)
        with open('result.json', 'w') as fp:
            fp.write(json_object)
