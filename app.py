from flask import Flask, request, jsonify, render_template
from azure.storage.blob import BlobServiceClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, AnalyzeResult
from dotenv import load_dotenv
import os

app = Flask(__name__)

load_dotenv()

# Azure Blob Storage configuration
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME")
AZURE_STORAGE_BLOB_NAME = os.getenv("AZURE_STORAGE_BLOB_NAME")

# Azure Document Intelligence configuration
DOCUMENT_INTELLIGENCE_ENDPOINT = os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT")
DOCUMENT_INTELLIGENCE_API_KEY = os.getenv("DOCUMENT_INTELLIGENCE_API_KEY")


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify(success=False, message="No file part"), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify(success=False, message="No selected file"), 400
    if file and allowed_file(file.filename):
        filename = file.filename
        upload_blob(file, filename)
        print(filename)
        return analyze_document(filename) # Directly return the analysis results
    else:
        return jsonify(success=False, message="Invalid file type"), 400
    
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

def upload_blob(file, filename):
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    blob_client = blob_service_client.get_blob_client(AZURE_STORAGE_CONTAINER_NAME, filename)
    blob_client.upload_blob(file.read(), overwrite=True)

def analyze_document(filename):
    document_intelligence_client = DocumentIntelligenceClient(endpoint=DOCUMENT_INTELLIGENCE_ENDPOINT, credential=AzureKeyCredential(DOCUMENT_INTELLIGENCE_API_KEY))
    url = f"https://{AZURE_STORAGE_BLOB_NAME}.blob.core.windows.net/{AZURE_STORAGE_CONTAINER_NAME}/{filename}"
    poller = document_intelligence_client.begin_analyze_document("prebuilt-invoice", AnalyzeDocumentRequest(url_source=url))
    result: AnalyzeResult = poller.result()
    
    processed_result = dict()

    if result.documents:
        for idx, receipt in enumerate(result.documents):
            print(f"--------Analysis of receipt #{idx + 1}--------")
            print(f"Receipt type: {receipt.doc_type if receipt.doc_type else 'N/A'}")
            if receipt.fields:
                vendor_name = receipt.fields.get("VendorName")
                if vendor_name:
                    print(
                        f"Vendor Name: {vendor_name.get('valueString')} has confidence: "
                        f"{vendor_name.confidence}"
                    )
                    processed_result['VendorName'] = vendor_name.get('valueString')

                # Customer Name
                customer_name = receipt.fields.get("CustomerName")
                if customer_name:
                    print(
                        f"Customer Name: {customer_name.get('valueString')} has confidence: "
                        f"{customer_name.confidence}"
                    )
                    processed_result['CustomerName'] = customer_name.get('valueString')

                # Customer ID
                customer_id = receipt.fields.get("CustomerId")
                if customer_id:
                    print(
                        f"Customer ID: {customer_id.get('valueString')} has confidence: "
                        f"{customer_id.confidence}"
                    )
                    processed_result['CustomerId'] = customer_id.get('valueString')

                # Purchase Order
                purchase_order = receipt.fields.get("PurchaseOrder")
                if purchase_order:
                    print(
                        f"Purchase Order: {purchase_order.get('valueString')} has confidence: "
                        f"{purchase_order.confidence}"
                    )
                    processed_result['PurchaseOrder'] = purchase_order.get('valueString')

                invoice_id = receipt.fields.get("InvoiceId")
                if invoice_id:
                    print(
                        f"Invoice ID: {invoice_id.get('valueString')} has confidence: "
                        f"{invoice_id.confidence}"
                    )
                    processed_result['InvoiceId'] = invoice_id.get('valueString')

            print("--------------------------------------")       
             
    
    return processed_result

if __name__ == '__main__':
    app.run(debug=True)
