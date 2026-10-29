"""
يولّد مفتاح RSA خاص لتوقيع طلبات LTI (client assertions لتصحيح الدرجات).
شغّله مرة وحدة، وحطّ الناتج بمتغيّر LTI_TOOL_PRIVATE_KEY بملف .env.

الاستخدام: python scripts/generate_lti_key.py
"""
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode()

print("=== انسخ هذا كامل لمتغيّر LTI_TOOL_PRIVATE_KEY بملف .env ===")
print("(لازم يكون بسطر واحد — استبدل الأسطر الجديدة بـ \\n)")
print()
print(repr(pem))
