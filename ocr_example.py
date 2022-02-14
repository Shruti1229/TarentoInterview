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
        dict['VAT'] = " ".join(sentences[-2].split()[-2:])
        for sentence in sentences[:-2]:
            for ind, word in enumerate(sentence):
                invoice = {}
                if word.isdigit():
                    if(sentence[ind-1] == '—'):
                        ind = ind - 2
                    invoice['text'] = sentence[:ind-2]
                    invoice['value'] = ' '.join(sentence.split()[-2:])
                    invoice['spec'] = sentence[ind:].replace(invoice['value'], ' ')
                    dict['invoiceRows'].append(invoice)
                    break
    if label == 'ms':
        sentences = text.split('\n')
        data_points = []
        dict_ms = {}
        for sentence in sentences:
            index = sentence.find('nummer: ')
            if index != -1:
                dict_ms['meterNumber'] = ''.join([word for word in sentence if word.isdigit()])
            a = re.findall(r"[\d]{4}—[\d]{1,2}—[\d]{1,2}", sentence)
            if a != []:
                words = sentence.split()[2:]
                if len(words) < 2:
                    value = words[0]
                else:
                    value = words[0] + words[1]
                data_points.append({'date':a[0], 'value': value})
        dict_ms['datapoints'] = data_points
        dict['meterstands'].append(dict_ms)


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
    count_ms = 0
    for object in objects:
        for i in object:
            if i.tag == 'name':
                label = i.text
            if i.tag == 'bndbox':
                xmin, ymin, xmax, ymax = get_coordinates(i)
                crop_img = img[int(ymin):int(ymax), int(xmin):int(xmax)]
                custom_config = r'--oem 1 --psm 6 '
                results = tes.image_to_string(crop_img, lang='lat',
                                              config=custom_config)
                if label == 'h':
                    find_in_sentences(results, main_dict, customerId = 'Kundnr ',
                                      invoiceNumber = '/OCR—nr')
                if label == 'fm1':
                    if bool(dict):
                        count_ms = 0
                        main_dict['invoiceSections'].append(dict)
                    dict = {}
                if label == 'ms':
                        count_ms = count_ms + 1
                        if(count_ms == 1):
                            dict['meterstands'] = []
                text_to_labels(label, results, dict)

    main_dict['invoiceSections'].append(dict)
    return main_dict

if __name__=="__main__":
        tree = ET.parse('/home/apurva/tmp/faktura-78014963017_(1)0001-2.xml')
        img = cv2.imread('/home/apurva/tmp/faktura-78014963017_(1)0001-2.jpg')
        root = tree.getroot()
        main_dict = {}
        main_dict['invoiceSections'] = []
        invoices_dict = image_to_dict(img, root, main_dict)
        json_object = json.dumps(invoices_dict, indent = 4, ensure_ascii=False)
        with open('result.json', 'w') as fp:
            fp.write(json_object)
