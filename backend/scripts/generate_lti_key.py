"""
يولّد مفتاح RSA خاص لتوقيع طلبات LTI (client assertions لتصحيح الدرجات).
شغّله مرة واحدة، ثم انسخ سطري الإعداد إلى ملف .env.

الاستخدام: python scripts/generate_lti_key.py
"""
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode("ascii")

print("# انسخ السطرين التاليين إلى backend/.env. لا ترفع المفتاح الخاص إلى Git.")
print("LTI_TOOL_PRIVATE_KEY=" + json.dumps(pem))
print("LTI_TOOL_KID=lumen-key-1")
