"""
يولّد مفتاح RSA خاص لتوقيع طلبات LTI (client assertions لتصحيح الدرجات).
شغّله مرة وحدة، وحطّ الناتج بمتغيّر LTI_TOOL_PRIVATE_KEY بملف .env.

الاستخدام: python scripts/generate_lti_key.py
"""
import json
import secrets

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode()

kid = f"lumen-{secrets.token_hex(8)}"

print("# انسخ السطرين التاليين كما هما إلى ملف .env")
print(f"LTI_TOOL_PRIVATE_KEY={json.dumps(pem)}")
print(f"LTI_TOOL_KID={kid}")
print()
print("# في Secret Manager استخدم محتوى PEM مع أسطره الفعلية،")
print("# وليس أحرف \\n النصية؛ خزّن KID في متغير منفصل.")
