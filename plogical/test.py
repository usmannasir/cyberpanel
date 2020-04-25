import urllib.parse
encodedStr = 'ville.laprairie.qc.ca&fileToDownload=/home/ville.laprairie.qc.ca/public_html/app/uploads/2019/05/2019-05-16_Terre-contamine%CC%81e-sur-Goyer-150x150.jpg'
print(urllib.parse.unquote(encodedStr))