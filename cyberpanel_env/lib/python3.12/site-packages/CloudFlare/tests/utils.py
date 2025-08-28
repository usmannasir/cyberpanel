""" misc utilities for Cloudflare test code """

dummy_loa_document = """%PDF-1.4
1 0 obj << /Length 559 >> stream
 1 0 0 rg
 BT /F1 24 Tf 72 680 Td (LOA DOCUMENT) Tj ET
 .75 .75 .75 RG 1 w
 72 676 m 540 676 l s
 0 0 0 rg
 BT /F1 12 Tf 72 648 Td (See /tests/ folder under python-cloudflare on GitHub) Tj ET
 BT /F1 12 Tf 72 624 Td (THIS DOCUMENT IS ONLY USED FOR TESTING) Tj ET
 BT /F1 12 Tf 72 604 Td (Please ignore and delete upon receipt) Tj ET
 BT /F1 12 Tf 72 584 Td (See URL:) Tj ET
 0 0 1 rg
 BT /F2 12 Tf 130 584 Td (http://github.com/cloudflare/python-cloudflare) Tj ET
 .75 .75 .75 RG 1 w
 72 560 m 540 560 l s
 .75 .75 .75 RG 1 w
 36 756 m 576 756 l 576 36 l 36 36 l 36 756 l s
endstream
endobj
2 0 obj << /Type /Catalog /Pages 3 0 R >> endobj
3 0 obj << /Type /Pages /Kids [4 0 R ] /Count 1 >> endobj
4 0 obj << /Type /Page /Parent 3 0 R /MediaBox [0 0 612 792] /Contents 1 0 R
 /Resources <<
  /ProcSet 5 0 R
  /Font << /F1 6 0 R >>
  /Font << /F2 7 0 R >>
 >>
>>
endobj
5 0 obj [/PDF /Text] endobj
6 0 obj << /Type /Font /Subtype /Type1 /Name /F1 /BaseFont /Arial >> endobj
7 0 obj << /Type /Font /Subtype /Type1 /Name /F2 /BaseFont /Courier >> endobj
8 0 obj << /Creator (https://github.com/cloudflare/python-cloudflare)
 /Producer (Hand coded for python-cloudflare)
 /Title (dummy_loa_document.pdf)
 /Author (Martin J Levy)
 /Subject (Dummy LOA Document - please delete)
 /Keywords (LOA)
 /CreationDate (D:20240101120000Z)
 /ModDate (D:20240101120000Z)
>> endobj
trailer << /Size 8 /Root 2 0 R /Info 8 0 R >>
%%EOF"""

