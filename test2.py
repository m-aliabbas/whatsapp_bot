from neonize.utils import build_jid

# Send simple text message
jid = build_jid("1234567890")
client.send_message(jid, text="Hello from Neonize! 🚀")

# Send image with caption
with open("image.jpg", "rb") as f:
    image_data = f.read()

image_msg = client.build_image_message(
    image_data,
    caption="Check out this amazing image! 📸",
    mime_type="image/jpeg"
)
client.send_message(jid, message=image_msg)

# Send document file
with open("document.pdf", "rb") as f:
    doc_data = f.read()

doc_msg = client.build_document_message(
    doc_data,
    filename="document.pdf",
    caption="Here is the document you requested",
    mime_type="application/pdf"
)
client.send_message(jid, message=doc_msg)